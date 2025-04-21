from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QStackedWidget, 
                            QComboBox, QLabel, QTableWidget, QTableWidgetItem,
                            QProgressBar, QSplitter)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from base_module import BaseModule
import sqlite3
import os
from pathlib import Path
import logging

class StatsModule(BaseModule):
    """Módulo para mostrar estadísticas de la base de datos de música."""
    
    def __init__(self, db_path=None, **kwargs):
        self.db_path = db_path
        self.conn = None
        self.current_category = None
        super().__init__(**kwargs)
        
    def init_ui(self):
        """Inicializa la interfaz de usuario."""
        # Intentamos cargar desde el archivo UI primero
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "estaditicas_module.ui")
        if os.path.exists(ui_path):
            result = self.load_ui_file("estadisticas_module.ui", 
                                      required_widgets=[
                                          "category_combo", 
                                          "stacked_widget", 
                                          "stats_content"
                                      ])
            if result:
                # Configuramos las conexiones después de cargar
                self.setup_connections()
                self.init_database()
                return
        
        # Si fallamos en cargar desde el UI, creamos manualmente
        self.create_manual_ui()
        
    def create_manual_ui(self):
        """Crea la UI manualmente si falla la carga del archivo UI."""
        layout = QVBoxLayout(self)
        
        # Selector de categoría
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Datos Ausentes", 
            "Géneros", 
            "Escuchas", 
            "Sellos", 
            "Tiempo", 
            "Países",
            "Feeds"
        ])
        layout.addWidget(self.category_combo)
        
        # Contenedor principal
        self.stats_content = QWidget()
        content_layout = QVBoxLayout(self.stats_content)
        
        # Widget apilado para diferentes vistas
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)
        
        # Añadir páginas al stacked widget
        for i in range(7):  # Una página por cada categoría
            page = QWidget()
            self.stacked_widget.addWidget(page)
        
        layout.addWidget(self.stats_content)
        
        # Configurar conexiones y base de datos
        self.setup_connections()
        self.init_database()
        
    def setup_connections(self):
        """Configura las señales y slots."""
        self.category_combo.currentIndexChanged.connect(self.change_category)
        
    def init_database(self):
        """Inicializa la conexión a la base de datos."""
        if not self.db_path:
            # Intentar encontrar la base de datos en ubicaciones típicas
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "data", "music.db"),
                os.path.join(os.path.expanduser("~"), ".config", "musicapp", "music.db")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.db_path = path
                    break
        
        if self.db_path and os.path.exists(self.db_path):
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
                logging.info(f"Conectado a la base de datos: {self.db_path}")
                
                # Cargar los datos iniciales
                self.load_initial_data()
            except Exception as e:
                logging.error(f"Error al conectar a la base de datos: {e}")
        else:
            logging.error("No se encontró la base de datos")
            
    def load_initial_data(self):
        """Carga los datos iniciales para la vista actual."""
        # Cargamos los datos para la primera categoría por defecto
        self.change_category(0)
        
    def change_category(self, index):
        """Cambia la categoría de estadísticas mostrada."""
        self.current_category = self.category_combo.currentText()
        self.stacked_widget.setCurrentIndex(index)
        
        # Cargar los datos para la categoría seleccionada
        if self.current_category == "Datos Ausentes":
            self.load_missing_data_stats()
        elif self.current_category == "Géneros":
            self.load_genre_stats()
        elif self.current_category == "Escuchas":
            self.load_listening_stats()
        elif self.current_category == "Sellos":
            self.load_label_stats()
        elif self.current_category == "Tiempo":
            self.load_time_stats()
        elif self.current_category == "Países":
            self.load_country_stats()
        elif self.current_category == "Feeds":
            self.load_feed_stats()
    
    # Métodos para cargar cada tipo de estadística
    def load_missing_data_stats(self):
        """Carga estadísticas sobre datos ausentes en la BD."""
        if not self.conn:
            return
            
        # Preparar la página
        page = self.stacked_widget.widget(0)
        self.clear_page(page)
        
        # Crear layout para esta página
        layout = QVBoxLayout(page)
        
        # Título
        title = QLabel("Análisis de Datos Ausentes en la Base de Datos")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Tabla para mostrar la información
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Tabla", "Campo", "% Completitud"])
        
        # Ajustar el comportamiento de la tabla
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        
        # Obtener las tablas de la base de datos
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Filtrar tablas del sistema o temporales
        tables = [t for t in tables if not t.startswith('sqlite_') and 
                not t.endswith('_fts') and not t.endswith('_config') and 
                not t.endswith('_idx') and not t.endswith('_data')]
        
        # Analizar cada tabla
        results = []
        for table_name in tables:
            # Obtener información sobre las columnas
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name = col[1]
                
                # Excluir columnas de ID y timestamps automáticos
                if col_name.lower() == 'id' or col_name.endswith('_id') or \
                col_name.endswith('_timestamp') or col_name == 'last_updated':
                    continue
                
                # Contar registros totales
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                total = cursor.fetchone()[0]
                
                if total > 0:
                    # Contar valores no nulos
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NOT NULL AND {col_name} != '';")
                    filled = cursor.fetchone()[0]
                    
                    # Calcular porcentaje de completitud
                    completeness = (filled / total) * 100 if total > 0 else 100
                    
                    results.append((table_name, col_name, completeness))
        
        # Ordenar por completitud (ascendente para ver los más incompletos primero)
        results.sort(key=lambda x: x[2])
        
        # Mostrar resultados en la tabla
        table.setRowCount(len(results))
        for i, (table_name, col_name, completeness) in enumerate(results):
            table.setItem(i, 0, QTableWidgetItem(table_name))
            table.setItem(i, 1, QTableWidgetItem(col_name))
            
            # Crear una barra de progreso para el porcentaje
            progress = QProgressBar()
            progress.setValue(int(completeness))
            progress.setTextVisible(True)
            progress.setFormat(f"{completeness:.1f}%")
            
            # Cambiar color basado en completitud
            if completeness < 30:
                progress.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
            elif completeness < 70:
                progress.setStyleSheet("QProgressBar::chunk { background-color: #f39c12; }")
            else:
                progress.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
            
            table.setCellWidget(i, 2, progress)
        
        # Ajustar tamaño de la tabla
        table.resizeColumnsToContents()
        
        layout.addWidget(table)
        
        # Añadir resumen
        summary = QLabel(f"Total de campos analizados: {len(results)}")
        layout.addWidget(summary)
        
    def load_genre_stats(self):
        """Carga estadísticas de géneros musicales."""
        if not self.conn:
            return
            
        # Preparar la página
        page = self.stacked_widget.widget(1)
        self.clear_page(page)
        
        # Crear un splitter para dividir la vista
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel izquierdo - Tabla de géneros
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_title = QLabel("Distribución de Géneros")
        left_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_layout.addWidget(left_title)
        
        # Tabla para mostrar géneros
        genre_table = QTableWidget()
        genre_table.setColumnCount(3)
        genre_table.setHorizontalHeaderLabels(["Género", "Canciones", "Porcentaje"])
        
        # Configurar comportamiento de la tabla
        genre_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        genre_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        genre_table.horizontalHeader().setStretchLastSection(True)
        
        # Consultar la distribución de géneros
        cursor = self.conn.cursor()
        
        # Primero obtener el total de canciones
        cursor.execute("SELECT COUNT(*) FROM songs WHERE genre IS NOT NULL AND genre != '';")
        total_songs_with_genre = cursor.fetchone()[0]
        
        # Luego contar por género
        cursor.execute("""
            SELECT genre, COUNT(*) as count
            FROM songs
            WHERE genre IS NOT NULL AND genre != ''
            GROUP BY genre
            ORDER BY count DESC;
        """)
        
        genres = cursor.fetchall()
        
        # Mostrar resultados en la tabla
        genre_table.setRowCount(len(genres))
        
        for i, (genre, count) in enumerate(genres):
            percentage = (count / total_songs_with_genre) * 100 if total_songs_with_genre > 0 else 0
            
            genre_table.setItem(i, 0, QTableWidgetItem(genre))
            genre_table.setItem(i, 1, QTableWidgetItem(str(count)))
            
            # Usar barra de progreso para el porcentaje
            progress = QProgressBar()
            progress.setValue(int(percentage))
            progress.setTextVisible(True)
            progress.setFormat(f"{percentage:.1f}%")
            
            genre_table.setCellWidget(i, 2, progress)
        
        genre_table.resizeColumnsToContents()
        left_layout.addWidget(genre_table)
        
        # Panel derecho - Gráfico de géneros
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_title = QLabel("Visualización de Géneros")
        right_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(right_title)
        
        # Placeholder para el gráfico (implementaremos con un widget personalizado después)
        chart_placeholder = QLabel("Aquí irá un gráfico de distribución de géneros")
        chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_placeholder.setStyleSheet("background-color: #f0f0f0; padding: 20px;")
        right_layout.addWidget(chart_placeholder)
        
        # Añadir los paneles al splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Configurar proporciones iniciales del splitter
        splitter.setSizes([400, 600])
        
        # Añadir el splitter a la página
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(splitter)
        

    def create_genre_pie_chart(self, genres_data):
        """
        Crea un gráfico circular para géneros musicales.
        
        Args:
            genres_data: Lista de tuplas (género, conteo)
        """
        try:
            from PyQt6.QtChart import QChart, QChartView, QPieSeries, QPieSlice
            
            # Crear una serie para el gráfico de pastel
            series = QPieSeries()
            
            # Límite para no sobrecargar el gráfico con demasiados géneros
            top_genres = genres_data[:10]  # Mostrar los 10 principales
            other_count = sum(count for _, count in genres_data[10:]) if len(genres_data) > 10 else 0
            
            # Añadir los géneros principales
            for genre, count in top_genres:
                slice = series.append(genre, count)
                slice.setLabelVisible(True)
            
            # Añadir "Otros" si hay más géneros
            if other_count > 0:
                slice = series.append("Otros", other_count)
                slice.setLabelVisible(True)
            
            # Crear el gráfico
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle("Distribución de Géneros")
            chart.legend().setVisible(True)
            
            # Crear la vista del gráfico
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            return chart_view
        
        except ImportError:
            # Si no está disponible PyQtChart, mostrar un mensaje
            label = QLabel("No se pudo cargar el módulo PyQtChart. Por favor, instálalo para ver gráficos.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: #f0f0f0; padding: 20px;")
            return label


    def load_listening_stats(self):
        """Carga estadísticas de escuchas (lastfm/listenbrainz)."""
        if not self.conn:
            return
            
        # Preparar la página
        page = self.stacked_widget.widget(2)
        self.clear_page(page)
        
        # Crear layout principal
        layout = QVBoxLayout(page)
        
        # Título
        title = QLabel("Estadísticas de Escuchas")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Determinar qué fuente de datos usar (LastFM o ListenBrainz)
        cursor = self.conn.cursor()
        
        # Verificar si hay datos de scrobbles (LastFM)
        cursor.execute("SELECT COUNT(*) FROM scrobbles;")
        scrobble_count = cursor.fetchone()[0]
        
        # Verificar si hay datos de listens (ListenBrainz)
        cursor.execute("SELECT COUNT(*) FROM listens;")
        listen_count = cursor.fetchone()[0]
        
        # Crear un combo para elegir la fuente
        source_label = QLabel("Fuente de datos:")
        layout.addWidget(source_label)
        
        source_combo = QComboBox()
        if scrobble_count > 0:
            source_combo.addItem(f"LastFM ({scrobble_count} scrobbles)")
        if listen_count > 0:
            source_combo.addItem(f"ListenBrainz ({listen_count} escuchas)")
        
        if source_combo.count() == 0:
            source_combo.addItem("No hay datos de escuchas")
            source_combo.setEnabled(False)
        
        layout.addWidget(source_combo)
        
        # Crear combo para elegir el tipo de estadística
        stats_type_label = QLabel("Tipo de estadística:")
        layout.addWidget(stats_type_label)
        
        stats_type_combo = QComboBox()
        stats_type_combo.addItems([
            "Top Artistas", 
            "Top Álbumes", 
            "Escuchas por Género",
            "Escuchas por Sello",
            "Tendencias Temporales"
        ])
        layout.addWidget(stats_type_combo)
        
        # Widget apilado para las diferentes estadísticas
        listen_stats_stack = QStackedWidget()
        layout.addWidget(listen_stats_stack)
        
        # Añadir páginas al stacked widget
        for i in range(5):  # Una página por cada tipo de estadística
            listen_page = QWidget()
            listen_page_layout = QVBoxLayout(listen_page)
            listen_stats_stack.addWidget(listen_page)
        
        # Conectar señales
        source_combo.currentIndexChanged.connect(lambda: self.update_listen_stats(
            listen_stats_stack, source_combo, stats_type_combo))
        stats_type_combo.currentIndexChanged.connect(lambda: self.update_listen_stats(
            listen_stats_stack, source_combo, stats_type_combo))
        
        # Cargar estadísticas iniciales si hay datos
        if source_combo.count() > 0 and source_combo.isEnabled():
            self.update_listen_stats(listen_stats_stack, source_combo, stats_type_combo)

    def update_listen_stats(self, stack_widget, source_combo, stats_type_combo):
        """
        Actualiza las estadísticas de escuchas según la fuente y tipo seleccionados.
        """
        if source_combo.currentText().startswith("No hay datos"):
            return
        
        source_type = "lastfm" if "LastFM" in source_combo.currentText() else "listenbrainz"
        stats_type = stats_type_combo.currentIndex()
        
        # Seleccionar la página correspondiente
        stack_widget.setCurrentIndex(stats_type)
        
        # Limpiar la página actual
        page = stack_widget.currentWidget()
        self.clear_page(page)
        
        # Crear layout para esta página
        layout = QVBoxLayout(page)
        
        # Implementar las estadísticas según el tipo
        if stats_type == 0:  # Top Artistas
            self.load_top_artists_stats(layout, source_type)
        elif stats_type == 1:  # Top Álbumes
            self.load_top_albums_stats(layout, source_type)
        elif stats_type == 2:  # Escuchas por Género
            self.load_genre_listen_stats(layout, source_type)
        elif stats_type == 3:  # Escuchas por Sello
            self.load_label_listen_stats(layout, source_type)
        elif stats_type == 4:  # Tendencias Temporales
            self.load_temporal_listen_stats(layout, source_type)

    def load_top_artists_stats(self, layout, source_type):
        """Carga estadísticas de top artistas."""
        title = QLabel("Top Artistas")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un splitter para tabla y gráfico
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel para la tabla
        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Artista", "Escuchas"])
        
        # Configurar comportamiento de la tabla
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        
        # Consultar datos
        cursor = self.conn.cursor()
        
        if source_type == "lastfm":
            cursor.execute("""
                SELECT artist_name, COUNT(*) as listen_count
                FROM scrobbles
                GROUP BY artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """)
        else:  # listenbrainz
            cursor.execute("""
                SELECT artist_name, COUNT(*) as listen_count
                FROM listens
                GROUP BY artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """)
        
        results = cursor.fetchall()
        
        # Llenar la tabla
        table.setRowCount(len(results))
        for i, (artist, count) in enumerate(results):
            table.setItem(i, 0, QTableWidgetItem(artist))
            table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table.resizeColumnsToContents()
        table_layout.addWidget(table)
        
        # Panel para el gráfico
        chart_panel = QWidget()
        chart_layout = QVBoxLayout(chart_panel)
        
        # Aquí implementaremos un gráfico para los 10 principales artistas
        # Por ahora usaremos un placeholder
        chart_placeholder = QLabel("Aquí irá un gráfico de top artistas")
        chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_placeholder.setStyleSheet("background-color: #f0f0f0; padding: 20px;")
        chart_layout.addWidget(chart_placeholder)
        
        # Añadir los paneles al splitter
        splitter.addWidget(table_panel)
        splitter.addWidget(chart_panel)
        
        # Configurar proporciones iniciales
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)


    def create_top_artists_bar_chart(self, artists_data):
        """
        Crea un gráfico de barras para top artistas.
        
        Args:
            artists_data: Lista de tuplas (artista, conteo)
        """
        try:
            from PyQt6.QtChart import QChart, QChartView, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QPainter
            
            # Limitar a los 10 primeros artistas
            top_artists = artists_data[:10]
            
            # Crear el conjunto de barras
            bar_set = QBarSet("Escuchas")
            
            # Nombres de artistas para el eje X
            categories = []
            
            # Añadir valores al conjunto
            for artist, count in top_artists:
                bar_set.append(count)
                # Acortar nombres muy largos
                display_name = artist if len(artist) < 20 else artist[:17] + "..."
                categories.append(display_name)
            
            # Crear la serie
            series = QBarSeries()
            series.append(bar_set)
            
            # Crear el gráfico
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle("Top 10 Artistas")
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            
            # Crear ejes
            axis_x = QBarCategoryAxis()
            axis_x.append(categories)
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            axis_y.setRange(0, max(count for _, count in top_artists) * 1.1)  # Añadir un 10% extra
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_y)
            
            chart.legend().setVisible(False)
            
            # Crear la vista del gráfico
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            return chart_view
        
        except ImportError:
            # Si no está disponible PyQtChart, mostrar un mensaje
            label = QLabel("No se pudo cargar el módulo PyQtChart. Por favor, instálalo para ver gráficos.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: #f0f0f0; padding: 20px;")
            return label


    def load_top_artists_stats(self, layout, source_type):
        """Carga estadísticas de top artistas."""
        title = QLabel("Top Artistas")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un splitter para tabla y gráfico
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel para la tabla
        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Artista", "Escuchas"])
        
        # Configurar comportamiento de la tabla
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        
        # Consultar datos
        cursor = self.conn.cursor()
        
        if source_type == "lastfm":
            cursor.execute("""
                SELECT artist_name, COUNT(*) as listen_count
                FROM scrobbles
                GROUP BY artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """)
        else:  # listenbrainz
            cursor.execute("""
                SELECT artist_name, COUNT(*) as listen_count
                FROM listens
                GROUP BY artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """)
        
        results = cursor.fetchall()
        
        # Llenar la tabla
        table.setRowCount(len(results))
        for i, (artist, count) in enumerate(results):
            table.setItem(i, 0, QTableWidgetItem(artist))
            table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table.resizeColumnsToContents()
        table_layout.addWidget(table)
        
        # Panel para el gráfico
        chart_panel = QWidget()
        chart_layout = QVBoxLayout(chart_panel)
        
        # Crear el gráfico real con los datos obtenidos
        chart_view = self.create_top_artists_bar_chart(results)
        chart_layout.addWidget(chart_view)
        
        # Añadir los paneles al splitter
        splitter.addWidget(table_panel)
        splitter.addWidget(chart_panel)
        
        # Configurar proporciones iniciales
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)

    def load_top_albums_stats(self, layout, source_type):
        """Carga estadísticas de top álbumes."""
        title = QLabel("Top Álbumes")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un splitter para tabla y gráfico
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel para la tabla
        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Álbum", "Artista", "Escuchas"])
        
        # Configurar comportamiento de la tabla
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        
        # Consultar datos
        cursor = self.conn.cursor()
        
        if source_type == "lastfm":
            cursor.execute("""
                SELECT album_name, artist_name, COUNT(*) as listen_count
                FROM scrobbles
                WHERE album_name IS NOT NULL AND album_name != ''
                GROUP BY album_name, artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """)
        else:  # listenbrainz
            cursor.execute("""
                SELECT album_name, artist_name, COUNT(*) as listen_count
                FROM listens
                WHERE album_name IS NOT NULL AND album_name != ''
                GROUP BY album_name, artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """)
        
        results = cursor.fetchall()
        
        # Llenar la tabla
        table.setRowCount(len(results))
        for i, (album, artist, count) in enumerate(results):
            table.setItem(i, 0, QTableWidgetItem(album))
            table.setItem(i, 1, QTableWidgetItem(artist))
            table.setItem(i, 2, QTableWidgetItem(str(count)))
        
        table.resizeColumnsToContents()
        table_layout.addWidget(table)
        
        # Panel para el gráfico
        chart_panel = QWidget()
        chart_layout = QVBoxLayout(chart_panel)
        
        # Crear el gráfico para los top álbumes
        # Transformar los datos para el gráfico (solo necesitamos album y count)
        album_data = [(f"{album} - {artist}", count) for album, artist, count in results]
        chart_view = self.create_top_albums_bar_chart(album_data)
        chart_layout.addWidget(chart_view)
        
        # Añadir los paneles al splitter
        splitter.addWidget(table_panel)
        splitter.addWidget(chart_panel)
        
        # Configurar proporciones iniciales
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)

    def create_top_albums_bar_chart(self, albums_data):
        """
        Crea un gráfico de barras para top álbumes.
        
        Args:
            albums_data: Lista de tuplas (álbum, conteo)
        """
        try:
            from PyQt6.QtChart import QChart, QChartView, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QPainter
            
            # Limitar a los 10 primeros álbumes
            top_albums = albums_data[:10]
            
            # Crear el conjunto de barras
            bar_set = QBarSet("Escuchas")
            
            # Nombres de álbumes para el eje X
            categories = []
            
            # Añadir valores al conjunto
            for album, count in top_albums:
                bar_set.append(count)
                # Acortar nombres muy largos
                display_name = album if len(album) < 25 else album[:22] + "..."
                categories.append(display_name)
            
            # Crear la serie
            series = QBarSeries()
            series.append(bar_set)
            
            # Crear el gráfico
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle("Top 10 Álbumes")
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            
            # Crear ejes
            axis_x = QBarCategoryAxis()
            axis_x.append(categories)
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            axis_y.setRange(0, max(count for _, count in top_albums) * 1.1)  # Añadir un 10% extra
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_y)
            
            chart.legend().setVisible(False)
            
            # Crear la vista del gráfico
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            return chart_view
        
        except ImportError:
            # Si no está disponible PyQtChart, mostrar un mensaje
            label = QLabel("No se pudo cargar el módulo PyQtChart. Por favor, instálalo para ver gráficos.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: #f0f0f0; padding: 20px;")
            return label


    def load_genre_listen_stats(self, layout, source_type):
        """Carga estadísticas de escuchas por género."""
        title = QLabel("Escuchas por Género")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un splitter para tabla y gráfico
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel para la tabla
        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Género", "Escuchas"])
        
        # Configurar comportamiento de la tabla
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        
        # Consultar datos
        cursor = self.conn.cursor()
        
        if source_type == "lastfm":
            cursor.execute("""
                SELECT s.genre, COUNT(sc.id) as listen_count
                FROM scrobbles sc
                JOIN songs s ON sc.track_name = s.title AND sc.artist_name = s.artist
                WHERE s.genre IS NOT NULL AND s.genre != ''
                GROUP BY s.genre
                ORDER BY listen_count DESC;
            """)
        else:  # listenbrainz
            cursor.execute("""
                SELECT s.genre, COUNT(l.id) as listen_count
                FROM listens l
                JOIN songs s ON l.track_name = s.title AND l.artist_name = s.artist
                WHERE s.genre IS NOT NULL AND s.genre != ''
                GROUP BY s.genre
                ORDER BY listen_count DESC;
            """)
        
        results = cursor.fetchall()
        
        # Llenar la tabla
        table.setRowCount(len(results))
        for i, (genre, count) in enumerate(results):
            table.setItem(i, 0, QTableWidgetItem(genre))
            table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table.resizeColumnsToContents()
        table_layout.addWidget(table)
        
        # Panel para el gráfico
        chart_panel = QWidget()
        chart_layout = QVBoxLayout(chart_panel)
        
        # Crear gráfico de pie para géneros
        chart_view = self.create_genre_pie_chart(results)
        chart_layout.addWidget(chart_view)
        
        # Añadir los paneles al splitter
        splitter.addWidget(table_panel)
        splitter.addWidget(chart_panel)
        
        # Configurar proporciones iniciales
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)



    def load_label_listen_stats(self, layout, source_type):
        """Carga estadísticas de escuchas por sello discográfico."""
        title = QLabel("Escuchas por Sello Discográfico")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un splitter para tabla y gráfico
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel para la tabla
        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Sello", "Escuchas"])
        
        # Configurar comportamiento de la tabla
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        
        # Consultar datos
        cursor = self.conn.cursor()
        
        if source_type == "lastfm":
            cursor.execute("""
                SELECT a.label, COUNT(sc.id) as listen_count
                FROM scrobbles sc
                JOIN songs s ON sc.track_name = s.title AND sc.artist_name = s.artist
                JOIN albums a ON s.album = a.name
                WHERE a.label IS NOT NULL AND a.label != ''
                GROUP BY a.label
                ORDER BY listen_count DESC;
            """)
        else:  # listenbrainz
            cursor.execute("""
                SELECT a.label, COUNT(l.id) as listen_count
                FROM listens l
                JOIN songs s ON l.track_name = s.title AND l.artist_name = s.artist
                JOIN albums a ON s.album = a.name
                WHERE a.label IS NOT NULL AND a.label != ''
                GROUP BY a.label
                ORDER BY listen_count DESC;
            """)
        
        results = cursor.fetchall()
        
        # Llenar la tabla
        table.setRowCount(len(results))
        for i, (label, count) in enumerate(results):
            table.setItem(i, 0, QTableWidgetItem(label))
            table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table.resizeColumnsToContents()
        table_layout.addWidget(table)
        
        # Panel para el gráfico
        chart_panel = QWidget()
        chart_layout = QVBoxLayout(chart_panel)
        
        # Crear gráfico para sellos discográficos
        # Podemos reutilizar la función de crear gráficos de pastel
        chart_view = self.create_pie_chart(results, "Escuchas por Sello")
        chart_layout.addWidget(chart_view)
        
        # Añadir los paneles al splitter
        splitter.addWidget(table_panel)
        splitter.addWidget(chart_panel)
        
        # Configurar proporciones iniciales
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)

    def create_pie_chart(self, data, title=""):
        """
        Crea un gráfico circular genérico.
        
        Args:
            data: Lista de tuplas (etiqueta, valor)
            title: Título del gráfico
        """
        try:
            from PyQt6.QtChart import QChart, QChartView, QPieSeries, QPieSlice
            from PyQt6.QtGui import QPainter
            
            # Crear una serie para el gráfico de pastel
            series = QPieSeries()
            
            # Límite para no sobrecargar el gráfico
            top_items = data[:10]  # Mostrar los 10 principales
            other_count = sum(count for _, count in data[10:]) if len(data) > 10 else 0
            
            # Añadir los items principales
            for label, count in top_items:
                slice = series.append(label, count)
                slice.setLabelVisible(True)
            
            # Añadir "Otros" si hay más items
            if other_count > 0:
                slice = series.append("Otros", other_count)
                slice.setLabelVisible(True)
            
            # Crear el gráfico
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle(title)
            chart.legend().setVisible(True)
            
            # Crear la vista del gráfico
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            return chart_view
        
        except ImportError:
            # Si no está disponible PyQtChart, mostrar un mensaje
            label = QLabel("No se pudo cargar el módulo PyQtChart. Por favor, instálalo para ver gráficos.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: #f0f0f0; padding: 20px;")
            return label

    def load_temporal_listen_stats(self, layout, source_type):
        """Carga estadísticas temporales de escuchas (por día, mes, año)."""
        title = QLabel("Tendencias Temporales de Escuchas")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un combo para elegir la unidad temporal
        time_unit_layout = QHBoxLayout()
        time_unit_label = QLabel("Agrupar por:")
        time_unit_combo = QComboBox()
        time_unit_combo.addItems(["Día", "Semana", "Mes", "Año"])
        time_unit_layout.addWidget(time_unit_label)
        time_unit_layout.addWidget(time_unit_combo)
        time_unit_layout.addStretch()
        
        layout.addLayout(time_unit_layout)
        
        # Widget para el gráfico
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        
        layout.addWidget(chart_container)
        
        # Función para actualizar el gráfico según la unidad temporal
        def update_time_chart():
            # Limpiar el layout actual
            while chart_layout.count():
                item = chart_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            
            time_unit = time_unit_combo.currentText()
            chart_view = self.create_temporal_chart(source_type, time_unit)
            chart_layout.addWidget(chart_view)
        
        # Conectar señal
        time_unit_combo.currentIndexChanged.connect(update_time_chart)
        
        # Cargar gráfico inicial
        update_time_chart()

    def create_temporal_chart(self, source_type, time_unit):
        """
        Crea un gráfico temporal de escuchas.
        
        Args:
            source_type: 'lastfm' o 'listenbrainz'
            time_unit: 'Día', 'Semana', 'Mes', 'Año'
        """
        try:
            from PyQt6.QtChart import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
            from PyQt6.QtCore import QDateTime, Qt
            from PyQt6.QtGui import QPainter
            
            cursor = self.conn.cursor()
            
            # Determinar la consulta SQL según la unidad temporal
            if source_type == "lastfm":
                date_field = "scrobble_date"
                table = "scrobbles"
            else:
                date_field = "listen_date"
                table = "listens"
            
            if time_unit == "Día":
                sql = f"""
                    SELECT date({date_field}) as date_group, COUNT(*) as count
                    FROM {table}
                    GROUP BY date_group
                    ORDER BY date_group;
                """
                date_format = "yyyy-MM-dd"
            elif time_unit == "Semana":
                sql = f"""
                    SELECT strftime('%Y-%W', {date_field}) as date_group, COUNT(*) as count
                    FROM {table}
                    GROUP BY date_group
                    ORDER BY date_group;
                """
                date_format = "yyyy-'W'w"
            elif time_unit == "Mes":
                sql = f"""
                    SELECT strftime('%Y-%m', {date_field}) as date_group, COUNT(*) as count
                    FROM {table}
                    GROUP BY date_group
                    ORDER BY date_group;
                """
                date_format = "yyyy-MM"
            else:  # Año
                sql = f"""
                    SELECT strftime('%Y', {date_field}) as date_group, COUNT(*) as count
                    FROM {table}
                    GROUP BY date_group
                    ORDER BY date_group;
                """
                date_format = "yyyy"
            
            cursor.execute(sql)
            results = cursor.fetchall()
            
            # Crear serie para el gráfico
            series = QLineSeries()
            
            # Preparar datos para el gráfico
            for date_str, count in results:
                if time_unit == "Día":
                    # date_str ya está en formato ISO
                    date = QDateTime.fromString(date_str, "yyyy-MM-dd")
                elif time_unit == "Semana":
                    # Convertir año-semana a una fecha aproximada
                    year, week = date_str.split('-')
                    date = QDateTime.fromString(f"{year}-01-01", "yyyy-MM-dd")
                    date = date.addDays((int(week) - 1) * 7)
                elif time_unit == "Mes":
                    # Convertir año-mes a una fecha
                    date = QDateTime.fromString(f"{date_str}-01", "yyyy-MM-dd")
                else:  # Año
                    date = QDateTime.fromString(f"{date_str}-01-01", "yyyy-MM-dd")
                
                # Añadir punto a la serie (msecs desde epoch)
                series.append(date.toMSecsSinceEpoch(), count)
            
            # Crear el gráfico
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle(f"Escuchas por {time_unit}")
            
            # Eje X (tiempo)
            axis_x = QDateTimeAxis()
            axis_x.setFormat(date_format)
            axis_x.setTitleText("Fecha")
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axis_x)
            
            # Eje Y (conteo)
            axis_y = QValueAxis()
            axis_y.setLabelFormat("%i")
            axis_y.setTitleText("Escuchas")
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_y)
            
            chart.legend().setVisible(False)
            
            # Crear la vista del gráfico
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            return chart_view
        
        except Exception as e:
            # Mostrar mensaje de error
            label = QLabel(f"Error al crear el gráfico temporal: {e}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: #f0f0f0; padding: 20px; color: red;")
            return label

    def load_time_stats(self):
        """Carga estadísticas temporales (por año de lanzamiento de discos)."""
        if not self.conn:
            return
                
        # Preparar la página
        page = self.stacked_widget.widget(4)
        self.clear_page(page)
        
        # Crear layout para esta página
        layout = QVBoxLayout(page)
        
        # Título
        title = QLabel("Distribución Temporal de Música")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un splitter para dividir la vista
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Panel superior - Distribución de años
        top_panel = QWidget()
        top_layout = QVBoxLayout(top_panel)
        
        year_title = QLabel("Distribución por Año de Lanzamiento")
        year_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_layout.addWidget(year_title)
        
        # Consultar distribución por año
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT year, COUNT(*) as album_count
            FROM albums
            WHERE year IS NOT NULL AND year != ''
            GROUP BY year
            ORDER BY year;
        """)
        
        years_data = cursor.fetchall()
        
        # Crear gráfico de línea temporal
        chart_view = self.create_year_distribution_chart(years_data)
        top_layout.addWidget(chart_view)
        
        # Panel inferior - Tabla de décadas
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        
        decade_title = QLabel("Distribución por Década")
        decade_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        bottom_layout.addWidget(decade_title)
        
        # Crear tabla para décadas
        decade_table = QTableWidget()
        decade_table.setColumnCount(2)
        decade_table.setHorizontalHeaderLabels(["Década", "Álbumes"])
        
        # Configurar comportamiento de la tabla
        decade_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        decade_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        decade_table.horizontalHeader().setStretchLastSection(True)
        
        # Preparar datos por década
        decades = {}
        for year_str, count in years_data:
            try:
                year = int(year_str)
                decade = (year // 10) * 10  # Redondear a la década
                if decade in decades:
                    decades[decade] += count
                else:
                    decades[decade] = count
            except (ValueError, TypeError):
                # Ignorar años no numéricos
                continue
        
        # Ordenar décadas
        sorted_decades = sorted(decades.items())
        
        # Llenar la tabla
        decade_table.setRowCount(len(sorted_decades))
        for i, (decade, count) in enumerate(sorted_decades):
            decade_str = f"{decade}s"
            decade_table.setItem(i, 0, QTableWidgetItem(decade_str))
            decade_table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        decade_table.resizeColumnsToContents()
        bottom_layout.addWidget(decade_table)
        
        # Añadir paneles al splitter
        splitter.addWidget(top_panel)
        splitter.addWidget(bottom_panel)
        
        # Añadir splitter al layout principal
        layout.addWidget(splitter)

    def create_year_distribution_chart(self, years_data):
        """
        Crea un gráfico de distribución de álbumes por año.
        """
        try:
            from PyQt6.QtChart import QChart, QChartView, QLineSeries, QValueAxis
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QPainter
            
            # Crear serie para el gráfico
            series = QLineSeries()
            
            # Convertir datos a puntos en la serie
            valid_years = []
            for year_str, count in years_data:
                try:
                    year = int(year_str)
                    valid_years.append((year, count))
                except (ValueError, TypeError):
                    # Ignorar años no numéricos
                    continue
            
            # Ordenar por año
            valid_years.sort()
            
            for year, count in valid_years:
                series.append(year, count)
            
            # Crear el gráfico
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle("Distribución de Álbumes por Año")
            
            # Configurar ejes
            axis_x = QValueAxis()
            axis_x.setLabelFormat("%i")
            axis_x.setTitleText("Año")
            
            axis_y = QValueAxis()
            axis_y.setLabelFormat("%i")
            axis_y.setTitleText("Número de Álbumes")
            
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
            
            chart.legend().setVisible(False)
            
            # Crear la vista del gráfico
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            return chart_view
        
        except Exception as e:
            # Mostrar mensaje de error
            label = QLabel(f"Error al crear el gráfico de años: {e}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: #f0f0f0; padding: 20px; color: red;")
            return label
            
    def load_country_stats(self):
        """Carga estadísticas por país de origen de artistas."""
        if not self.conn:
            return
                
        # Preparar la página
        page = self.stacked_widget.widget(5)
        self.clear_page(page)
        
        # Crear layout para esta página
        layout = QVBoxLayout(page)
        
        # Título
        title = QLabel("Distribución por País de Origen")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Crear un splitter para tabla y gráfico
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Panel para la tabla
        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["País", "Artistas"])
        
        # Configurar comportamiento de la tabla
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        
        # Consultar datos
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT origin, COUNT(*) as artist_count
            FROM artists
            WHERE origin IS NOT NULL AND origin != ''
            GROUP BY origin
            ORDER BY artist_count DESC;
        """)
        
        results = cursor.fetchall()
        
        # Llenar la tabla
        table.setRowCount(len(results))
        for i, (country, count) in enumerate(results):
            table.setItem(i, 0, QTableWidgetItem(country))
            table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table.resizeColumnsToContents()
        table_layout.addWidget(table)
        
        # Panel para el gráfico
        chart_panel = QWidget()
        chart_layout = QVBoxLayout(chart_panel)
        
        # Crear gráfico para países
        chart_view = self.create_pie_chart(results, "Distribución por País")
        chart_layout.addWidget(chart_view)
        
        # Añadir los paneles al splitter
        splitter.addWidget(table_panel)
        splitter.addWidget(chart_panel)
        
        # Configurar proporciones iniciales
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
    def load_feed_stats(self):
        """Carga estadísticas de feeds."""
        if not self.conn:
            return
                
        # Preparar la página
        page = self.stacked_widget.widget(6)
        self.clear_page(page)
        
        # Crear layout para esta página
        layout = QVBoxLayout(page)
        
        # Título
        title = QLabel("Análisis de Feeds")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Verificar si hay datos de feeds
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM feeds;")
        feed_count = cursor.fetchone()[0]
        
        if feed_count == 0:
            no_data = QLabel("No hay datos de feeds disponibles en la base de datos.")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("font-size: 14px; color: gray; padding: 20px;")
            layout.addWidget(no_data)
            return
        
        # Crear un splitter para dividir la vista
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Panel superior - Por tipo de entidad
        top_panel = QWidget()
        top_layout = QVBoxLayout(top_panel)
        
        entity_title = QLabel("Feeds por Tipo de Entidad")
        entity_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_layout.addWidget(entity_title)
        
        # Consultar feeds por tipo de entidad
        cursor.execute("""
            SELECT entity_type, COUNT(*) as feed_count
            FROM feeds
            GROUP BY entity_type
            ORDER BY feed_count DESC;
        """)
        
        entity_results = cursor.fetchall()
        
        # Crear tabla para tipos de entidad
        entity_table = QTableWidget()
        entity_table.setColumnCount(2)
        entity_table.setHorizontalHeaderLabels(["Tipo de Entidad", "Cantidad"])
        
        # Configurar comportamiento de la tabla
        entity_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        entity_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        entity_table.horizontalHeader().setStretchLastSection(True)
        
        # Llenar la tabla
        entity_table.setRowCount(len(entity_results))
        for i, (entity_type, count) in enumerate(entity_results):
            entity_table.setItem(i, 0, QTableWidgetItem(entity_type))
            entity_table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        entity_table.resizeColumnsToContents()
        top_layout.addWidget(entity_table)
        
        # Panel inferior - Por nombre de feed
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        
        feed_title = QLabel("Feeds por Nombre")
        feed_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        bottom_layout.addWidget(feed_title)
        
        # Consultar feeds por nombre
        cursor.execute("""
            SELECT feed_name, COUNT(*) as post_count
            FROM feeds
            GROUP BY feed_name
            ORDER BY post_count DESC;
        """)
        
        feed_results = cursor.fetchall()
        
        # Crear tabla para nombres de feed
        feed_table = QTableWidget()
        feed_table.setColumnCount(2)
        feed_table.setHorizontalHeaderLabels(["Nombre del Feed", "Publicaciones"])
        
        # Configurar comportamiento de la tabla
        feed_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        feed_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        feed_table.horizontalHeader().setStretchLastSection(True)
        
        # Llenar la tabla
        feed_table.setRowCount(len(feed_results))
        for i, (feed_name, count) in enumerate(feed_results):
            feed_table.setItem(i, 0, QTableWidgetItem(feed_name))
            feed_table.setItem(i, 1, QTableWidgetItem(str(count)))
        
        feed_table.resizeColumnsToContents()
        bottom_layout.addWidget(feed_table)
        
        # Añadir paneles al splitter
        splitter.addWidget(top_panel)
        splitter.addWidget(bottom_panel)
        
        # Añadir splitter al layout principal
        layout.addWidget(splitter)
        
        # Añadir gráfico de pie para entidades
        entity_chart = self.create_pie_chart(entity_results, "Feeds por Tipo de Entidad")
        layout.addWidget(entity_chart)
        


    def on_tab_activated(self):
        """
        Método llamado cuando se activa esta pestaña.
        Utilizado para actualizar los datos si es necesario.
        """
        # Si necesitamos actualizar los datos al cambiar a esta pestaña
        if self.current_category:
            index = self.category_combo.findText(self.current_category)
            if index >= 0:
                self.change_category(index)


    def load_label_stats(self):
        """Carga estadísticas sobre sellos discográficos."""
        if not self.conn:
            return
            
        page = self.stacked_widget.widget(3)
        self.clear_page(page)
        
        # Implementación pendiente



    def clear_page(self, page):
        """Limpia el contenido de una página."""
        # Eliminar todos los widgets hijos
        for i in reversed(range(page.layout().count())):
            widget = page.layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)



    def ensure_db_connection(self):
        """Asegura que hay una conexión activa a la base de datos."""
        if self.db_path and (self.conn is None or not hasattr(self.conn, 'execute')):
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
                return True
            except Exception as e:
                logging.error(f"Error reconectando a la base de datos: {e}")
                return False
        return self.conn is not None

    def cleanup(self):
        """Limpieza antes de cerrar el módulo."""
        if self.conn:
            try:
                self.conn.close()
            except Exception as e:
                logging.error(f"Error al cerrar la conexión DB: {e}")                