from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QLabel, QPushButton, QLineEdit,
                            QSplitter, QStackedWidget, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
import logging
import json
import os
import sys
import sqlite3

# Adjust the path to ensure we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tools.chart_utils import ChartFactory

class ArtistsSubmodule:
    """
    Submódulo para manejar las estadísticas relacionadas con artistas.
    Permite visualizar diferentes métricas y estadísticas para cada artista.
    """
    
    def __init__(self, parent=None, db_connection=None, lastfm_username=None, musicbrainz_username=None, helper_functions=None):
        """
        Inicializa el submódulo de artistas.
        
        Args:
            parent: El módulo padre (StatsModule)
            db_connection: Conexión SQLite a la base de datos
            helper_functions: Diccionario de funciones auxiliares del módulo padre
        """
        self.parent = parent
        self.conn = db_connection
        self.helper_functions = helper_functions or {}
        self.lastfm_username = lastfm_username
        self.musicbrainz_username = musicbrainz_username

        # Almacenamiento de datos
        self.artist_list = []
        self.selected_artist = None
        self.selected_artist_id = None
        
        # Inicializar referencias a elementos de la UI
        self.init_ui_references()
        
        # Verificar componentes de la UI
        self._verify_ui_components()
    
    def init_ui_references(self):
        """Inicializa referencias a elementos de la UI desde el módulo padre."""
        if not self.parent:
            logging.error("No se proporcionó módulo padre a ArtistsSubmodule")
            return
            
        # Referencia al widget principal
        self.artists_page = getattr(self.parent, 'page_artists', None)
        
        # Referencia a la tabla de artistas
        self.table_artists = getattr(self.parent, 'tableWidget', None)
        if not self.table_artists and self.artists_page:
            self.table_artists = self.artists_page.findChild(QTableWidget, "tableWidget")
            if not self.table_artists:
                self.table_artists = self.artists_page.findChild(QTableWidget, "tableWidget_3")
        
        # Referencia al stackedWidget para las vistas de detalle
        self.stacked_widget = getattr(self.parent, 'stackedWidget_artist', None)
        if not self.stacked_widget and self.artists_page:
            self.stacked_widget = self.artists_page.findChild(QStackedWidget, "stackedWidget_artist")
        
        # Referencia al nuevo stackedWidget_24
        self.stacked_widget_24 = getattr(self.parent, 'stackedWidget_24', None)
        if not self.stacked_widget_24 and self.artists_page:
            self.stacked_widget_24 = self.artists_page.findChild(QStackedWidget, "stackedWidget_24")
        
        # Añadir referencia al QSplitter (será creado en setup_connections)
        self.main_splitter = None
        
        # Referencias a los botones de navegación
        self.btn_home = getattr(self.parent, 'action_artist_home', None)
        self.btn_time = getattr(self.parent, 'action_artist_time', None)
        self.btn_concerts = getattr(self.parent, 'action_artist_conciertos', None)
        self.btn_genres = getattr(self.parent, 'action_artist_genres', None)
        self.btn_feeds = getattr(self.parent, 'action_artist_feeds', None)
        self.btn_labels = getattr(self.parent, 'action_artist_label', None)
        self.btn_discography = getattr(self.parent, 'action_artist_discog', None)
        self.btn_scrobbles = getattr(self.parent, 'action_artist_scrobbles', None)
        self.btn_producers = getattr(self.parent, 'action_artist_prod', None)
        self.btn_collaborators = getattr(self.parent, 'action_artist_collaborators', None)
        
        # Si los botones no se encontraron directamente, buscarlos en el widget
        if self.artists_page:
            button_widget = self.artists_page.findChild(QWidget, "widget_artists")
            if button_widget:
                if not self.btn_home:
                    self.btn_home = button_widget.findChild(QPushButton, "action_artist_home")
                if not self.btn_time:
                    self.btn_time = button_widget.findChild(QPushButton, "action_artist_time")
                if not self.btn_concerts:
                    self.btn_concerts = button_widget.findChild(QPushButton, "action_artist_conciertos")
                if not self.btn_genres:
                    self.btn_genres = button_widget.findChild(QPushButton, "action_artist_genres")
                if not self.btn_feeds:
                    self.btn_feeds = button_widget.findChild(QPushButton, "action_artist_feeds")
                if not self.btn_labels:
                    self.btn_labels = button_widget.findChild(QPushButton, "action_artist_label")
                if not self.btn_discography:
                    self.btn_discography = button_widget.findChild(QPushButton, "action_artist_discog")
                if not self.btn_scrobbles:
                    self.btn_scrobbles = button_widget.findChild(QPushButton, "action_artist_scrobbles")
                if not self.btn_producers:
                    self.btn_producers = button_widget.findChild(QPushButton, "action_artist_prod")
                if not self.btn_collaborators:
                    self.btn_collaborators = button_widget.findChild(QPushButton, "action_artist_collaborators")

        # Obtener funciones auxiliares importantes
        self.clear_layout = self.helper_functions.get('clear_layout', self._default_clear_layout)
        self.ensure_widget_has_layout = self.helper_functions.get('ensure_widget_has_layout', self._default_ensure_layout)

    def setup_connections(self):
        """Configura las conexiones de señales para los botones y la tabla."""
        # Conectar la tabla
        if self.table_artists:
            try:
                self.table_artists.itemClicked.disconnect()
            except:
                pass
            self.table_artists.itemClicked.connect(self.on_artist_selected)
        
        # Conectar los botones de navegación
        buttons = [
            (self.btn_time, self.show_time_stats),
            (self.btn_concerts, self.show_concert_stats),
            (self.btn_genres, self.show_genre_stats),
            (self.btn_feeds, self.show_feed_stats),
            (self.btn_labels, self.show_label_stats),
            (self.btn_discography, self.show_discography_stats),
            (self.btn_scrobbles, self.show_listen_stats),
            (self.btn_producers, self.show_producer_stats),
            (self.btn_collaborators, self.show_collaborator_stats)
        ]
        
        # Buscar y conectar el botón home si existe
        home_button = getattr(self.parent, 'action_artist_home', None)
        if not home_button and self.parent:
            home_button = self.parent.findChild(QPushButton, "action_artist_home")
        
        if home_button:
            try:
                home_button.clicked.disconnect()
            except:
                pass
            home_button.clicked.connect(self.home_stats)
            logging.info("Botón home conectado correctamente")
        
        for button, handler in buttons:
            if button:
                try:
                    button.clicked.disconnect()
                except:
                    pass
                button.clicked.connect(handler)
                
        # Configurar el QSplitter entre la tabla y los gráficos
        self.setup_splitter()

    def setup_splitter(self):
        """Configura un QSplitter entre la tabla de artistas y los gráficos."""
        if not self.artists_page:
            logging.error("No se puede configurar el splitter sin un widget de página de artistas")
            return
            
        # Buscar el layout horizontal que contiene el stackedWidget_24 y el widget_31
        widget_23 = self.artists_page.findChild(QWidget, "widget_23") 
        if not widget_23:
            logging.error("No se encontró widget_23 en page_artists")
            return
            
        # Obtener el layout horizontal existente
        horizontal_layout = widget_23.layout()
        if not horizontal_layout:
            logging.error("widget_23 no tiene un layout")
            return
            
        # Guardar una referencia a los widgets que necesitamos reorganizar
        table_widget = None
        if self.stacked_widget_24:
            # El stackedWidget_24 contiene la tabla de artistas en su primera página
            table_widget = self.stacked_widget_24
            
        details_widget = self.artists_page.findChild(QWidget, "widget_31")
        line_widget = self.artists_page.findChild(QFrame, "line")
        
        # Si cualquiera de estos no se encuentra, no podemos configurar el splitter
        if not table_widget or not details_widget:
            logging.error("No se encontraron los widgets necesarios para el splitter")
            return
            
        # Eliminar todos los widgets del layout horizontal existente
        while horizontal_layout.count():
            item = horizontal_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        
        # Crear un nuevo QSplitter horizontal
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Añadir widgets al splitter en el orden correcto
        self.main_splitter.addWidget(table_widget)
        if line_widget:
            self.main_splitter.addWidget(line_widget)
        self.main_splitter.addWidget(details_widget)
        
        # Establecer proporciones iniciales (ajusta estos valores según prefieras)
        self.main_splitter.setSizes([200, 10, 600])  # Valores aproximados en píxeles
        
        # Añadir el splitter al layout horizontal
        horizontal_layout.addWidget(self.main_splitter)
        
        logging.info("QSplitter configurado correctamente entre la tabla y los gráficos")

    def load_artist_stats(self):
        """Carga estadísticas de artistas y prepara la interfaz."""
        if not self.ensure_db_connection():
            return
        
        # Cargar la lista de artistas
        self.load_artist_list()
        
        # Configurar la tabla
        self.setup_artists_table()
        
        # Inicializar vistas en el stacked widget
        self.init_stacked_widget_pages()
        
        # Configurar conexiones
        self.setup_connections()
        
        # Verificar si hay un stackedWidget_24 y configurar la visibilidad
        if hasattr(self.parent, 'stackedWidget_24'):
            self.parent.stackedWidget_24.setCurrentIndex(0)  # Mostrar la página de tabla de artistas por defecto
            
        # Actualizar la etiqueta del artista 
        if hasattr(self.parent, 'artista_label'):
            self.parent.artista_label.setText("Artista: Seleccione un artista de la tabla")
    
    def _default_clear_layout(self, layout):
        """Implementación predeterminada de clear_layout."""
        if layout is None:
            return
            
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self._default_clear_layout(item.layout())
                item.layout().setParent(None)
    
    def _default_ensure_layout(self, widget, layout_type=QVBoxLayout):
        """Implementación predeterminada de ensure_widget_has_layout."""
        if widget is None:
            return None
            
        layout = widget.layout()
        if layout is None:
            layout = layout_type()
            widget.setLayout(layout)
        return layout
    
    def _verify_ui_components(self):
        """Verifica que los componentes de la UI existan y registra su estado."""
        components = {
            'artists_page': self.artists_page,
            'table_artists': self.table_artists,
            'stacked_widget': self.stacked_widget,
            'btn_time': self.btn_time,
            'btn_concerts': self.btn_concerts,
            'btn_genres': self.btn_genres,
            'btn_feeds': self.btn_feeds,
            'btn_labels': self.btn_labels,
            'btn_discography': self.btn_discography,
            'btn_scrobbles': self.btn_scrobbles,
            'btn_producers': self.btn_producers,
            'btn_collaborators': self.btn_collaborators
        }
        
        for name, component in components.items():
            if component:
                logging.info(f"Componente {name} encontrado")
            else:
                logging.warning(f"Componente {name} no encontrado")
    
  
    
    def ensure_db_connection(self):
        """Asegura que tenemos una conexión válida a la base de datos."""
        if self.conn and hasattr(self.conn, 'cursor'):
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT 1")
                return True
            except sqlite3.Error:
                logging.error("Prueba de conexión a la base de datos fallida")
        
        # Si llegamos aquí, la conexión no es válida
        if hasattr(self.parent, 'ensure_db_connection'):
            # Intentar obtener una conexión del padre
            if self.parent.ensure_db_connection():
                self.conn = self.parent.conn
                return True
        
        logging.error("No hay conexión válida disponible a la base de datos")
        return False
    
    def load_artist_list(self):
        """Carga la lista de artistas desde la base de datos."""
        if not self.ensure_db_connection():
            return
        
        cursor = self.conn.cursor()
        try:
            # Consultar los artistas con conteo de álbumes y ordenarlos por total de álbumes
            cursor.execute("""
                SELECT 
                    a.id, 
                    a.name, 
                    a.origin,
                    a.formed_year,
                    a.total_albums,
                    COUNT(DISTINCT dd.album_name) as discogs_albums,
                    COUNT(DISTINCT s.id) as setlist_count
                FROM 
                    artists a
                LEFT JOIN 
                    discogs_discography dd ON a.id = dd.artist_id
                LEFT JOIN 
                    artists_setlistfm s ON a.id = s.artist_id
                GROUP BY 
                    a.id
                ORDER BY 
                    COALESCE(a.total_albums, 0) DESC, 
                    discogs_albums DESC,
                    a.name
                LIMIT 10000;
            """)
            
            self.artist_list = cursor.fetchall()
            logging.info(f"Cargados {len(self.artist_list)} artistas")
            
        except Exception as e:
            logging.error(f"Error al cargar la lista de artistas: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self.artist_list = []
    
    def setup_artists_table(self):
        """Configura la tabla de artistas con la lista cargada."""
        if not self.table_artists or not self.artist_list:
            return
        
        try:
            # Importar el widget de tabla numérica
            from modules.submodules.muspy.table_widgets import NumericTableWidgetItem
            
            # Configurar las columnas
            self.table_artists.setColumnCount(4)
            self.table_artists.setHorizontalHeaderLabels(["Artista", "Origen", "Año", "Álbumes"])
            
            # Configurar comportamiento
            self.table_artists.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table_artists.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table_artists.setAlternatingRowColors(True)
            
            # Llenar los datos
            self.table_artists.setRowCount(len(self.artist_list))
            for i, artist in enumerate(self.artist_list):
                if isinstance(artist, sqlite3.Row):
                    artist_id = artist['id']
                    name = artist['name']
                    origin = artist['origin'] or ""
                    formed_year = artist['formed_year'] or ""
                    albums = artist['total_albums'] or artist['discogs_albums'] or 0
                else:  # Tupla
                    artist_id, name, origin, formed_year, albums, discogs_albums, _ = artist
                    if not albums:
                        albums = discogs_albums or 0
                
                # Limitar a 30 caracteres
                name_limited = name[:30] + "..." if len(str(name)) > 30 else name
                origin_limited = origin[:30] + "..." if len(str(origin)) > 30 else origin
                
                # Asignar texto limitado a las celdas
                self.table_artists.setItem(i, 0, QTableWidgetItem(name_limited))
                self.table_artists.setItem(i, 1, QTableWidgetItem(str(origin_limited)))
                
                # Usar NumericTableWidgetItem para columnas numéricas
                self.table_artists.setItem(i, 2, NumericTableWidgetItem(str(formed_year)))
                self.table_artists.setItem(i, 3, NumericTableWidgetItem(str(albums)))
                
                # Guardar el nombre completo en los datos de la celda para usarlo cuando se seleccione
                self.table_artists.item(i, 0).setData(Qt.ItemDataRole.UserRole, name)
            
            # Ajustar ancho de columnas
            self.table_artists.resizeColumnsToContents()
            
        except Exception as e:
            logging.error(f"Error al configurar la tabla de artistas: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def init_stacked_widget_pages(self):
        """Inicializa las páginas en el stackedWidget para mostrar diferentes estadísticas."""
        if not self.stacked_widget:
            return
        
        # Si el stacked widget no tiene páginas, añadirlas
        while self.stacked_widget.count() < 9:
            # Crear una página para cada tipo de estadística
            page = QWidget()
            layout = QVBoxLayout(page)
            
            # Añadir un título inicial
            title = QLabel("Selecciona un artista para ver estadísticas")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("font-size: 16px; font-weight: bold;")
            layout.addWidget(title)
            
            self.stacked_widget.addWidget(page)
    
    def on_artist_selected(self, item):
        """Maneja la selección de un artista en la tabla."""
        if not self.table_artists:
            return
        
        row = item.row()
        artist_name = self.table_artists.item(row, 0).text()
        
        # Almacenar el artista seleccionado
        self.selected_artist = artist_name
        
        # Actualizar el label con el nombre del artista
        if hasattr(self.parent, 'artista_label'):
            self.parent.artista_label.setText(f"Artista: {artist_name}")
        
        # Obtener el ID del artista
        if len(self.artist_list) > row:
            artist_data = self.artist_list[row]
            if isinstance(artist_data, sqlite3.Row):
                self.selected_artist_id = artist_data['id']
            else:  # Tupla
                self.selected_artist_id = artist_data[0]
        else:
            # Buscar el ID en la base de datos
            self.selected_artist_id = self.get_artist_id(artist_name)
        
        logging.info(f"Artista seleccionado: {artist_name} (ID: {self.selected_artist_id})")
        
        # Resaltar la fila seleccionada
        self.highlight_selected_artist(row)
        
        # Cambiar a la primera página del stackedWidget_24 si existe
        if hasattr(self.parent, 'stackedWidget_24'):
            self.parent.stackedWidget_24.setCurrentIndex(0)
        
        # Mostrar estadísticas básicas (por defecto, mostrar la vista de tiempo)
        self.show_time_stats()
    

    def home_stats(self):
        """Muestra la vista inicial (tabla de artistas) en el stackedWidget."""
        if hasattr(self.parent, 'stackedWidget_24'):
            self.parent.stackedWidget_24.setCurrentIndex(0)
        
        if self.selected_artist:
            # Actualizar el título con el nombre del artista seleccionado
            if hasattr(self.parent, 'artista_label'):
                self.parent.artista_label.setText(f"Artista: {self.selected_artist}")

    def get_artist_id(self, artist_name):
        """Obtiene el ID de un artista a partir de su nombre."""
        if not self.ensure_db_connection():
            return None
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT id FROM artists WHERE name = ?", (artist_name,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logging.error(f"Error al obtener ID del artista: {e}")
            return None
    
    def highlight_selected_artist(self, selected_row):
        """Resalta la fila del artista seleccionado en la tabla."""
        if not self.table_artists:
            return
            
        highlight_color = QColor("#e0f2f1")  # Color suave para la fila seleccionada
        normal_color = QColor("#ffffff")     # Color para las filas no seleccionadas
        
        for row in range(self.table_artists.rowCount()):
            for col in range(self.table_artists.columnCount()):
                item = self.table_artists.item(row, col)
                if item:
                    if row == selected_row:
                        item.setBackground(QBrush(highlight_color))
                    else:
                        # Mantener el color alternante si está activado
                        if not self.table_artists.alternatingRowColors() or row % 2 == 0:
                            item.setBackground(QBrush(normal_color))
    
    def show_time_stats(self):
        """Muestra estadísticas de tiempo para el artista seleccionado."""
        if not self.selected_artist or not self.selected_artist_id:
            return
        
        # Asegurarse de que estamos en la primera página del stacked widget
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(0)
        
        # Obtener la página actual
        current_page = self.stacked_widget.currentWidget()
        if not current_page:
            return
        
        # Limpiar la página
        layout = self.ensure_widget_has_layout(current_page)
        self.clear_layout(layout)
        
        # Añadir título
        title = QLabel(f"Distribución Temporal - {self.selected_artist}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un splitter para organizar los gráficos
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Añadir widget para gráfico por décadas
        decades_widget = QWidget()
        decades_layout = QVBoxLayout(decades_widget)
        decades_title = QLabel("Álbumes por Década")
        decades_title.setStyleSheet("font-weight: bold;")
        decades_layout.addWidget(decades_title)
        
        # Contenedor para el gráfico de décadas
        decades_chart_container = QWidget()
        decades_chart_layout = QVBoxLayout(decades_chart_container)
        decades_layout.addWidget(decades_chart_container)
        
        # Añadir widget para gráfico por años
        years_widget = QWidget()
        years_layout = QVBoxLayout(years_widget)
        years_title = QLabel("Álbumes por Año")
        years_title.setStyleSheet("font-weight: bold;")
        years_layout.addWidget(years_title)
        
        # Contenedor para el gráfico de años
        years_chart_container = QWidget()
        years_chart_layout = QVBoxLayout(years_chart_container)
        years_layout.addWidget(years_chart_container)
        
        # Añadir los widgets al splitter
        splitter.addWidget(decades_widget)
        splitter.addWidget(years_widget)
        
        # Añadir el splitter al layout principal
        layout.addWidget(splitter)
        
        # Cargar y mostrar los datos
        self.load_artist_decade_data(decades_chart_layout)
        self.load_artist_year_data(years_chart_layout)
    
    def load_artist_decade_data(self, layout):
        """Carga y muestra un gráfico circular con álbumes por década."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Intentar obtener datos de discogs primero
            cursor.execute("""
                SELECT 
                    (year / 10) * 10 as decade, 
                    COUNT(*) as album_count
                FROM 
                    discogs_discography
                WHERE 
                    artist_id = ? AND
                    year IS NOT NULL AND
                    year > 0
                GROUP BY 
                    decade
                ORDER BY 
                    decade;
            """, (self.selected_artist_id,))
            
            decade_data = cursor.fetchall()
            
            # Si no hay datos de discogs, intentar con la tabla albums
            if not decade_data:
                cursor.execute("""
                    SELECT 
                        (CAST(SUBSTR(year, 1, 4) AS INTEGER) / 10) * 10 as decade, 
                        COUNT(*) as album_count
                    FROM 
                        albums
                    WHERE 
                        artist_id = ? AND
                        year IS NOT NULL AND 
                        year != '' AND
                        LENGTH(year) >= 4 AND
                        CAST(SUBSTR(year, 1, 4) AS INTEGER) > 0
                    GROUP BY 
                        decade
                    ORDER BY 
                        decade;
                """, (self.selected_artist_id,))
                
                decade_data = cursor.fetchall()
            
            # Crear el gráfico si hay datos
            if decade_data:
                # Formatear los datos para el gráfico
                chart_data = [(f"{decade}s", count) for decade, count in decade_data]
                
                # Crear gráfico circular
                chart_view = ChartFactory.create_pie_chart(
                    chart_data,
                    f"Distribución de Álbumes por Década - {self.selected_artist}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay datos de décadas disponibles para este artista")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de décadas: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def load_artist_year_data(self, layout):
        """Carga y muestra un gráfico de barras con álbumes por año."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener datos de discogs primero (con nombres de álbumes)
            cursor.execute("""
                SELECT 
                    year, 
                    album_name
                FROM 
                    discogs_discography
                WHERE 
                    artist_id = ? AND
                    year IS NOT NULL AND
                    year > 0
                ORDER BY 
                    year;
            """, (self.selected_artist_id,))
            
            year_data = cursor.fetchall()
            
            # Si no hay datos de discogs, intentar con la tabla albums
            if not year_data:
                cursor.execute("""
                    SELECT 
                        CAST(SUBSTR(year, 1, 4) AS INTEGER) as release_year, 
                        name as album_name
                    FROM 
                        albums
                    WHERE 
                        artist_id = ? AND
                        year IS NOT NULL AND 
                        year != '' AND
                        LENGTH(year) >= 4 AND
                        CAST(SUBSTR(year, 1, 4) AS INTEGER) > 0
                    ORDER BY 
                        release_year;
                """, (self.selected_artist_id,))
                
                year_data = cursor.fetchall()
            
            # Crear el gráfico si hay datos
            if year_data:
                # Agrupar álbumes por año
                albums_by_year = {}
                
                for year, album in year_data:
                    try:
                        year_int = int(year)
                        
                        if year_int not in albums_by_year:
                            albums_by_year[year_int] = []
                        albums_by_year[year_int].append(album)
                    except (ValueError, TypeError):
                        # Ignorar años que no se pueden convertir a entero
                        pass
                
                # Obtener todos los años que tienen al menos un álbum, ordenados
                all_years = sorted(albums_by_year.keys())
                
                if not all_years:
                    no_data = QLabel("No hay datos de años válidos para este artista")
                    no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_data)
                    return
                
                min_year = min(all_years)
                max_year = max(all_years)
                
                # Determinar los años a mostrar en el gráfico
                max_bars = 20  # Número máximo de barras a mostrar
                logging.info(f"Años totales con álbumes: {len(all_years)}, rango: {min_year}-{max_year}")
                
                # Algoritmo mejorado para seleccionar exactamente max_bars puntos para el gráfico
                if len(all_years) <= max_bars:
                    # Si tenemos menos o igual que max_bars años, mostrarlos todos
                    years_to_show = all_years
                else:
                    # Siempre incluir el primer y último año
                    years_to_show = []
                    
                    # Calcular el paso para distribuir max_bars puntos uniformemente
                    # entre min_year y max_year (inclusive)
                    step = (max_year - min_year) / (max_bars - 1)
                    
                    for i in range(max_bars):
                        # Calcular el año objetivo en este paso
                        if i == 0:
                            target_year = min_year
                        elif i == max_bars - 1:
                            target_year = max_year
                        else:
                            target_year = int(min_year + i * step)
                        
                        # Encontrar el año más cercano en all_years
                        closest_year = min(all_years, key=lambda y: abs(y - target_year))
                        
                        # Solo añadir si no está ya en la lista
                        if closest_year not in years_to_show:
                            years_to_show.append(closest_year)
                
                # Ordenar los años seleccionados
                years_to_show.sort()
                
                logging.info(f"Mostrando {len(years_to_show)} años en el gráfico de barras")
                
                # Preparar datos para el gráfico
                chart_data = [(str(year), len(albums_by_year[year])) for year in years_to_show]
                
                # Crear gráfico de barras
                chart_view = ChartFactory.create_bar_chart(
                    chart_data,
                    f"Álbumes por Año - {self.selected_artist}",
                    x_label="Año",
                    y_label="Número de Álbumes"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    
                    # Añadir una tabla con TODOS los álbumes para cada año
                    albums_table = QTableWidget()
                    albums_table.setColumnCount(2)
                    albums_table.setHorizontalHeaderLabels(["Año", "Álbumes"])
                    
                    # Importar NumericTableWidgetItem para ordenación numérica
                    from modules.submodules.muspy.table_widgets import NumericTableWidgetItem
                    
                    # Llenar la tabla con TODOS los años que tengan álbumes
                    albums_table.setRowCount(len(all_years))
                    
                    for i, year in enumerate(all_years):
                        albums = albums_by_year[year]
                        albums_table.setItem(i, 0, NumericTableWidgetItem(str(year)))
                        
                        # Limitar el número de álbumes mostrados si hay muchos
                        if len(albums) > 10:
                            albums_text = ", ".join(albums[:10]) + f"... ({len(albums)} total)"
                        else:
                            albums_text = ", ".join(albums)
                        
                        albums_table.setItem(i, 1, QTableWidgetItem(albums_text))
                    
                    # Ordenar tabla por año para que coincida con el gráfico
                    albums_table.sortItems(0, Qt.SortOrder.AscendingOrder)
                    albums_table.resizeColumnsToContents()
                    layout.addWidget(albums_table)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay datos de años disponibles para este artista")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de años: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def show_concert_stats(self):
        """Muestra estadísticas de conciertos para el artista seleccionado."""
        if not self.selected_artist or not self.selected_artist_id:
            return
        
        # Asegurarse de que estamos en la segunda página del stacked widget
        if self.stacked_widget:
            if self.stacked_widget.count() > 1:
                self.stacked_widget.setCurrentIndex(1)
            else:
                self.stacked_widget.setCurrentIndex(0)
        
        # Obtener la página actual
        current_page = self.stacked_widget.currentWidget()
        if not current_page:
            return
        
        # Limpiar la página
        layout = self.ensure_widget_has_layout(current_page)
        self.clear_layout(layout)
        
        # Añadir título
        title = QLabel(f"Estadísticas de Conciertos - {self.selected_artist}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un stacked widget para navegación entre vistas
        concert_stacked = QStackedWidget()
        
        # Páginas para las diferentes vistas
        dates_page = QWidget()
        dates_layout = QVBoxLayout(dates_page)
        
        countries_page = QWidget()
        countries_layout = QVBoxLayout(countries_page)
        
        # Añadir páginas al stacked widget
        concert_stacked.addWidget(dates_page)
        concert_stacked.addWidget(countries_page)
        
        # Añadir el stacked widget al layout principal
        layout.addWidget(concert_stacked)
        
        # Crear botones de navegación
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        
        dates_button = QPushButton("Fechas")
        dates_button.clicked.connect(lambda: concert_stacked.setCurrentIndex(0))
        
        countries_button = QPushButton("Países")
        countries_button.clicked.connect(lambda: concert_stacked.setCurrentIndex(1))
        
        button_layout.addWidget(dates_button)
        button_layout.addWidget(countries_button)
        button_layout.addStretch()
        
        # Añadir botones al layout principal
        layout.addWidget(button_container)
        
        # Cargar los datos para la página de fechas
        self.load_concert_dates(dates_layout)
        
        # Cargar los datos para la página de países
        self.load_concert_country_data(countries_layout)
        
        # Por defecto, mostrar la página de fechas
        concert_stacked.setCurrentIndex(0)
    
    # Modificación a la función load_concert_dates para corregir el formato de fecha
    def load_concert_dates(self, layout):
        """Carga y muestra gráficos y tablas con conciertos por mes y por año."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Crear un splitter vertical para separar las secciones de año y mes
            dates_splitter = QSplitter(Qt.Orientation.Vertical)
            
            # Contenedor para la sección de años
            years_container = QWidget()
            years_layout = QVBoxLayout(years_container)
            years_title = QLabel("Conciertos por Año")
            years_title.setStyleSheet("font-weight: bold;")
            years_layout.addWidget(years_title)
            
            # Contenedor para el gráfico y la tabla de años
            years_data_container = QWidget()
            years_data_layout = QHBoxLayout(years_data_container)
            
            # Contenedor para el gráfico de años
            years_chart_container = QWidget()
            years_chart_layout = QVBoxLayout(years_chart_container)
            
            # Contenedor para la tabla de años
            years_table_container = QWidget()
            years_table_layout = QVBoxLayout(years_table_container)
            
            # Tabla para años
            years_table = QTableWidget()
            years_table.setColumnCount(2)
            years_table.setHorizontalHeaderLabels(["Año", "Conciertos"])
            years_table_layout.addWidget(years_table)
            
            # Añadir contenedores al layout de datos de años
            years_data_layout.addWidget(years_chart_container)
            years_data_layout.addWidget(years_table_container)
            
            # Añadir el contenedor de datos al layout de años
            years_layout.addWidget(years_data_container)
            
            # Contenedor para la sección de meses
            months_container = QWidget()
            months_layout = QVBoxLayout(months_container)
            months_title = QLabel("Conciertos por Mes")
            months_title.setStyleSheet("font-weight: bold;")
            months_layout.addWidget(months_title)
            
            # Contenedor para el gráfico y la tabla de meses
            months_data_container = QWidget()
            months_data_layout = QHBoxLayout(months_data_container)
            
            # Contenedor para el gráfico de meses
            months_chart_container = QWidget()
            months_chart_layout = QVBoxLayout(months_chart_container)
            
            # Contenedor para la tabla de meses
            months_table_container = QWidget()
            months_table_layout = QVBoxLayout(months_table_container)
            
            # Tabla para meses
            months_table = QTableWidget()
            months_table.setColumnCount(2)
            months_table.setHorizontalHeaderLabels(["Mes", "Conciertos"])
            months_table_layout.addWidget(months_table)
            
            # Añadir contenedores al layout de datos de meses
            months_data_layout.addWidget(months_chart_container)
            months_data_layout.addWidget(months_table_container)
            
            # Añadir el contenedor de datos al layout de meses
            months_layout.addWidget(months_data_container)
            
            # Añadir contenedores al splitter
            dates_splitter.addWidget(years_container)
            dates_splitter.addWidget(months_container)
            
            # Añadir el splitter al layout principal
            layout.addWidget(dates_splitter)
            
            # Cargar datos de conciertos por año
            cursor.execute("""
                SELECT 
                    SUBSTR(eventDate, 7, 4) as year, 
                    COUNT(*) as concert_count
                FROM 
                    artists_setlistfm
                WHERE 
                    artist_id = ? AND
                    eventDate IS NOT NULL AND
                    eventDate != ''
                GROUP BY 
                    year
                ORDER BY 
                    year;
            """, (self.selected_artist_id,))
            
            year_data = cursor.fetchall()
            
            # Procesar y mostrar datos de años
            if year_data:
                # Llenar la tabla de años
                years_table.setRowCount(len(year_data))
                for i, (year, count) in enumerate(year_data):
                    years_table.setItem(i, 0, QTableWidgetItem(year))
                    years_table.setItem(i, 1, QTableWidgetItem(str(count)))
                
                years_table.resizeColumnsToContents()
                
                # Crear gráfico de barras vertical para años
                years_chart = ChartFactory.create_bar_chart(
                    year_data,
                    f"Conciertos por Año - {self.selected_artist}",
                    x_label="Año",
                    y_label="Número de Conciertos"
                )
                
                if years_chart:
                    years_chart_layout.addWidget(years_chart)
            else:
                no_year_data = QLabel("No hay datos de conciertos por año disponibles")
                no_year_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                years_chart_layout.addWidget(no_year_data)
            
            # Cargar datos de conciertos por mes
            cursor.execute("""
                SELECT 
                    SUBSTR(eventDate, 4, 2) as month, 
                    COUNT(*) as concert_count
                FROM 
                    artists_setlistfm
                WHERE 
                    artist_id = ? AND
                    eventDate IS NOT NULL AND
                    eventDate != ''
                GROUP BY 
                    month
                ORDER BY 
                    month;
            """, (self.selected_artist_id,))
            
            month_data = cursor.fetchall()
            
            # Procesar y mostrar datos de meses
            if month_data:
                # Convertir números de mes a nombres
                month_names = [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ]
                
                named_month_data = []
                for month_num, count in month_data:
                    try:
                        month_idx = int(month_num) - 1  # Ajustar a índice base 0
                        if 0 <= month_idx < 12:
                            month_name = month_names[month_idx]
                            named_month_data.append((month_name, count))
                        else:
                            named_month_data.append((f"Mes {month_num}", count))
                    except (ValueError, IndexError):
                        named_month_data.append((f"Mes {month_num}", count))
                
                # Llenar la tabla de meses
                months_table.setRowCount(len(named_month_data))
                for i, (month, count) in enumerate(named_month_data):
                    months_table.setItem(i, 0, QTableWidgetItem(month))
                    months_table.setItem(i, 1, QTableWidgetItem(str(count)))
                
                months_table.resizeColumnsToContents()
                
                # Crear gráfico de barras para meses
                months_chart = ChartFactory.create_bar_chart(
                    named_month_data,
                    f"Conciertos por Mes - {self.selected_artist}",
                    x_label="Mes",
                    y_label="Número de Conciertos"
                )
                
                if months_chart:
                    months_chart_layout.addWidget(months_chart)
            else:
                no_month_data = QLabel("No hay datos de conciertos por mes disponibles")
                no_month_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                months_chart_layout.addWidget(no_month_data)
        
        except Exception as e:
            logging.error(f"Error al cargar datos de conciertos por fecha: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)


    def load_concert_country_data(self, layout):
        """Carga y muestra un gráfico circular con conciertos por país."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Contenedor para el gráfico y la tabla
            countries_container = QWidget()
            countries_layout = QHBoxLayout(countries_container)
            
            # Contenedor para el gráfico
            chart_container = QWidget()
            chart_layout = QVBoxLayout(chart_container)
            chart_title = QLabel("Distribución por País")
            chart_title.setStyleSheet("font-weight: bold;")
            chart_layout.addWidget(chart_title)
            
            # Contenedor para la tabla
            table_container = QWidget()
            table_layout = QVBoxLayout(table_container)
            table_title = QLabel("Detalles por País")
            table_title.setStyleSheet("font-weight: bold;")
            table_layout.addWidget(table_title)
            
            # Añadir contenedores al layout principal
            countries_layout.addWidget(chart_container)
            countries_layout.addWidget(table_container)
            
            # Añadir el contenedor principal al layout
            layout.addWidget(countries_container)
            
            # Obtener datos de conciertos por país
            cursor.execute("""
                SELECT 
                    country_name, 
                    COUNT(*) as concert_count
                FROM 
                    artists_setlistfm
                WHERE 
                    artist_id = ? AND
                    country_name IS NOT NULL AND
                    country_name != ''
                GROUP BY 
                    country_name
                ORDER BY 
                    concert_count DESC;
            """, (self.selected_artist_id,))
            
            country_data = cursor.fetchall()
            
            # Crear el gráfico si hay datos
            if country_data:
                # Crear gráfico circular
                chart_view = ChartFactory.create_pie_chart(
                    country_data,
                    f"Conciertos por País - {self.selected_artist}"
                )
                
                if chart_view:
                    chart_layout.addWidget(chart_view)
                    
                    # Crear tabla con detalles
                    table = QTableWidget()
                    table.setColumnCount(3)
                    table.setHorizontalHeaderLabels(["País", "Conciertos", "Ciudades"])
                    table.setRowCount(len(country_data))
                    
                    # Para cada país, obtener las ciudades
                    for i, (country, count) in enumerate(country_data):
                        # Consultar ciudades
                        cursor.execute("""
                            SELECT 
                                city_name, 
                                COUNT(*) as concert_count
                            FROM 
                                artists_setlistfm
                            WHERE 
                                artist_id = ? AND
                                country_name = ?
                            GROUP BY 
                                city_name
                            ORDER BY 
                                concert_count DESC
                            LIMIT 5;
                        """, (self.selected_artist_id, country))
                        
                        cities = cursor.fetchall()
                        city_names = ", ".join([f"{city} ({count})" for city, count in cities])
                        
                        # Añadir a la tabla
                        table.setItem(i, 0, QTableWidgetItem(country))
                        table.setItem(i, 1, QTableWidgetItem(str(count)))
                        table.setItem(i, 2, QTableWidgetItem(city_names))
                    
                    table.resizeColumnsToContents()
                    table_layout.addWidget(table)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    chart_layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay datos de conciertos por país disponibles")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chart_layout.addWidget(no_data)
                    
        except Exception as e:
            logging.error(f"Error al cargar datos de conciertos por país: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)

    def load_concert_year_data(self, layout):
        """Carga y muestra un gráfico de barras con conciertos por año."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener datos de conciertos por año
            cursor.execute("""
                SELECT 
                    SUBSTR(eventDate, 1, 4) as year, 
                    COUNT(*) as concert_count
                FROM 
                    artists_setlistfm
                WHERE 
                    artist_id = ? AND
                    eventDate IS NOT NULL AND
                    eventDate != ''
                GROUP BY 
                    year
                ORDER BY 
                    year;
            """, (self.selected_artist_id,))
            
            year_data = cursor.fetchall()
            
            # Crear el gráfico si hay datos
            if year_data:
                # Crear gráfico de barras
                chart_view = ChartFactory.create_bar_chart(
                    year_data,
                    f"Conciertos por Año - {self.selected_artist}",
                    x_label="Año",
                    y_label="Número de Conciertos"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay datos de conciertos por año disponibles para este artista")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de conciertos por año: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def load_concert_country_data(self, layout):
        """Carga y muestra un gráfico circular con conciertos por país."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener datos de conciertos por país
            cursor.execute("""
                SELECT 
                    country_name, 
                    COUNT(*) as concert_count
                FROM 
                    artists_setlistfm
                WHERE 
                    artist_id = ? AND
                    country_name IS NOT NULL AND
                    country_name != ''
                GROUP BY 
                    country_name
                ORDER BY 
                    concert_count DESC;
            """, (self.selected_artist_id,))
            
            country_data = cursor.fetchall()
            
            # Crear el gráfico si hay datos
            if country_data:
                # Crear gráfico circular
                chart_view = ChartFactory.create_pie_chart(
                    country_data,
                    f"Conciertos por País - {self.selected_artist}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    
                    # Añadir tabla con detalles
                    table = QTableWidget()
                    table.setColumnCount(3)
                    table.setHorizontalHeaderLabels(["País", "Conciertos", "Ciudades"])
                    table.setRowCount(len(country_data))
                    
                    # Para cada país, obtener las ciudades
                    for i, (country, count) in enumerate(country_data):
                        # Consultar ciudades
                        cursor.execute("""
                            SELECT 
                                city_name, 
                                COUNT(*) as concert_count
                            FROM 
                                artists_setlistfm
                            WHERE 
                                artist_id = ? AND
                                country_name = ?
                            GROUP BY 
                                city_name
                            ORDER BY 
                                concert_count DESC
                            LIMIT 5;
                        """, (self.selected_artist_id, country))
                        
                        cities = cursor.fetchall()
                        city_names = ", ".join([f"{city} ({count})" for city, count in cities])
                        
                        # Añadir a la tabla
                        table.setItem(i, 0, QTableWidgetItem(country))
                        table.setItem(i, 1, QTableWidgetItem(str(count)))
                        table.setItem(i, 2, QTableWidgetItem(city_names))
                    
                    table.resizeColumnsToContents()
                    layout.addWidget(table)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay datos de conciertos por país disponibles para este artista")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de conciertos por país: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def show_genre_stats(self):
        """Muestra estadísticas de géneros para el artista seleccionado."""
        if not self.selected_artist or not self.selected_artist_id:
            return
        
        # Asegurarse de que estamos en la tercera página del stacked widget
        if self.stacked_widget:
            if self.stacked_widget.count() > 2:
                self.stacked_widget.setCurrentIndex(2)
            else:
                self.stacked_widget.setCurrentIndex(0)
        
        # Obtener la página actual
        current_page = self.stacked_widget.currentWidget()
        if not current_page:
            return
        
        # Limpiar la página
        layout = self.ensure_widget_has_layout(current_page)
        self.clear_layout(layout)
        
        # Añadir título
        title = QLabel(f"Distribución de Géneros - {self.selected_artist}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un splitter para organizar los gráficos
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Crear contenedores para los cuatro gráficos
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        
        # Contenedor para géneros de discogs
        discogs_genres_widget = QWidget()
        discogs_genres_layout = QVBoxLayout(discogs_genres_widget)
        discogs_genres_title = QLabel("Géneros (Discogs)")
        discogs_genres_title.setStyleSheet("font-weight: bold;")
        discogs_genres_layout.addWidget(discogs_genres_title)
        
        discogs_genres_chart = QWidget()
        discogs_genres_chart_layout = QVBoxLayout(discogs_genres_chart)
        discogs_genres_layout.addWidget(discogs_genres_chart)
        
        # Contenedor para estilos de discogs
        discogs_styles_widget = QWidget()
        discogs_styles_layout = QVBoxLayout(discogs_styles_widget)
        discogs_styles_title = QLabel("Estilos (Discogs)")
        discogs_styles_title.setStyleSheet("font-weight: bold;")
        discogs_styles_layout.addWidget(discogs_styles_title)
        
        discogs_styles_chart = QWidget()
        discogs_styles_chart_layout = QVBoxLayout(discogs_styles_chart)
        discogs_styles_layout.addWidget(discogs_styles_chart)
        
        # Añadir widgets a la fila superior
        top_layout.addWidget(discogs_genres_widget)
        top_layout.addWidget(discogs_styles_widget)
        
        # Segunda fila
        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        
        # Contenedor para géneros de álbumes
        album_genres_widget = QWidget()
        album_genres_layout = QVBoxLayout(album_genres_widget)
        album_genres_title = QLabel("Géneros (Álbumes)")
        album_genres_title.setStyleSheet("font-weight: bold;")
        album_genres_layout.addWidget(album_genres_title)
        
        album_genres_chart = QWidget()
        album_genres_chart_layout = QVBoxLayout(album_genres_chart)
        album_genres_layout.addWidget(album_genres_chart)
        
        # Contenedor para etiquetas de artistas
        artist_tags_widget = QWidget()
        artist_tags_layout = QVBoxLayout(artist_tags_widget)
        artist_tags_title = QLabel("Etiquetas (lastfm)")
        artist_tags_title.setStyleSheet("font-weight: bold;")
        artist_tags_layout.addWidget(artist_tags_title)
        
        artist_tags_chart = QWidget()
        artist_tags_chart_layout = QVBoxLayout(artist_tags_chart)
        artist_tags_layout.addWidget(artist_tags_chart)
        
        # Añadir widgets a la fila inferior
        bottom_layout.addWidget(album_genres_widget)
        bottom_layout.addWidget(artist_tags_widget)
        
        # Añadir filas al splitter
        splitter.addWidget(top_row)
        splitter.addWidget(bottom_row)
        
        # Añadir splitter al layout principal
        layout.addWidget(splitter)
        
        # Cargar y mostrar datos
        self.load_discogs_genres_data(discogs_genres_chart_layout)
        self.load_discogs_styles_data(discogs_styles_chart_layout)
        self.load_album_genres_data(album_genres_chart_layout)
        self.load_artist_tags_data(artist_tags_chart_layout)
    
    def load_discogs_genres_data(self, layout):
        """Carga y muestra un gráfico circular con géneros de Discogs."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener datos de géneros de Discogs
            cursor.execute("""
                SELECT 
                    genres
                FROM 
                    discogs_discography
                WHERE 
                    artist_id = ? AND
                    genres IS NOT NULL AND
                    genres != ''
            """, (self.selected_artist_id,))
            
            genres_data = cursor.fetchall()
            
            # Procesar los datos JSON
            genre_counts = {}
            for genres_json, in genres_data:
                try:
                    if genres_json:
                        genres = json.loads(genres_json)
                        if isinstance(genres, list):
                            for genre in genres:
                                if genre in genre_counts:
                                    genre_counts[genre] += 1
                                else:
                                    genre_counts[genre] = 1
                except json.JSONDecodeError:
                    # Intentar dividir por comas si no es JSON válido
                    if genres_json and ',' in genres_json:
                        for genre in genres_json.split(','):
                            genre = genre.strip()
                            if genre:
                                if genre in genre_counts:
                                    genre_counts[genre] += 1
                                else:
                                    genre_counts[genre] = 1
                    elif genres_json:
                        # Si es un solo valor sin comas
                        genre = genres_json.strip()
                        if genre in genre_counts:
                            genre_counts[genre] += 1
                        else:
                            genre_counts[genre] = 1
            
            # Crear el gráfico si hay datos
            if genre_counts:
                # Convertir a formato para gráfico
                chart_data = [(genre, count) for genre, count in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)]
                
                # Limitar a los 15 principales para mejor visualización
                if len(chart_data) > 15:
                    chart_data = chart_data[:15]
                
                # Crear gráfico circular
                chart_view = ChartFactory.create_pie_chart(
                    chart_data,
                    f"Géneros (Discogs) - {self.selected_artist}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay datos de géneros de Discogs disponibles")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de géneros de Discogs: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def load_discogs_styles_data(self, layout):
        """Carga y muestra un gráfico circular con estilos de Discogs."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener datos de estilos de Discogs
            cursor.execute("""
                SELECT 
                    styles
                FROM 
                    discogs_discography
                WHERE 
                    artist_id = ? AND
                    styles IS NOT NULL AND
                    styles != ''
            """, (self.selected_artist_id,))
            
            styles_data = cursor.fetchall()
            
            # Procesar los datos JSON
            style_counts = {}
            for styles_json, in styles_data:
                try:
                    if styles_json:
                        styles = json.loads(styles_json)
                        if isinstance(styles, list):
                            for style in styles:
                                if style in style_counts:
                                    style_counts[style] += 1
                                else:
                                    style_counts[style] = 1
                except json.JSONDecodeError:
                    # Intentar dividir por comas si no es JSON válido
                    if styles_json and ',' in styles_json:
                        for style in styles_json.split(','):
                            style = style.strip()
                            if style:
                                if style in style_counts:
                                    style_counts[style] += 1
                                else:
                                    style_counts[style] = 1
                    elif styles_json:
                        # Si es un solo valor sin comas
                        style = styles_json.strip()
                        if style in style_counts:
                            style_counts[style] += 1
                        else:
                            style_counts[style] = 1
            
            # Crear el gráfico si hay datos
            if style_counts:
                # Convertir a formato para gráfico
                chart_data = [(style, count) for style, count in sorted(style_counts.items(), key=lambda x: x[1], reverse=True)]
                
                # Limitar a los 15 principales para mejor visualización
                if len(chart_data) > 15:
                    chart_data = chart_data[:15]
                
                # Crear gráfico circular
                chart_view = ChartFactory.create_pie_chart(
                    chart_data,
                    f"Estilos (Discogs) - {self.selected_artist}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay datos de estilos de Discogs disponibles")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de estilos de Discogs: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def load_album_genres_data(self, layout):
        """Carga y muestra un gráfico circular con géneros de álbumes."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener datos de géneros de álbumes
            cursor.execute("""
                SELECT 
                    genre, 
                    COUNT(*) as genre_count
                FROM 
                    albums
                WHERE 
                    artist_id = ? AND
                    genre IS NOT NULL AND
                    genre != ''
                GROUP BY 
                    genre
                ORDER BY 
                    genre_count DESC;
            """, (self.selected_artist_id,))
            
            genre_data = cursor.fetchall()
            
            # Crear el gráfico si hay datos
            if genre_data:
                # Crear gráfico circular
                chart_view = ChartFactory.create_pie_chart(
                    genre_data,
                    f"Géneros de Álbumes - {self.selected_artist}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay datos de géneros de álbumes disponibles")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de géneros de álbumes: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def load_artist_tags_data(self, layout):
        """Carga y muestra un gráfico circular con etiquetas del artista."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener tags del artista
            cursor.execute("""
                SELECT 
                    tags
                FROM 
                    artists
                WHERE 
                    id = ? AND
                    tags IS NOT NULL AND
                    tags != ''
            """, (self.selected_artist_id,))
            
            tags_data = cursor.fetchone()
            
            if tags_data and tags_data[0]:
                tags_str = tags_data[0]
                
                # Intentar procesar como JSON primero
                tag_counts = {}
                try:
                    tags = json.loads(tags_str)
                    if isinstance(tags, list):
                        for tag in tags:
                            if tag in tag_counts:
                                tag_counts[tag] += 1
                            else:
                                tag_counts[tag] = 1
                    elif isinstance(tags, dict):
                        # Si es un diccionario con pesos
                        for tag, weight in tags.items():
                            tag_counts[tag] = weight
                except json.JSONDecodeError:
                    # Intentar dividir por comas si no es JSON válido
                    if ',' in tags_str:
                        for tag in tags_str.split(','):
                            tag = tag.strip()
                            if tag:
                                if tag in tag_counts:
                                    tag_counts[tag] += 1
                                else:
                                    tag_counts[tag] = 1
                    else:
                        # Si es un solo valor sin comas
                        tag_counts[tags_str.strip()] = 1
                
                # Crear gráfico si hay datos
                if tag_counts:
                    # Convertir a formato para gráfico
                    chart_data = [(tag, count) for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)]
                    
                    # Limitar a los 15 principales para mejor visualización
                    if len(chart_data) > 15:
                        chart_data = chart_data[:15]
                    
                    # Crear gráfico circular
                    chart_view = ChartFactory.create_pie_chart(
                        chart_data,
                        f"Etiquetas del Artista - {self.selected_artist}"
                    )
                    
                    if chart_view:
                        layout.addWidget(chart_view)
                    else:
                        no_chart = QLabel("No se pudo crear el gráfico")
                        no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        layout.addWidget(no_chart)
                else:
                    no_data = QLabel("No se pudieron procesar las etiquetas del artista")
                    no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_data)
            else:
                no_data = QLabel("No hay etiquetas disponibles para este artista")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar etiquetas del artista: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def show_feed_stats(self):
        """Muestra estadísticas de feeds para el artista seleccionado."""
        if not self.selected_artist or not self.selected_artist_id:
            return
        
        # Asegurarse de que estamos en la cuarta página del stacked widget
        if self.stacked_widget:
            if self.stacked_widget.count() > 3:
                self.stacked_widget.setCurrentIndex(3)
            else:
                self.stacked_widget.setCurrentIndex(0)
        
        # Obtener la página actual
        current_page = self.stacked_widget.currentWidget()
        if not current_page:
            return
        
        # Limpiar la página
        layout = self.ensure_widget_has_layout(current_page)
        self.clear_layout(layout)
        
        # Añadir título
        title = QLabel(f"Feeds - {self.selected_artist}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Consultar datos
        self.load_artist_feeds(layout)
    
    def load_artist_feeds(self, layout):
        """Carga y muestra información sobre los feeds del artista."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener feeds del artista
            cursor.execute("""
                SELECT 
                    feed_name, 
                    COUNT(*) as feed_count
                FROM 
                    feeds
                WHERE 
                    entity_type = 'artist' AND
                    entity_id = ?
                GROUP BY 
                    feed_name
                ORDER BY 
                    feed_count DESC;
            """, (self.selected_artist_id,))
            
            feed_data = cursor.fetchall()
            
            # Crear el gráfico si hay datos
            if feed_data:
                # Crear gráfico circular
                chart_view = ChartFactory.create_pie_chart(
                    feed_data,
                    f"Feeds del Artista - {self.selected_artist}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    
                    # Tabla con detalles
                    table = QTableWidget()
                    table.setColumnCount(3)
                    table.setHorizontalHeaderLabels(["Feed", "Publicaciones", "Última Actualización"])
                    table.setRowCount(len(feed_data))
                    
                    for i, (feed_name, count) in enumerate(feed_data):
                        # Buscar la última actualización
                        cursor.execute("""
                            SELECT 
                                MAX(post_date) as latest_date
                            FROM 
                                feeds
                            WHERE 
                                entity_type = 'artist' AND
                                entity_id = ? AND
                                feed_name = ?
                        """, (self.selected_artist_id, feed_name))
                        
                        latest_date = cursor.fetchone()[0] or "Desconocida"
                        
                        # Llenar la tabla
                        table.setItem(i, 0, QTableWidgetItem(feed_name))
                        table.setItem(i, 1, QTableWidgetItem(str(count)))
                        table.setItem(i, 2, QTableWidgetItem(str(latest_date)))
                    
                    table.resizeColumnsToContents()
                    layout.addWidget(table)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                # Intentar buscar si hay feeds para los álbumes del artista
                cursor.execute("""
                    SELECT 
                        f.feed_name, 
                        COUNT(*) as feed_count,
                        a.name as album_name
                    FROM 
                        feeds f
                    JOIN 
                        albums a ON f.entity_id = a.id AND f.entity_type = 'album'
                    WHERE 
                        a.artist_id = ?
                    GROUP BY 
                        f.feed_name, a.name
                    ORDER BY 
                        feed_count DESC;
                """, (self.selected_artist_id,))
                
                album_feed_data = cursor.fetchall()
                
                if album_feed_data:
                    # Agrupar por feed_name
                    feeds_by_name = {}
                    for feed_name, count, album_name in album_feed_data:
                        if feed_name not in feeds_by_name:
                            feeds_by_name[feed_name] = 0
                        feeds_by_name[feed_name] += count
                    
                    # Preparar datos para el gráfico
                    chart_data = [(feed, count) for feed, count in feeds_by_name.items()]
                    
                    # Crear gráfico circular
                    chart_view = ChartFactory.create_pie_chart(
                        chart_data,
                        f"Feeds de Álbumes de {self.selected_artist}"
                    )
                    
                    if chart_view:
                        layout.addWidget(chart_view)
                        
                        # Crear tabla con detalles
                        table = QTableWidget()
                        table.setColumnCount(3)
                        table.setHorizontalHeaderLabels(["Feed", "Álbum", "Publicaciones"])
                        table.setRowCount(len(album_feed_data))
                        
                        for i, (feed_name, count, album_name) in enumerate(album_feed_data):
                            table.setItem(i, 0, QTableWidgetItem(feed_name))
                            table.setItem(i, 1, QTableWidgetItem(album_name))
                            table.setItem(i, 2, QTableWidgetItem(str(count)))
                        
                        table.resizeColumnsToContents()
                        layout.addWidget(table)
                    else:
                        no_chart = QLabel("No se pudo crear el gráfico")
                        no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        layout.addWidget(no_chart)
                else:
                    no_data = QLabel("No hay feeds disponibles para este artista o sus álbumes")
                    no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar feeds del artista: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    # Los métodos para el resto de las estadísticas se implementan de manera similar
    def show_label_stats(self):
        """Muestra estadísticas de sellos para el artista seleccionado."""
        if not self.selected_artist or not self.selected_artist_id:
            return
        
        # Obtener la página actual
        if self.stacked_widget:
            if self.stacked_widget.count() > 4:
                self.stacked_widget.setCurrentIndex(4)
            else:
                self.stacked_widget.setCurrentIndex(0)
        
        current_page = self.stacked_widget.currentWidget()
        if not current_page:
            return
        
        # Limpiar la página
        layout = self.ensure_widget_has_layout(current_page)
        self.clear_layout(layout)
        
        # Añadir título
        title = QLabel(f"Sellos Discográficos - {self.selected_artist}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Consultar datos
        self.load_artist_labels(layout)
    
    def load_artist_labels(self, layout):
        """Carga y muestra información sobre los sellos del artista usando un gráfico de líneas temporal."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Crear una estructura para organizar contenido
            main_container = QWidget()
            main_layout = QVBoxLayout(main_container)
            
            title = QLabel(f"Sellos Discográficos - {self.selected_artist}")
            title.setStyleSheet("font-size: 16px; font-weight: bold;")
            main_layout.addWidget(title)
            
            # Contenedor para el gráfico y la tabla
            content_splitter = QSplitter(Qt.Orientation.Vertical)
            
            # Contenedor para el gráfico temporal
            chart_container = QWidget()
            chart_layout = QVBoxLayout(chart_container)
            chart_title = QLabel("Evolución temporal de discos por sello")
            chart_title.setStyleSheet("font-weight: bold;")
            chart_layout.addWidget(chart_title)
            
            # Contenedor para las tablas de información
            table_container = QWidget()
            table_layout = QVBoxLayout(table_container)
            table_title = QLabel("Detalles de sellos")
            table_title.setStyleSheet("font-weight: bold;")
            table_layout.addWidget(table_title)
            
            # Intentamos primero con datos del sistema local
            cursor.execute("""
                SELECT 
                    a.label,
                    a.year,
                    a.name as album_name
                FROM 
                    albums a
                WHERE 
                    a.artist_id = ? AND
                    a.label IS NOT NULL AND
                    a.label != '' AND
                    a.year IS NOT NULL AND
                    a.year != ''
                ORDER BY 
                    a.year, a.label, a.name
            """, (self.selected_artist_id,))
            
            local_albums = cursor.fetchall()
            
            # Si no hay suficientes datos en el sistema local, intentar con discogs
            if len(local_albums) < 5:
                cursor.execute("""
                    SELECT 
                        d.label,
                        d.year,
                        d.album_name
                    FROM 
                        discogs_discography d
                    WHERE 
                        d.artist_id = ? AND
                        d.label IS NOT NULL AND
                        d.label != '' AND
                        d.year IS NOT NULL AND
                        d.year > 0
                    ORDER BY 
                        d.year, d.label, d.album_name
                """, (self.selected_artist_id,))
                
                discogs_albums = cursor.fetchall()
                
                # Combinar resultados evitando duplicados
                combined_albums = {}
                
                # Primero añadir albums locales
                for label, year, album in local_albums:
                    key = (str(label), str(year), str(album))
                    combined_albums[key] = True
                
                # Luego añadir albums de discogs sin duplicar
                for label, year, album in discogs_albums:
                    key = (str(label), str(year), str(album))
                    combined_albums[key] = True
                
                # Convertir de vuelta a lista de tuplas
                album_data = [(label, year, album) for (label, year, album) in combined_albums.keys()]
                
                # Ordenar por año
                album_data.sort(key=lambda x: (int(str(x[1])) if str(x[1]).isdigit() else 0, str(x[0]), str(x[2])))
            else:
                album_data = local_albums
            
            if album_data:
                # Organizar datos por sello y año
                labels_years = {}
                all_years = set()
                min_year = 9999
                max_year = 0
                
                for label, year, album in album_data:
                    label_str = str(label)
                    try:
                        # Asegurarse de que el año es un número válido
                        year_int = int(str(year))
                        
                        # Actualizar años extremos
                        if year_int < min_year:
                            min_year = year_int
                        if year_int > max_year:
                            max_year = year_int
                        
                        # Añadir año al conjunto
                        all_years.add(year_int)
                        
                        # Inicializar diccionario para este sello si no existe
                        if label_str not in labels_years:
                            labels_years[label_str] = {}
                        
                        # Incrementar contador de álbumes para este sello y año
                        if year_int not in labels_years[label_str]:
                            labels_years[label_str][year_int] = 0
                        
                        labels_years[label_str][year_int] += 1
                    except (ValueError, TypeError):
                        # Ignorar años que no se pueden convertir a entero
                        continue
                
                # Determinar un rango de años óptimo para mostrar
                if min_year != 9999 and max_year != 0:
                    # Incluir TODOS los años en el rango en years_to_display
                    years_to_display = list(range(min_year, max_year + 1))
                    
                    # Ordenar los sellos por número total de álbumes
                    total_albums_by_label = {}
                    for label, years_dict in labels_years.items():
                        total_albums_by_label[label] = sum(years_dict.values())
                    
                    # Obtener los 10 sellos con más álbumes
                    top_labels = sorted(total_albums_by_label.items(), key=lambda x: x[1], reverse=True)[:10]
                    top_label_names = [label for label, _ in top_labels]
                    
                    # Preparar datos para el gráfico de líneas - UN SOLO GRÁFICO CON MÚLTIPLES LÍNEAS
                    line_series_data = []
                    
                    # Crear una serie para cada uno de los sellos principales
                    for label in top_label_names:
                        if label in labels_years:
                            series_points = []
                            cumulative_count = 0
                            
                            # Añadir puntos para CADA AÑO en el rango, asegurándose de incluir todos
                            for year in years_to_display:
                                if year in labels_years[label]:
                                    cumulative_count += labels_years[label][year]
                                
                                # Añadir punto (año, conteo acumulado) para cada año, tenga o no lanzamientos
                                series_points.append((str(year), cumulative_count))
                            
                            # Solo añadir la serie si tiene datos relevantes
                            if any(count > 0 for _, count in series_points):
                                line_series_data.append((label, series_points))
                    
                    # Crear el gráfico de líneas ÚNICO
                    if line_series_data:
                        # Usar ChartFactory para crear un gráfico de líneas múltiples
                        # Asegurarse de que la leyenda esté a la derecha y sea visible
                        from PyQt6.QtCore import QMargins
                        from PyQt6.QtGui import QFont
                        
                        chart_view = ChartFactory.create_multi_line_chart(
                            line_series_data,
                            f"Evolución temporal por sello - {self.selected_artist}",
                            x_label="Año",
                            y_label="Álbumes acumulados"
                        )
                        
                        # Ajustar la leyenda para que sea más visible
                        if chart_view:
                            try:
                                chart = chart_view.chart()
                                legend = chart.legend()
                                legend.setAlignment(Qt.AlignmentFlag.AlignRight)  # Leyenda a la derecha
                                
                                # Dar más espacio a la leyenda
                                chart.setMargins(QMargins(10, 10, 120, 10))  # Más espacio a la derecha para la leyenda
                                
                                # Mejorar la visualización de la leyenda
                                font = QFont()
                                font.setPointSize(9)
                                legend.setFont(font)
                                legend.setShowToolTips(True)
                            except Exception as e:
                                logging.error(f"Error al ajustar la leyenda: {e}")
                        
                        # Añadir el gráfico al layout
                        if chart_view:
                            chart_layout.addWidget(chart_view)
                        else:
                            error_label = QLabel("No se pudo crear el gráfico de líneas")
                            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            chart_layout.addWidget(error_label)
                
                # Crear tabla con información detallada
                table = QTableWidget()
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Sello", "Álbumes", "Años"])
                
                # Calcular conteo de álbumes por sello
                label_counts = {}
                label_years = {}
                
                for label, year, album in album_data:
                    label_str = str(label)
                    
                    if label_str not in label_counts:
                        label_counts[label_str] = 0
                        label_years[label_str] = set()
                    
                    label_counts[label_str] += 1
                    
                    try:
                        year_int = int(str(year))
                        label_years[label_str].add(year_int)
                    except (ValueError, TypeError):
                        pass
                
                # Ordenar sellos por número de álbumes
                sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
                
                # Llenar la tabla
                table.setRowCount(len(sorted_labels))
                
                for i, (label, count) in enumerate(sorted_labels):
                    years = sorted(label_years[label]) if label in label_years else []
                    years_str = ", ".join(str(y) for y in years[:5])
                    
                    if len(years) > 5:
                        years_str += f"... ({min(years)}-{max(years)})"
                    
                    table.setItem(i, 0, QTableWidgetItem(label))
                    table.setItem(i, 1, QTableWidgetItem(str(count)))
                    table.setItem(i, 2, QTableWidgetItem(years_str))
                
                table.resizeColumnsToContents()
                table_layout.addWidget(table)
                
                # Añadir contenedores al splitter
                content_splitter.addWidget(chart_container)
                content_splitter.addWidget(table_container)
                
                # Añadir splitter al contenedor principal
                main_layout.addWidget(content_splitter)
                
                # Añadir el contenedor principal al layout
                layout.addWidget(main_container)
            else:
                no_data = QLabel("No hay suficientes datos de sellos para mostrar una evolución temporal")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos temporales de sellos: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    



    def show_discography_stats(self):
        """Muestra estadísticas de discografía para el artista seleccionado."""
        if not self.selected_artist or not self.selected_artist_id:
            return
        
        # Obtener la página actual
        if self.stacked_widget:
            if self.stacked_widget.count() > 5:
                self.stacked_widget.setCurrentIndex(5)
            else:
                self.stacked_widget.setCurrentIndex(0)
        
        current_page = self.stacked_widget.currentWidget()
        if not current_page:
            return
        
        # Limpiar la página
        layout = self.ensure_widget_has_layout(current_page)
        self.clear_layout(layout)
        
        # Añadir título
        title = QLabel(f"Discografía - {self.selected_artist}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Contenedor para los gráficos
        charts_container = QWidget()
        charts_layout = QHBoxLayout(charts_container)
        
        # Contenedor para el gráfico de formatos
        formats_container = QWidget()
        formats_layout = QVBoxLayout(formats_container)
        formats_title = QLabel("Formatos")
        formats_title.setStyleSheet("font-weight: bold;")
        formats_layout.addWidget(formats_title)
        
        formats_chart_container = QWidget()
        formats_chart_layout = QVBoxLayout(formats_chart_container)
        formats_layout.addWidget(formats_chart_container)
        
        # Contenedor para el gráfico de tipos de lanzamiento
        types_container = QWidget()
        types_layout = QVBoxLayout(types_container)
        types_title = QLabel("Tipos de Lanzamiento")
        types_title.setStyleSheet("font-weight: bold;")
        types_layout.addWidget(types_title)
        
        types_chart_container = QWidget()
        types_chart_layout = QVBoxLayout(types_chart_container)
        types_layout.addWidget(types_chart_container)
        
        # Contenedor para el gráfico de posesión
        owned_container = QWidget()
        owned_layout = QVBoxLayout(owned_container)
        owned_title = QLabel("Tu Colección")
        owned_title.setStyleSheet("font-weight: bold;")
        owned_layout.addWidget(owned_title)
        
        owned_chart_container = QWidget()
        owned_chart_layout = QVBoxLayout(owned_chart_container)
        owned_layout.addWidget(owned_chart_container)
        
        # Añadir contenedores al layout de gráficos
        charts_layout.addWidget(formats_container)
        charts_layout.addWidget(types_container)
        charts_layout.addWidget(owned_container)
        
        # Añadir contenedor de gráficos al layout principal
        layout.addWidget(charts_container)
        
        # Contenedor para la tabla de álbumes
        albums_container = QWidget()
        albums_layout = QVBoxLayout(albums_container)
        albums_title = QLabel("Álbumes")
        albums_title.setStyleSheet("font-weight: bold;")
        albums_layout.addWidget(albums_title)
        
        # Tabla de álbumes
        albums_table = QTableWidget()
        albums_layout.addWidget(albums_table)
        
        # Añadir contenedor de álbumes al layout principal
        layout.addWidget(albums_container)
        
        # Cargar y mostrar datos
        self.load_artist_formats(formats_chart_layout)
        self.load_artist_release_types(types_chart_layout)
        self.load_artist_owned_albums(owned_chart_layout)
        self.load_artist_albums(albums_table)

    def load_artist_owned_albums(self, layout):
        """Carga y muestra un gráfico circular con la proporción de álbumes en posesión vs. no poseídos."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Primero obtener el total de álbumes conocidos (de discogs)
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT album_name) as total_albums
                FROM 
                    discogs_discography
                WHERE 
                    artist_id = ?;
            """, (self.selected_artist_id,))
            
            discogs_count = cursor.fetchone()[0] or 0
            
            # Obtener el total de álbumes en nuestra base de datos
            cursor.execute("""
                SELECT 
                    COUNT(*) as owned_albums
                FROM 
                    albums
                WHERE 
                    artist_id = ?;
            """, (self.selected_artist_id,))
            
            owned_count = cursor.fetchone()[0] or 0
            
            # Calcular la proporción
            total_count = max(discogs_count, owned_count)
            missing_count = total_count - owned_count
            
            # Crear datos para el gráfico
            chart_data = [
                ("En colección", owned_count),
                ("No poseídos", missing_count if missing_count > 0 else 0)
            ]
            
            # Crear gráfico si hay datos
            if total_count > 0:
                chart_view = ChartFactory.create_pie_chart(
                    chart_data,
                    f"Álbumes en Colección - {self.selected_artist}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    
                    # Añadir etiqueta con porcentaje
                    percentage = (owned_count / total_count) * 100 if total_count > 0 else 0
                    stats_label = QLabel(f"Tienes {owned_count} de {total_count} álbumes ({percentage:.1f}%)")
                    stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(stats_label)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay datos de discografía disponibles")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de posesión de álbumes: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)


    def load_artist_formats(self, layout):
        """Carga y muestra un gráfico circular con los formatos de lanzamiento."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener formatos de discogs_discography
            cursor.execute("""
                SELECT 
                    formats
                FROM 
                    discogs_discography
                WHERE 
                    artist_id = ? AND
                    formats IS NOT NULL AND
                    formats != ''
            """, (self.selected_artist_id,))
            
            formats_data = cursor.fetchall()
            
            # Procesar los datos JSON
            format_counts = {}
            for formats_json, in formats_data:
                try:
                    if formats_json:
                        formats = json.loads(formats_json)
                        if isinstance(formats, list):
                            for format_obj in formats:
                                if isinstance(format_obj, dict) and 'name' in format_obj:
                                    format_name = format_obj['name']
                                    if format_name in format_counts:
                                        format_counts[format_name] += 1
                                    else:
                                        format_counts[format_name] = 1
                except json.JSONDecodeError:
                    # Si no es JSON válido, intentar obtener el formato directamente
                    if formats_json and isinstance(formats_json, str):
                        if formats_json in format_counts:
                            format_counts[formats_json] += 1
                        else:
                            format_counts[formats_json] = 1
            
            # Crear el gráfico si hay datos
            if format_counts:
                # Convertir a formato para gráfico
                chart_data = [(format_name, count) for format_name, count in sorted(format_counts.items(), key=lambda x: x[1], reverse=True)]
                
                # Crear gráfico circular
                chart_view = ChartFactory.create_pie_chart(
                    chart_data,
                    f"Formatos - {self.selected_artist}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay información de formatos disponible")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar formatos del artista: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def load_artist_release_types(self, layout):
        """Carga y muestra un gráfico circular con los tipos de lanzamiento."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Obtener tipos de lanzamiento
            cursor.execute("""
                SELECT 
                    type, 
                    COUNT(*) as type_count
                FROM 
                    discogs_discography
                WHERE 
                    artist_id = ? AND
                    type IS NOT NULL AND
                    type != ''
                GROUP BY 
                    type
                ORDER BY 
                    type_count DESC;
            """, (self.selected_artist_id,))
            
            type_data = cursor.fetchall()
            
            # Crear el gráfico si hay datos
            if type_data:
                # Crear gráfico circular
                chart_view = ChartFactory.create_pie_chart(
                    type_data,
                    f"Tipos de Lanzamiento - {self.selected_artist}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                else:
                    no_chart = QLabel("No se pudo crear el gráfico")
                    no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_chart)
            else:
                no_data = QLabel("No hay información de tipos de lanzamiento disponible")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar tipos de lanzamiento: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def load_artist_albums(self, table):
        """Carga y muestra una tabla con los álbumes del artista."""
        if not self.ensure_db_connection() or not self.selected_artist_id or not table:
            return
        
        cursor = self.conn.cursor()
        try:
            # Primero intentar obtener datos de la tabla albums
            cursor.execute("""
                SELECT 
                    name, 
                    year, 
                    label, 
                    genre,
                    total_tracks
                FROM 
                    albums
                WHERE 
                    artist_id = ?
                ORDER BY 
                    year DESC, name;
            """, (self.selected_artist_id,))
            
            album_data = cursor.fetchall()
            
            if album_data:
                # Configurar tabla
                table.setColumnCount(5)
                table.setHorizontalHeaderLabels(["Álbum", "Año", "Sello", "Género", "Pistas"])
                table.setRowCount(len(album_data))
                
                # Llenar la tabla
                for i, (name, year, label, genre, tracks) in enumerate(album_data):
                    table.setItem(i, 0, QTableWidgetItem(name or ""))
                    table.setItem(i, 1, QTableWidgetItem(str(year) or ""))
                    table.setItem(i, 2, QTableWidgetItem(label or ""))
                    table.setItem(i, 3, QTableWidgetItem(genre or ""))
                    table.setItem(i, 4, QTableWidgetItem(str(tracks) if tracks else ""))
                
                table.resizeColumnsToContents()
            else:
                # Si no hay datos en albums, intentar con discogs_discography
                cursor.execute("""
                    SELECT 
                        album_name, 
                        year, 
                        CASE
                            WHEN labels IS NOT NULL AND labels != '' AND labels != '[]' THEN labels
                            ELSE label
                        END as release_label,
                        CASE
                            WHEN genres IS NOT NULL AND genres != '' AND genres != '[]' THEN genres
                            ELSE ''
                        END as release_genre,
                        role
                    FROM 
                        discogs_discography
                    WHERE 
                        artist_id = ?
                    ORDER BY 
                        year DESC, album_name;
                """, (self.selected_artist_id,))
                
                discogs_data = cursor.fetchall()
                
                if discogs_data:
                    # Configurar tabla
                    table.setColumnCount(5)
                    table.setHorizontalHeaderLabels(["Álbum", "Año", "Sello", "Género", "Rol"])
                    table.setRowCount(len(discogs_data))
                    
                    # Llenar la tabla
                    for i, (name, year, labels_json, genres_json, role) in enumerate(discogs_data):
                        # Procesar etiquetas
                        labels = "Desconocido"
                        try:
                            if labels_json and labels_json != labels:  # Si no es el valor de la columna label
                                labels_data = json.loads(labels_json)
                                if isinstance(labels_data, list) and labels_data:
                                    label_names = []
                                    for label_obj in labels_data:
                                        if isinstance(label_obj, dict) and 'name' in label_obj:
                                            label_names.append(label_obj['name'])
                                    if label_names:
                                        labels = ", ".join(label_names)
                        except json.JSONDecodeError:
                            labels = labels_json if labels_json else "Desconocido"
                        
                        # Procesar géneros
                        genres = "Desconocido"
                        try:
                            if genres_json:
                                genres_data = json.loads(genres_json)
                                if isinstance(genres_data, list) and genres_data:
                                    genres = ", ".join(genres_data)
                        except json.JSONDecodeError:
                            genres = genres_json if genres_json else "Desconocido"
                        
                        # Llenar la tabla
                        table.setItem(i, 0, QTableWidgetItem(name or ""))
                        table.setItem(i, 1, QTableWidgetItem(str(year) if year else ""))
                        table.setItem(i, 2, QTableWidgetItem(labels))
                        table.setItem(i, 3, QTableWidgetItem(genres))
                        table.setItem(i, 4, QTableWidgetItem(role or ""))
                    
                    table.resizeColumnsToContents()
                else:
                    # No hay datos en ninguna de las tablas
                    table.setColumnCount(1)
                    table.setRowCount(1)
                    table.setHorizontalHeaderLabels(["Información"])
                    table.setItem(0, 0, QTableWidgetItem("No hay información de álbumes disponible"))
                    table.resizeColumnsToContents()
                
        except Exception as e:
            logging.error(f"Error al cargar álbumes del artista: {e}")
            table.setColumnCount(1)
            table.setRowCount(1)
            table.setHorizontalHeaderLabels(["Error"])
            table.setItem(0, 0, QTableWidgetItem(f"Error: {str(e)}"))
            table.resizeColumnsToContents()
    
    def show_listen_stats(self):
        """Muestra estadísticas de escuchas para el artista seleccionado."""
        if not self.selected_artist or not self.selected_artist_id:
            return
        
        # Obtener la página actual
        if self.stacked_widget:
            if self.stacked_widget.count() > 6:
                self.stacked_widget.setCurrentIndex(6)
            else:
                self.stacked_widget.setCurrentIndex(0)
        
        current_page = self.stacked_widget.currentWidget()
        if not current_page:
            return
        
        # Limpiar la página
        layout = self.ensure_widget_has_layout(current_page)
        self.clear_layout(layout)
        
        # Añadir título
        title = QLabel(f"Estadísticas de Escuchas - {self.selected_artist}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear splitter para organizar los gráficos
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Container for LastFM scrobbles
        lastfm_container = QWidget()
        lastfm_layout = QVBoxLayout(lastfm_container)
        lastfm_title = QLabel("Escuchas LastFM")
        lastfm_title.setStyleSheet("font-weight: bold;")
        lastfm_layout.addWidget(lastfm_title)
        
        lastfm_chart_container = QWidget()
        lastfm_chart_layout = QVBoxLayout(lastfm_chart_container)
        lastfm_layout.addWidget(lastfm_chart_container)
        
        # Container for ListenBrainz listens
        listenbrainz_container = QWidget()
        listenbrainz_layout = QVBoxLayout(listenbrainz_container)
        listenbrainz_title = QLabel("Escuchas ListenBrainz")
        listenbrainz_title.setStyleSheet("font-weight: bold;")
        listenbrainz_layout.addWidget(listenbrainz_title)
        
        listenbrainz_chart_container = QWidget()
        listenbrainz_chart_layout = QVBoxLayout(listenbrainz_chart_container)
        listenbrainz_layout.addWidget(listenbrainz_chart_container)
        
        # Add containers to splitter
        splitter.addWidget(lastfm_container)
        splitter.addWidget(listenbrainz_container)
        
        # Add splitter to main layout
        layout.addWidget(splitter)
        
        # Load and display data
        self.load_lastfm_listen_data(lastfm_chart_layout)
        self.load_listenbrainz_listen_data(listenbrainz_chart_layout)
    
    def load_lastfm_listen_data(self, layout):
        """Carga y muestra un gráfico con las escuchas de LastFM."""
        if not self.ensure_db_connection():
            return
        
        cursor = self.conn.cursor()
        try:
            # Verificar si el artista existe en LastFM
            query = f"""
                SELECT 
                    COUNT(*) as scrobble_count,
                    MIN(fecha_scrobble) as first_scrobble,
                    MAX(fecha_scrobble) as last_scrobble
                FROM 
                    scrobbles_{self.lastfm_username}
                WHERE 
                    artist_name = ?;
            """
            cursor.execute(query, (self.selected_artist,))
            
            scrobble_info = cursor.fetchone()
            
            if scrobble_info and scrobble_info[0] > 0:
                scrobble_count = scrobble_info[0]
                # Corregir asignación de las fechas - la primera debe ser la más antigua 
                # y la última debe ser la más reciente
                first_scrobble = scrobble_info[1]  # MIN(fecha_scrobble)
                last_scrobble = scrobble_info[2]   # MAX(fecha_scrobble)
                
                # Verificar y corregir fechas si es necesario
                if first_scrobble and last_scrobble:
                    try:
                        # Convertir a objetos de fecha si es posible para compararlos
                        import datetime
                        
                        # Intentar varios formatos de fecha comunes
                        date_formats = [
                            "%d %b %Y, %H:%M", 
                            "%Y-%m-%d %H:%M:%S",
                            "%Y-%m-%d"
                        ]
                        
                        first_date = None
                        last_date = None
                        
                        # Intentar parsear la primera fecha
                        for fmt in date_formats:
                            try:
                                first_date = datetime.datetime.strptime(first_scrobble, fmt)
                                break
                            except ValueError:
                                continue
                                
                        # Intentar parsear la última fecha
                        for fmt in date_formats:
                            try:
                                last_date = datetime.datetime.strptime(last_scrobble, fmt)
                                break
                            except ValueError:
                                continue
                        
                        # Si pudimos parsear ambas fechas, verificar si están en el orden correcto
                        if first_date and last_date and first_date > last_date:
                            # Las fechas están en orden incorrecto, intercambiarlas
                            first_scrobble, last_scrobble = last_scrobble, first_scrobble
                            logging.warning(f"Fechas de escucha corregidas para {self.selected_artist}")
                    except Exception as e:
                        logging.error(f"Error al procesar fechas: {e}")
                
                # Mostrar información básica
                info_label = QLabel(f"Total de escuchas: {scrobble_count}\nPrimera escucha: {first_scrobble}\nÚltima escucha: {last_scrobble}")
                layout.addWidget(info_label)
                
                # Obtener escuchas por canción
                query = f"""
                    SELECT 
                        track_name, 
                        COUNT(*) as listen_count
                    FROM 
                        scrobbles_{self.lastfm_username}
                    WHERE 
                        artist_name = ?
                    GROUP BY 
                        track_name
                    ORDER BY 
                        listen_count DESC
                    LIMIT 15;
                """
                cursor.execute(query, (self.selected_artist,))
                
                song_data = cursor.fetchall()
                
                if song_data:
                    # Crear gráfico de barras
                    song_chart = ChartFactory.create_bar_chart(
                        song_data,
                        f"Canciones Más Escuchadas (LastFM) - {self.selected_artist}",
                        x_label="Canción",
                        y_label="Escuchas"
                    )
                    
                    if song_chart:
                        layout.addWidget(song_chart)
                    
                    # Crear tabla con todas las canciones
                    table = QTableWidget()
                    table.setColumnCount(3)
                    table.setHorizontalHeaderLabels(["Canción", "Álbum", "Escuchas"])
                    
                    # Obtener escuchas por canción con álbum
                    query = f"""
                        SELECT 
                            track_name, 
                            album_name, 
                            COUNT(*) as listen_count
                        FROM 
                            scrobbles_{self.lastfm_username}
                        WHERE 
                            artist_name = ?
                        GROUP BY 
                            track_name, album_name
                        ORDER BY 
                            listen_count DESC;
                    """
                    cursor.execute(query, (self.selected_artist,))
                    
                    detailed_song_data = cursor.fetchall()
                    
                    if detailed_song_data:
                        table.setRowCount(len(detailed_song_data))
                        
                        for i, (song, album, count) in enumerate(detailed_song_data):
                            table.setItem(i, 0, QTableWidgetItem(song or ""))
                            table.setItem(i, 1, QTableWidgetItem(album or ""))
                            table.setItem(i, 2, QTableWidgetItem(str(count)))
                        
                        table.resizeColumnsToContents()
                        layout.addWidget(table)
                
                # Obtener escuchas por año
                query = f"""
                    SELECT 
                        strftime('%Y', fecha_scrobble) as year, 
                        COUNT(*) as listen_count
                    FROM 
                        scrobbles_{self.lastfm_username}
                    WHERE 
                        artist_name = ? AND
                        fecha_scrobble IS NOT NULL AND
                        fecha_scrobble != '' AND
                        strftime('%Y', fecha_scrobble) IS NOT NULL
                    GROUP BY 
                        year
                    ORDER BY 
                        year;
                """
                cursor.execute(query, (self.selected_artist,))
                
                year_data = cursor.fetchall()
                
                if year_data:
                    # Verificar y filtrar años no válidos (ceros o valores muy bajos)
                    valid_year_data = []
                    for year, count in year_data:
                        try:
                            year_int = int(year)
                            if year_int > 1970 and year_int <= 2030:  # Rango razonable de años
                                valid_year_data.append((year, count))
                            else:
                                logging.warning(f"Año de escucha fuera de rango ignorado: {year}")
                        except (ValueError, TypeError):
                            logging.warning(f"Valor de año no válido ignorado: {year}")
                            continue
                    
                    if valid_year_data:
                        # Crear gráfico de línea con años válidos
                        year_chart = ChartFactory.create_line_chart(
                            valid_year_data,
                            f"Escuchas por Año (LastFM) - {self.selected_artist}",
                            x_label="Año",
                            y_label="Escuchas"
                        )
                        
                        if year_chart:
                            layout.addWidget(year_chart)
                        else:
                            no_chart = QLabel("No se pudo crear el gráfico de escuchas por año")
                            no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            layout.addWidget(no_chart)
                    else:
                        no_years = QLabel("No hay datos de años válidos para mostrar")
                        no_years.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        layout.addWidget(no_years)
                else:
                    no_years = QLabel("No hay datos de escuchas por año disponibles")
                    no_years.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_years)
            else:
                no_data = QLabel("No hay datos de LastFM para este artista")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de LastFM: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error al cargar datos de LastFM: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)

    def load_listenbrainz_listen_data(self, layout):
        """Carga y muestra un gráfico con las escuchas de ListenBrainz."""
        if not self.ensure_db_connection():
            return
        
        cursor = self.conn.cursor()
        try:
            # Verificar si el artista existe en ListenBrainz
            query = f"""
                SELECT 
                    COUNT(*) as listen_count,
                    MIN(listen_date) as first_listen,
                    MAX(listen_date) as last_listen
                FROM 
                    listens_{self.musicbrainz_username}
                WHERE 
                    artist_name = ?;
            """
            cursor.execute(query, (self.selected_artist,))
            
            listen_info = cursor.fetchone()
            
            if listen_info and listen_info[0] > 0:
                listen_count = listen_info[0]
                # Corregir asignación de las fechas - la primera debe ser la más antigua 
                # y la última debe ser la más reciente
                first_listen = listen_info[1]  # MIN(listen_date)
                last_listen = listen_info[2]   # MAX(listen_date)
                
                # Verificar y corregir fechas si es necesario
                if first_listen and last_listen:
                    try:
                        # Convertir a objetos de fecha si es posible para compararlos
                        import datetime
                        
                        # Intentar varios formatos de fecha comunes
                        date_formats = [
                            "%d %b %Y, %H:%M", 
                            "%Y-%m-%d %H:%M:%S",
                            "%Y-%m-%d"
                        ]
                        
                        first_date = None
                        last_date = None
                        
                        # Intentar parsear la primera fecha
                        for fmt in date_formats:
                            try:
                                first_date = datetime.datetime.strptime(str(first_listen), fmt)
                                break
                            except (ValueError, TypeError):
                                continue
                                
                        # Intentar parsear la última fecha
                        for fmt in date_formats:
                            try:
                                last_date = datetime.datetime.strptime(str(last_listen), fmt)
                                break
                            except (ValueError, TypeError):
                                continue
                        
                        # Si pudimos parsear ambas fechas, verificar si están en el orden correcto
                        if first_date and last_date and first_date > last_date:
                            # Las fechas están en orden incorrecto, intercambiarlas
                            first_listen, last_listen = last_listen, first_listen
                            logging.warning(f"Fechas de escucha ListenBrainz corregidas para {self.selected_artist}")
                    except Exception as e:
                        logging.error(f"Error al procesar fechas de ListenBrainz: {e}")
                
                # Mostrar información básica
                info_label = QLabel(f"Total de escuchas: {listen_count}\nPrimera escucha: {first_listen}\nÚltima escucha: {last_listen}")
                layout.addWidget(info_label)
                
                # Obtener escuchas por canción
                query = f"""
                    SELECT 
                        track_name, 
                        COUNT(*) as listen_count
                    FROM 
                        listens_{self.musicbrainz_username}
                    WHERE 
                        artist_name = ?
                    GROUP BY 
                        track_name
                    ORDER BY 
                        listen_count DESC
                    LIMIT 15;
                """
                cursor.execute(query, (self.selected_artist,))
                
                song_data = cursor.fetchall()
                
                if song_data:
                    # Crear gráfico de barras
                    song_chart = ChartFactory.create_bar_chart(
                        song_data,
                        f"Canciones Más Escuchadas (ListenBrainz) - {self.selected_artist}",
                        x_label="Canción",
                        y_label="Escuchas"
                    )
                    
                    if song_chart:
                        layout.addWidget(song_chart)
                    
                    # Crear tabla con todas las canciones
                    table = QTableWidget()
                    table.setColumnCount(3)
                    table.setHorizontalHeaderLabels(["Canción", "Álbum", "Escuchas"])
                    
                    # Obtener escuchas por canción con álbum
                    query = f"""
                        SELECT 
                            track_name, 
                            album_name, 
                            COUNT(*) as listen_count
                        FROM 
                            listens_{self.musicbrainz_username}
                        WHERE 
                            artist_name = ?
                        GROUP BY 
                            track_name, album_name
                        ORDER BY 
                            listen_count DESC;
                    """
                    cursor.execute(query, (self.selected_artist,))
                    
                    detailed_song_data = cursor.fetchall()
                    
                    if detailed_song_data:
                        table.setRowCount(len(detailed_song_data))
                        
                        for i, (song, album, count) in enumerate(detailed_song_data):
                            table.setItem(i, 0, QTableWidgetItem(song or ""))
                            table.setItem(i, 1, QTableWidgetItem(album or ""))
                            table.setItem(i, 2, QTableWidgetItem(str(count)))
                        
                        table.resizeColumnsToContents()
                        layout.addWidget(table)
                
                # Obtener escuchas por año
                query = f"""
                    SELECT 
                        strftime('%Y', listen_date) as year, 
                        COUNT(*) as listen_count
                    FROM 
                        listens_{self.musicbrainz_username}
                    WHERE 
                        artist_name = ? AND
                        listen_date IS NOT NULL AND
                        listen_date != '' AND
                        strftime('%Y', listen_date) IS NOT NULL
                    GROUP BY 
                        year
                    ORDER BY 
                        year;
                """
                cursor.execute(query, (self.selected_artist,))
                
                year_data = cursor.fetchall()
                
                if year_data:
                    # Verificar y filtrar años no válidos (ceros o valores muy bajos)
                    valid_year_data = []
                    for year, count in year_data:
                        try:
                            year_int = int(year)
                            if year_int > 1970 and year_int <= 2030:  # Rango razonable de años
                                valid_year_data.append((year, count))
                            else:
                                logging.warning(f"Año de escucha fuera de rango ignorado: {year}")
                        except (ValueError, TypeError):
                            logging.warning(f"Valor de año no válido ignorado: {year}")
                            continue
                    
                    if valid_year_data:
                        # Crear gráfico de línea con años válidos
                        year_chart = ChartFactory.create_line_chart(
                            valid_year_data,
                            f"Escuchas por Año (ListenBrainz) - {self.selected_artist}",
                            x_label="Año",
                            y_label="Escuchas"
                        )
                        
                        if year_chart:
                            layout.addWidget(year_chart)
                        else:
                            no_chart = QLabel("No se pudo crear el gráfico de escuchas por año")
                            no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            layout.addWidget(no_chart)
                    else:
                        no_years = QLabel("No hay datos de años válidos para mostrar")
                        no_years.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        layout.addWidget(no_years)
                else:
                    no_years = QLabel("No hay datos de escuchas por año disponibles")
                    no_years.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_years)
            else:
                no_data = QLabel("No hay datos de ListenBrainz para este artista")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al cargar datos de ListenBrainz: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error al cargar datos de ListenBrainz: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def show_producer_stats(self):
        """Muestra estadísticas de productores para el artista seleccionado."""
        if not self.selected_artist or not self.selected_artist_id:
            return
        
        # Obtener la página actual
        if self.stacked_widget:
            if self.stacked_widget.count() > 7:
                self.stacked_widget.setCurrentIndex(7)
            else:
                self.stacked_widget.setCurrentIndex(0)
        
        current_page = self.stacked_widget.currentWidget()
        if not current_page:
            return
        
        # Limpiar la página
        layout = self.ensure_widget_has_layout(current_page)
        self.clear_layout(layout)
        
# Añadir título
        title = QLabel(f"Productores - {self.selected_artist}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Cargar información de productores
        self.load_producer_data(layout)
    
    def load_producer_data(self, layout):
        """Carga y muestra información sobre productores relacionados con el artista."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Primero intentar obtener productores de la tabla albums
            cursor.execute("""
                SELECT 
                    producers, 
                    engineers, 
                    mastering_engineers,
                    name as album_name
                FROM 
                    albums
                WHERE 
                    artist_id = ? AND
                    (producers IS NOT NULL OR engineers IS NOT NULL OR mastering_engineers IS NOT NULL)
                ORDER BY 
                    year DESC, name;
            """, (self.selected_artist_id,))
            
            album_data = cursor.fetchall()
            
            if album_data:
                # Procesar datos
                producer_counts = {}
                engineer_counts = {}
                mastering_counts = {}
                
                for producers, engineers, mastering, album in album_data:
                    # Procesar productores
                    if producers:
                        try:
                            producer_list = json.loads(producers)
                            if isinstance(producer_list, list):
                                for producer in producer_list:
                                    if producer in producer_counts:
                                        producer_counts[producer].append(album)
                                    else:
                                        producer_counts[producer] = [album]
                            elif isinstance(producer_list, str):  # También manejar casos donde es una cadena
                                if producer_list in producer_counts:
                                    producer_counts[producer_list].append(album)
                                else:
                                    producer_counts[producer_list] = [album]
                        except json.JSONDecodeError:
                            # Intentar dividir por comas
                            if ',' in producers:
                                for producer in producers.split(','):
                                    producer = producer.strip()
                                    if producer:
                                        if producer in producer_counts:
                                            producer_counts[producer].append(album)
                                        else:
                                            producer_counts[producer] = [album]
                            elif producers:
                                if producers in producer_counts:
                                    producer_counts[producers].append(album)
                                else:
                                    producer_counts[producers] = [album]
                    
                    # Procesar ingenieros - similar a productores
                    if engineers:
                        try:
                            engineer_list = json.loads(engineers)
                            if isinstance(engineer_list, list):
                                for engineer in engineer_list:
                                    if engineer in engineer_counts:
                                        engineer_counts[engineer].append(album)
                                    else:
                                        engineer_counts[engineer] = [album]
                            elif isinstance(engineer_list, str):
                                if engineer_list in engineer_counts:
                                    engineer_counts[engineer_list].append(album)
                                else:
                                    engineer_counts[engineer_list] = [album]
                        except json.JSONDecodeError:
                            # Intentar dividir por comas
                            if ',' in engineers:
                                for engineer in engineers.split(','):
                                    engineer = engineer.strip()
                                    if engineer:
                                        if engineer in engineer_counts:
                                            engineer_counts[engineer].append(album)
                                        else:
                                            engineer_counts[engineer] = [album]
                            elif engineers:
                                if engineers in engineer_counts:
                                    engineer_counts[engineers].append(album)
                                else:
                                    engineer_counts[engineers] = [album]
                    
                    # Procesar ingenieros de masterización - similar a los anteriores
                    if mastering:
                        try:
                            mastering_list = json.loads(mastering)
                            if isinstance(mastering_list, list):
                                for engineer in mastering_list:
                                    if engineer in mastering_counts:
                                        mastering_counts[engineer].append(album)
                                    else:
                                        mastering_counts[engineer] = [album]
                            elif isinstance(mastering_list, str):
                                if mastering_list in mastering_counts:
                                    mastering_counts[mastering_list].append(album)
                                else:
                                    mastering_counts[mastering_list] = [album]
                        except json.JSONDecodeError:
                            # Intentar dividir por comas
                            if ',' in mastering:
                                for engineer in mastering.split(','):
                                    engineer = engineer.strip()
                                    if engineer:
                                        if engineer in mastering_counts:
                                            mastering_counts[engineer].append(album)
                                        else:
                                            mastering_counts[engineer] = [album]
                            elif mastering:
                                if mastering in mastering_counts:
                                    mastering_counts[mastering].append(album)
                                else:
                                    mastering_counts[mastering] = [album]
                
                # Crear gráficos y tablas para mostrar la información
                if producer_counts or engineer_counts or mastering_counts:
                    # Crear un splitter vertical para las diferentes categorías
                    splitter = QSplitter(Qt.Orientation.Vertical)
                    
                    # Sección de productores
                    if producer_counts:
                        producers_widget = QWidget()
                        producers_layout = QVBoxLayout(producers_widget)
                        producers_title = QLabel("Productores")
                        producers_title.setStyleSheet("font-weight: bold;")
                        producers_layout.addWidget(producers_title)
                        
                        # Contenedor horizontal para gráfico y tabla
                        producers_content = QWidget()
                        producers_content_layout = QHBoxLayout(producers_content)
                        
                        # Preparar gráfico
                        producers_chart_container = QWidget()
                        producers_chart_layout = QVBoxLayout(producers_chart_container)
                        
                        # Crear datos para el gráfico
                        producer_chart_data = [(producer, len(albums)) for producer, albums in 
                                            sorted(producer_counts.items(), key=lambda x: len(x[1]), reverse=True)]
                        
                        # Limitar a los 15 principales para el gráfico
                        if len(producer_chart_data) > 15:
                            chart_data = producer_chart_data[:15]
                        else:
                            chart_data = producer_chart_data
                        
                        # Crear gráfico
                        producer_chart = ChartFactory.create_pie_chart(
                            chart_data,
                            f"Productores - {self.selected_artist}"
                        )
                        
                        if producer_chart:
                            producers_chart_layout.addWidget(producer_chart)
                        else:
                            no_chart = QLabel("No se pudo crear el gráfico")
                            no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            producers_chart_layout.addWidget(no_chart)
                        
                        # Preparar tabla
                        producers_table_container = QWidget()
                        producers_table_layout = QVBoxLayout(producers_table_container)
                        
                        producer_table = QTableWidget()
                        producer_table.setColumnCount(2)
                        producer_table.setHorizontalHeaderLabels(["Productor", "Álbumes"])
                        producer_table.setRowCount(len(producer_counts))
                        
                        for i, (producer, albums) in enumerate(sorted(producer_counts.items(), key=lambda x: len(x[1]), reverse=True)):
                            producer_table.setItem(i, 0, QTableWidgetItem(producer))
                            producer_table.setItem(i, 1, QTableWidgetItem(", ".join(albums)))
                        
                        producer_table.resizeColumnsToContents()
                        producers_table_layout.addWidget(producer_table)
                        
                        # Añadir gráfico y tabla al contenedor horizontal
                        producers_content_layout.addWidget(producers_chart_container, 1)  # 1 = peso relativo
                        producers_content_layout.addWidget(producers_table_container, 1)
                        
                        # Añadir el contenedor al layout de productores
                        producers_layout.addWidget(producers_content)
                        
                        # Añadir widget de productores al splitter
                        splitter.addWidget(producers_widget)
                    
                    # Sección de ingenieros - estructura similar a productores
                    if engineer_counts:
                        engineers_widget = QWidget()
                        engineers_layout = QVBoxLayout(engineers_widget)
                        engineers_title = QLabel("Ingenieros")
                        engineers_title.setStyleSheet("font-weight: bold;")
                        engineers_layout.addWidget(engineers_title)
                        
                        # Contenedor horizontal para gráfico y tabla
                        engineers_content = QWidget()
                        engineers_content_layout = QHBoxLayout(engineers_content)
                        
                        # Preparar gráfico
                        engineers_chart_container = QWidget()
                        engineers_chart_layout = QVBoxLayout(engineers_chart_container)
                        
                        # Crear datos para el gráfico
                        engineer_chart_data = [(engineer, len(albums)) for engineer, albums in 
                                            sorted(engineer_counts.items(), key=lambda x: len(x[1]), reverse=True)]
                        
                        # Limitar a los 15 principales para el gráfico
                        if len(engineer_chart_data) > 15:
                            chart_data = engineer_chart_data[:15]
                        else:
                            chart_data = engineer_chart_data
                        
                        # Crear gráfico
                        engineer_chart = ChartFactory.create_pie_chart(
                            chart_data,
                            f"Ingenieros - {self.selected_artist}"
                        )
                        
                        if engineer_chart:
                            engineers_chart_layout.addWidget(engineer_chart)
                        else:
                            no_chart = QLabel("No se pudo crear el gráfico")
                            no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            engineers_chart_layout.addWidget(no_chart)
                        
                        # Preparar tabla
                        engineers_table_container = QWidget()
                        engineers_table_layout = QVBoxLayout(engineers_table_container)
                        
                        engineer_table = QTableWidget()
                        engineer_table.setColumnCount(2)
                        engineer_table.setHorizontalHeaderLabels(["Ingeniero", "Álbumes"])
                        engineer_table.setRowCount(len(engineer_counts))
                        
                        for i, (engineer, albums) in enumerate(sorted(engineer_counts.items(), key=lambda x: len(x[1]), reverse=True)):
                            engineer_table.setItem(i, 0, QTableWidgetItem(engineer))
                            engineer_table.setItem(i, 1, QTableWidgetItem(", ".join(albums)))
                        
                        engineer_table.resizeColumnsToContents()
                        engineers_table_layout.addWidget(engineer_table)
                        
                        # Añadir gráfico y tabla al contenedor horizontal
                        engineers_content_layout.addWidget(engineers_chart_container, 1)
                        engineers_content_layout.addWidget(engineers_table_container, 1)
                        
                        # Añadir el contenedor al layout de ingenieros
                        engineers_layout.addWidget(engineers_content)
                        
                        # Añadir widget de ingenieros al splitter
                        splitter.addWidget(engineers_widget)
                    
                    # Sección de ingenieros de masterización - estructura similar a los anteriores
                    if mastering_counts:
                        mastering_widget = QWidget()
                        mastering_layout = QVBoxLayout(mastering_widget)
                        mastering_title = QLabel("Ingenieros de Masterización")
                        mastering_title.setStyleSheet("font-weight: bold;")
                        mastering_layout.addWidget(mastering_title)
                        
                        # Contenedor horizontal para gráfico y tabla
                        mastering_content = QWidget()
                        mastering_content_layout = QHBoxLayout(mastering_content)
                        
                        # Preparar gráfico
                        mastering_chart_container = QWidget()
                        mastering_chart_layout = QVBoxLayout(mastering_chart_container)
                        
                        # Crear datos para el gráfico
                        mastering_chart_data = [(engineer, len(albums)) for engineer, albums in 
                                            sorted(mastering_counts.items(), key=lambda x: len(x[1]), reverse=True)]
                        
                        # Limitar a los 15 principales para el gráfico
                        if len(mastering_chart_data) > 15:
                            chart_data = mastering_chart_data[:15]
                        else:
                            chart_data = mastering_chart_data
                        
                        # Crear gráfico
                        mastering_chart = ChartFactory.create_pie_chart(
                            chart_data,
                            f"Ingenieros de Masterización - {self.selected_artist}"
                        )
                        
                        if mastering_chart:
                            mastering_chart_layout.addWidget(mastering_chart)
                        else:
                            no_chart = QLabel("No se pudo crear el gráfico")
                            no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            mastering_chart_layout.addWidget(no_chart)
                        
                        # Preparar tabla
                        mastering_table_container = QWidget()
                        mastering_table_layout = QVBoxLayout(mastering_table_container)
                        
                        mastering_table = QTableWidget()
                        mastering_table.setColumnCount(2)
                        mastering_table.setHorizontalHeaderLabels(["Ingeniero de Masterización", "Álbumes"])
                        mastering_table.setRowCount(len(mastering_counts))
                        
                        for i, (engineer, albums) in enumerate(sorted(mastering_counts.items(), key=lambda x: len(x[1]), reverse=True)):
                            mastering_table.resizeColumnsToContents()
                            mastering_table_layout.addWidget(mastering_table)
                        
                            # Añadir gráfico y tabla al contenedor horizontal
                            mastering_content_layout.addWidget(mastering_chart_container, 1)
                            mastering_content_layout.addWidget(mastering_table_container, 1)
                            
                            # Añadir el contenedor al layout de ingenieros de masterización
                            mastering_layout.addWidget(mastering_content)
                            
                            # Añadir widget de masterización al splitter
                            splitter.addWidget(mastering_widget)
                        
                        # Añadir splitter al layout principal
                        layout.addWidget(splitter)
                    else:
                        # Si no hay datos agrupados
                        # Crear tabla con los datos de cada álbum
                        album_table = QTableWidget()
                        album_table.setColumnCount(4)
                        album_table.setHorizontalHeaderLabels(["Álbum", "Productores", "Ingenieros", "Masterización"])
                        album_table.setRowCount(len(album_data))
                        
                        for i, (producers, engineers, mastering, album) in enumerate(album_data):
                            album_table.setItem(i, 0, QTableWidgetItem(str(album) or ""))
                            album_table.setItem(i, 1, QTableWidgetItem(str(producers) or ""))
                            album_table.setItem(i, 2, QTableWidgetItem(str(engineers) or ""))
                            album_table.setItem(i, 3, QTableWidgetItem(str(mastering) or ""))
                        
                        album_table.resizeColumnsToContents()
                        layout.addWidget(album_table)
                else:
                    # Intentar obtener datos de discogs_discography
                    cursor.execute("""
                        SELECT 
                            extraartists
                        FROM 
                            discogs_discography
                        WHERE 
                            artist_id = ? AND
                            extraartists IS NOT NULL AND
                            extraartists != '' AND
                            extraartists != '[]'
                    """, (self.selected_artist_id,))
                    
                    extraartists_data = cursor.fetchall()
                    
                    if extraartists_data:
                        # Procesar datos
                        role_counts = {}
                        
                        for extraartists_json, in extraartists_data:
                            try:
                                extraartists = json.loads(extraartists_json)
                                if isinstance(extraartists, list):
                                    for artist_obj in extraartists:
                                        if isinstance(artist_obj, dict) and 'name' in artist_obj and 'role' in artist_obj:
                                            name = str(artist_obj['name'])
                                            role = str(artist_obj['role'])
                                            
                                            if role not in role_counts:
                                                role_counts[role] = {}
                                            
                                            if name in role_counts[role]:
                                                role_counts[role][name] += 1
                                            else:
                                                role_counts[role][name] = 1
                            except json.JSONDecodeError:
                                # Si no es JSON válido, ignorar
                                pass
                        
                        # Mostrar información por rol
                        if role_counts:
                            # Crear un splitter para organizar las secciones
                            splitter = QSplitter(Qt.Orientation.Vertical)
                            
                            # Filtrar roles relacionados con producción
                            production_roles = [
                                'Producer', 'Co-producer', 'Executive Producer', 
                                'Engineer', 'Recording Engineer', 'Mastering Engineer', 
                                'Mix Engineer', 'Mixing Engineer', 'Sound Engineer',
                                'Recorded By', 'Mixed By', 'Mastered By'
                            ]
                            
                            # Agrupar roles similares
                            grouped_roles = {
                                'Productores': ['Producer', 'Co-producer', 'Executive Producer'],
                                'Ingenieros': ['Engineer', 'Recording Engineer', 'Sound Engineer', 'Recorded By'],
                                'Mezcla': ['Mix Engineer', 'Mixing Engineer', 'Mixed By'],
                                'Masterización': ['Mastering Engineer', 'Mastered By']
                            }
                            
                            # Procesar cada grupo
                            for group_name, roles in grouped_roles.items():
                                group_data = {}
                                
                                # Recopilar datos para este grupo
                                for role in roles:
                                    if role in role_counts:
                                        for name, count in role_counts[role].items():
                                            if name in group_data:
                                                group_data[name] += count
                                            else:
                                                group_data[name] = count
                                
                                # Mostrar si hay datos
                                if group_data:
                                    group_widget = QWidget()
                                    group_layout = QVBoxLayout(group_widget)
                                    group_title = QLabel(group_name)
                                    group_title.setStyleSheet("font-weight: bold;")
                                    group_layout.addWidget(group_title)
                                    
                                    # Contenedor horizontal para gráfico y tabla
                                    group_content = QWidget()
                                    group_content_layout = QHBoxLayout(group_content)
                                    
                                    # Contenedor para el gráfico
                                    chart_container = QWidget()
                                    chart_layout = QVBoxLayout(chart_container)
                                    
                                    # Crear datos para el gráfico
                                    chart_data = [(name, count) for name, count in sorted(group_data.items(), key=lambda x: x[1], reverse=True)]
                                    
                                    # Limitar a los 15 principales para el gráfico
                                    if len(chart_data) > 15:
                                        display_data = chart_data[:15]
                                    else:
                                        display_data = chart_data
                                    
                                    # Crear gráfico
                                    chart = ChartFactory.create_pie_chart(
                                        display_data,
                                        f"{group_name} - {self.selected_artist}"
                                    )
                                    
                                    if chart:
                                        chart_layout.addWidget(chart)
                                    else:
                                        no_chart = QLabel("No se pudo crear el gráfico")
                                        no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                        chart_layout.addWidget(no_chart)
                                    
                                    # Contenedor para la tabla
                                    table_container = QWidget()
                                    table_layout = QVBoxLayout(table_container)
                                    
                                    # Tabla con todos los nombres
                                    table = QTableWidget()
                                    table.setColumnCount(2)
                                    table.setHorizontalHeaderLabels(["Nombre", "Cantidad"])
                                    table.setRowCount(len(chart_data))
                                    
                                    for i, (name, count) in enumerate(chart_data):
                                        table.setItem(i, 0, QTableWidgetItem(name))
                                        table.setItem(i, 1, QTableWidgetItem(str(count)))
                                    
                                    table.resizeColumnsToContents()
                                    table_layout.addWidget(table)
                                    
                                    # Añadir gráfico y tabla al contenedor horizontal
                                    group_content_layout.addWidget(chart_container, 1)
                                    group_content_layout.addWidget(table_container, 1)
                                    
                                    # Añadir el contenedor al layout del grupo
                                    group_layout.addWidget(group_content)
                                    
                                    # Añadir widget del grupo al splitter
                                    splitter.addWidget(group_widget)
                            
                            # Añadir splitter al layout principal
                            layout.addWidget(splitter)
                        else:
                            no_data = QLabel("No se encontraron roles de producción")
                            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            layout.addWidget(no_data)
                    else:
                        no_data = QLabel("No hay información de productores disponible")
                        no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        layout.addWidget(no_data)
                        
        except Exception as e:
            logging.error(f"Error al cargar datos de productores: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)
    
    def show_collaborator_stats(self):
        """Muestra estadísticas de colaboradores para el artista seleccionado."""
        if not self.selected_artist or not self.selected_artist_id:
            return
        
        # Obtener la página actual
        if self.stacked_widget:
            if self.stacked_widget.count() > 8:
                self.stacked_widget.setCurrentIndex(8)
            else:
                self.stacked_widget.setCurrentIndex(0)
        
        current_page = self.stacked_widget.currentWidget()
        if not current_page:
            return
        
        # Limpiar la página
        layout = self.ensure_widget_has_layout(current_page)
        self.clear_layout(layout)
        
        # Añadir título
        title = QLabel(f"Colaboradores - {self.selected_artist}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Cargar información de colaboradores
        self.load_collaborator_data(layout)
    
    def load_collaborator_data(self, layout):
        """Carga y muestra información sobre los colaboradores del artista."""
        if not self.ensure_db_connection() or not self.selected_artist_id:
            return
        
        cursor = self.conn.cursor()
        try:
            # Intentar obtener datos de discogs_discography
            cursor.execute("""
                SELECT 
                    extraartists, 
                    album_name
                FROM 
                    discogs_discography
                WHERE 
                    artist_id = ? AND
                    extraartists IS NOT NULL AND
                    extraartists != '' AND
                    extraartists != '[]'
            """, (self.selected_artist_id,))
            
            extraartists_data = cursor.fetchall()
            
            if extraartists_data:
                # Procesar datos
                collaborator_counts = {}
                collaborator_roles = {}
                collaborator_albums = {}
                
                for extraartists_json, album in extraartists_data:
                    try:
                        extraartists = json.loads(extraartists_json)
                        if isinstance(extraartists, list):
                            for artist_obj in extraartists:
                                if isinstance(artist_obj, dict) and 'name' in artist_obj and 'role' in artist_obj:
                                    name = artist_obj['name']
                                    role = artist_obj['role']
                                    
                                    # Excluir roles no colaborativos (producción, ingeniería, etc.)
                                    non_collaborative_roles = [
                                        'Producer', 'Co-producer', 'Executive Producer', 
                                        'Engineer', 'Recording Engineer', 'Mastering Engineer', 
                                        'Mix Engineer', 'Mixing Engineer', 'Sound Engineer',
                                        'Recorded By', 'Mixed By', 'Mastered By',
                                        'Design', 'Artwork', 'Photography', 'Layout'
                                    ]
                                    
                                    if role not in non_collaborative_roles:
                                        # Incrementar conteo
                                        if name in collaborator_counts:
                                            collaborator_counts[name] += 1
                                        else:
                                            collaborator_counts[name] = 1
                                        
                                        # Registrar roles
                                        if name in collaborator_roles:
                                            if role not in collaborator_roles[name]:
                                                collaborator_roles[name].append(role)
                                        else:
                                            collaborator_roles[name] = [role]
                                        
                                        # Registrar álbumes
                                        if name in collaborator_albums:
                                            if album not in collaborator_albums[name]:
                                                collaborator_albums[name].append(album)
                                        else:
                                            collaborator_albums[name] = [album]
                    except json.JSONDecodeError:
                        # Si no es JSON válido, ignorar
                        pass
                
                # Crear gráfico si hay datos
                if collaborator_counts:
                    # Convertir a formato para gráfico
                    chart_data = [(name, count) for name, count in sorted(collaborator_counts.items(), key=lambda x: x[1], reverse=True)]
                    
                    # Limitar a los 15 principales para el gráfico
                    if len(chart_data) > 15:
                        display_data = chart_data[:15]
                    else:
                        display_data = chart_data
                    
                    # Crear gráfico
                    chart = ChartFactory.create_pie_chart(
                        display_data,
                        f"Colaboradores - {self.selected_artist}"
                    )
                    
                    if chart:
                        layout.addWidget(chart)
                    
                    # Tabla con todos los colaboradores
                    table = QTableWidget()
                    table.setColumnCount(3)
                    table.setHorizontalHeaderLabels(["Nombre", "Roles", "Álbumes"])
                    table.setRowCount(len(collaborator_counts))
                    
                    for i, (name, count) in enumerate(chart_data):
                        roles = ", ".join(collaborator_roles[name])
                        albums = ", ".join(collaborator_albums[name])
                        
                        table.setItem(i, 0, QTableWidgetItem(name))
                        table.setItem(i, 1, QTableWidgetItem(roles))
                        table.setItem(i, 2, QTableWidgetItem(albums))
                    
                    table.resizeColumnsToContents()
                    layout.addWidget(table)
                else:
                    # Mostrar mensaje alternativo
                    no_collaborators = QLabel("No se encontraron colaboradores claros")
                    no_collaborators.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_collaborators)
                    
                    # Mostrar todos los artistas extra
                    alt_table = QTableWidget()
                    alt_table.setColumnCount(3)
                    alt_table.setHorizontalHeaderLabels(["Nombre", "Rol", "Álbum"])
                    
                    # Recopilar todos los artistas extra
                    all_artists = []
                    for extraartists_json, album in extraartists_data:
                        try:
                            extraartists = json.loads(extraartists_json)
                            if isinstance(extraartists, list):
                                for artist_obj in extraartists:
                                    if isinstance(artist_obj, dict) and 'name' in artist_obj and 'role' in artist_obj:
                                        all_artists.append((artist_obj['name'], artist_obj['role'], album))
                        except json.JSONDecodeError:
                            # Si no es JSON válido, ignorar
                            pass
                    
                    # Ordenar y mostrar
                    all_artists.sort(key=lambda x: (x[0], x[1]))
                    
                    if all_artists:
                        alt_table.setRowCount(len(all_artists))
                        
                        for i, (name, role, album) in enumerate(all_artists):
                            alt_table.setItem(i, 0, QTableWidgetItem(name))
                            alt_table.setItem(i, 1, QTableWidgetItem(role))
                            alt_table.setItem(i, 2, QTableWidgetItem(album))
                        
                        alt_table.resizeColumnsToContents()
                        layout.addWidget(alt_table)
                    else:
                        no_extra = QLabel("No hay información sobre artistas adicionales")
                        no_extra.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        layout.addWidget(no_extra)
            else:
                # Intentar obtener datos de member_of
                cursor.execute("""
                    SELECT 
                        member_of
                    FROM 
                        artists
                    WHERE 
                        id = ? AND
                        member_of IS NOT NULL AND
                        member_of != ''
                """, (self.selected_artist_id,))
                
                member_of_data = cursor.fetchone()
                
                if member_of_data and member_of_data[0]:
                    member_of = member_of_data[0]
                    
                    # Intentar procesar como JSON
                    try:
                        groups = json.loads(member_of)
                        if isinstance(groups, list):
                            # Crear una tabla
                            table = QTableWidget()
                            table.setColumnCount(1)
                            table.setHorizontalHeaderLabels(["Grupos"])
                            table.setRowCount(len(groups))
                            
                            for i, group in enumerate(groups):
                                table.setItem(i, 0, QTableWidgetItem(group))
                            
                            table.resizeColumnsToContents()
                            layout.addWidget(table)
                        else:
                            # Si no es una lista, mostrar como texto
                            groups_label = QLabel(f"Grupos: {member_of}")
                            layout.addWidget(groups_label)
                    except json.JSONDecodeError:
                        # Si no es JSON válido, intentar dividir por comas
                        if ',' in member_of:
                            groups = [g.strip() for g in member_of.split(',')]
                            
                            # Crear una tabla
                            table = QTableWidget()
                            table.setColumnCount(1)
                            table.setHorizontalHeaderLabels(["Grupos"])
                            table.setRowCount(len(groups))
                            
                            for i, group in enumerate(groups):
                                table.setItem(i, 0, QTableWidgetItem(group))
                            
                            table.resizeColumnsToContents()
                            layout.addWidget(table)
                        else:
                            # Si no hay comas, mostrar como texto
                            groups_label = QLabel(f"Grupos: {member_of}")
                            layout.addWidget(groups_label)
                else:
                    no_data = QLabel("No hay información de colaboradores disponible")
                    no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(no_data)
        
        except Exception as e:
            logging.error(f"Error al cargar datos de colaboradores: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)