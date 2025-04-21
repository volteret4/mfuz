from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QStackedWidget, 
                            QComboBox, QLabel, QTableWidget, QTableWidgetItem,
                            QProgressBar, QSplitter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6 import uic
import sqlite3
import os
import sys
from pathlib import Path
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, PROJECT_ROOT
from tools.chart_utils import ChartFactory

# Try to import charts, but don't fail if not available
CHARTS_AVAILABLE = False
try:
    from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet
    from PyQt6.QtCharts import QLineSeries, QValueAxis, QBarCategoryAxis, QDateTimeAxis, QPieSlice
    from PyQt6.QtGui import QPainter
    CHARTS_AVAILABLE = True
except ImportError:
    logging.warning("PyQt6.QtCharts not available. Charts will be displayed as text.")

class StatsModule(BaseModule):
    """Módulo para mostrar estadísticas de la base de datos de música."""
    
    def __init__(self, db_path=None, **kwargs):
        self.db_path = db_path
        self.conn = None
        self.current_category = None
        super().__init__(**kwargs)

        # Verificar disponibilidad de gráficos
        self.charts_available = ChartFactory.is_charts_available()
        if not self.charts_available:
            logging.warning("PyQt6.QtCharts no está disponible. Los gráficos se mostrarán como texto.")
        
    def init_ui(self):
        """Inicializa la interfaz de usuario utilizando el archivo UI."""
        # Intentamos cargar desde el archivo UI
        ui_path = os.path.join(PROJECT_ROOT, "ui", "stats", "stats_module.ui")
        
        if os.path.exists(ui_path):
            try:
                # Cargar directamente con uic
                uic.loadUi(ui_path, self)
                logging.info(f"UI cargada correctamente desde {ui_path}")
                
                # Inicializar referencias a elementos de la UI
                self.init_ui_elements()
                
                # Inicializar layouts para los contenedores de gráficos
                self.init_chart_containers()
                
                # Configuramos las conexiones después de cargar
                self.setup_connections()
                self.init_database()
                return True
            except Exception as e:
                logging.error(f"Error al cargar el archivo UI: {e}")
        else:
            logging.error(f"No se encontró el archivo UI en: {ui_path}")
        
        # Si no se pudo cargar el UI, mostrar mensaje de error
        error_layout = QVBoxLayout(self)
        error_label = QLabel("Error: No se pudo cargar la interfaz. Compruebe el archivo UI.")
        error_label.setStyleSheet("color: red; font-weight: bold;")
        error_layout.addWidget(error_label)
        return False

    def init_ui_elements(self):
        """Inicializa referencias a elementos de la UI para acceso más directo."""
        # Categoría sellos
        self.table_labels = self.findChild(QTableWidget, "table_labels")
        self.chart_container_labels = self.findChild(QWidget, "chart_container_labels")
        self.combo_decade = self.findChild(QComboBox, "combo_decade")
        self.decade_chart_container = self.findChild(QWidget, "decade_chart_container")
        
        # Asegurar que los contenedores tienen layouts
        if self.chart_container_labels and not self.chart_container_labels.layout():
            self.chart_container_labels.setLayout(QVBoxLayout())
        
        if self.decade_chart_container and not self.decade_chart_container.layout():
            self.decade_chart_container.setLayout(QVBoxLayout())
        
        # Verificar elementos encontrados
        logging.info(f"UI Elements: table_labels={self.table_labels is not None}, " +
                    f"chart_container_labels={self.chart_container_labels is not None}, " +
                    f"combo_decade={self.combo_decade is not None}, " + 
                    f"decade_chart_container={self.decade_chart_container is not None}")




    def init_chart_containers(self):
        """Inicializa los layouts de todos los contenedores de gráficos."""
        try:
            # Lista de nombres de contenedores de gráficos
            chart_containers = [
                "chart_container_missing",
                "chart_container_genres",
                "chart_container_artists",
                "chart_container_labels",
                "decade_chart_container",
                "chart_container_years",
                "chart_container_decades",
                "chart_container_countries",
                "chart_container_entity",
                "chart_container_feeds",
                "chart_container_temporal"
            ]
            
            # Inicializar cada contenedor
            for container_name in chart_containers:
                container = self.findChild(QWidget, container_name)
                if container:
                    logging.info(f"Inicializando layout para {container_name}")
                    # Verificamos si ya tiene un layout
                    if container.layout() is None:
                        # Si no tiene layout, creamos uno nuevo
                        layout = QVBoxLayout(container)
                        container.setLayout(layout)  # Explícitamente establecer el layout
                        logging.info(f"Creado nuevo QVBoxLayout para {container_name}")
                    else:
                        logging.info(f"El contenedor {container_name} ya tiene un layout: {type(container.layout()).__name__}")
                else:
                    logging.error(f"No se encontró el contenedor: {container_name}")
        
        except Exception as e:
            logging.error(f"Error al inicializar contenedores de gráficos: {e}")
            import traceback
            logging.error(traceback.format_exc())
        
    def setup_connections(self):
        """Configura las señales y slots."""
        # Conexión del combo de categorías
        self.category_combo.currentIndexChanged.connect(self.change_category)
        
        # Si estamos en la página de escuchas, conectar sus combos
        if hasattr(self, 'combo_source') and hasattr(self, 'combo_stats_type'):
            self.combo_source.currentIndexChanged.connect(lambda: self.update_listen_stats())
            self.combo_stats_type.currentIndexChanged.connect(lambda: self.update_listen_stats())
        
        # Si tenemos el combo de unidad temporal, conectarlo
        if hasattr(self, 'combo_time_unit'):
            self.combo_time_unit.currentIndexChanged.connect(self.update_time_chart)
        
        # Si tenemos el combo de década, conectarlo
        combo_decade = self.findChild(QComboBox, "combo_decade")
        if combo_decade:
            # Desconectar primero (por si ya tenía conexiones)
            try:
                combo_decade.currentIndexChanged.disconnect()
            except:
                pass
            # Conectar de nuevo
            combo_decade.currentIndexChanged.connect(self.update_decade_chart)
            logging.info("Combo de décadas conectado correctamente")
        else:
            logging.warning("No se encontró el combo de décadas para conectar")
        
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
        try:
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
        except Exception as e:
            logging.error(f"Error en change_category: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def load_missing_data_stats(self):
        """Carga estadísticas sobre datos ausentes en la BD."""
        if not self.conn:
            return
        
        # Obtener referencias a los widgets desde el UI
        table = self.findChild(QTableWidget, "table_missing_data")
        summary_label = self.findChild(QLabel, "label_summary")
        chart_container = self.findChild(QWidget, "widget_chart_container_missing")
        
        # Limpiar tabla
        table.setRowCount(0)
        
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
        
        # Actualizar resumen
        if summary_label:
            summary_label.setText(f"Total de campos analizados: {len(results)}")
        
        # Añadir una visualización de los 10 campos con menor completitud
        if len(results) > 0 and chart_container:
            # Limpiar el contenedor de gráficos
            self.clear_layout(chart_container.layout())
            
            # Los 10 peores
            worst_fields = results[:10]
            worst_field_data = [(f"{table}.{field}", comp) for table, field, comp in worst_fields]
            
            chart_view = ChartFactory.create_bar_chart(
                worst_field_data,
                "Campos con menor completitud",
                x_label="Campo",
                y_label="% Completitud"
            )
            
            # Añadir el gráfico al contenedor
            chart_container.layout().addWidget(chart_view)

    def load_genre_stats(self):
        """Carga estadísticas de géneros musicales."""
        if not self.conn:
            logging.error("No hay conexión a la base de datos")
            return
        
        try:
            # Obtener referencias a los widgets desde el UI
            table = self.findChild(QTableWidget, "table_genres")
            chart_container = self.findChild(QWidget, "chart_container_genres")
            
            if not table:
                logging.error("No se encontró el widget table_genres")
                return
            if not chart_container:
                logging.error("No se encontró el widget chart_container_genres")
                return
                    
            # Limpiar tabla
            table.setRowCount(0)
            
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
            table.setRowCount(len(genres))
            
            for i, (genre, count) in enumerate(genres):
                percentage = (count / total_songs_with_genre) * 100 if total_songs_with_genre > 0 else 0
                
                table.setItem(i, 0, QTableWidgetItem(genre))
                table.setItem(i, 1, QTableWidgetItem(str(count)))
                
                # Usar barra de progreso para el porcentaje
                progress = QProgressBar()
                progress.setValue(int(percentage))
                progress.setTextVisible(True)
                progress.setFormat(f"{percentage:.1f}%")
                
                table.setCellWidget(i, 2, progress)
            
            table.resizeColumnsToContents()
            
            # Verificar y crear layout si es necesario
            if chart_container.layout() is None:
                logging.warning(f"chart_container_genres no tiene layout, creando uno nuevo")
                chart_layout = QVBoxLayout(chart_container)
            else:
                chart_layout = chart_container.layout()
                logging.info(f"Usando layout existente para chart_container_genres: {type(chart_layout).__name__}")
                
            # Limpiar el contenedor de gráficos
            self.clear_layout(chart_layout)
            
            # Create chart with proper error handling
            try:
                if len(genres) > 0:
                    chart_view = ChartFactory.create_pie_chart(
                        genres[:15] if len(genres) > 15 else genres,  # Limit to 15 for better visualization
                        "Distribución de Géneros"
                    )
                    
                    if chart_view:
                        # Añadir el gráfico al contenedor
                        chart_layout.addWidget(chart_view)
                        logging.info(f"Gráfico de géneros añadido correctamente")
                    else:
                        error_label = QLabel("No se pudo crear el gráfico de géneros")
                        error_label.setStyleSheet("color: red;")
                        chart_layout.addWidget(error_label)
                        logging.error("ChartFactory.create_pie_chart devolvió None")
                else:
                    no_data = QLabel("No hay datos de géneros disponibles")
                    no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    chart_layout.addWidget(no_data)
            except Exception as e:
                error_label = QLabel(f"Error al crear el gráfico: {str(e)}")
                error_label.setStyleSheet("color: red;")
                chart_layout.addWidget(error_label)
                logging.error(f"Error creando gráfico de géneros: {e}")
                import traceback
                logging.error(traceback.format_exc())
        except Exception as e:
            logging.error(f"Error general en load_genre_stats: {e}")
            import traceback
            logging.error(traceback.format_exc())


                
    def load_listening_stats(self):
        """Carga estadísticas de escuchas (lastfm/listenbrainz)."""
        if not self.conn:
            return
        
        # Obtener referencias a los widgets desde el UI
        source_combo = self.findChild(QComboBox, "combo_source")
        stats_type_combo = self.findChild(QComboBox, "combo_stats_type")
        listen_stats_stack = self.findChild(QStackedWidget, "stacked_listen_stats")
        
        # Limpiar y reiniciar el combo de fuentes
        source_combo.clear()
        
        # Determinar qué fuente de datos usar (LastFM o ListenBrainz)
        cursor = self.conn.cursor()
        
        # Verificar si hay datos de scrobbles (LastFM)
        cursor.execute("SELECT COUNT(*) FROM scrobbles;")
        scrobble_count = cursor.fetchone()[0]
        
        # Verificar si hay datos de listens (ListenBrainz)
        cursor.execute("SELECT COUNT(*) FROM listens;")
        listen_count = cursor.fetchone()[0]
        
        # Añadir fuentes al combo
        if scrobble_count > 0:
            source_combo.addItem(f"LastFM ({scrobble_count} scrobbles)")
        if listen_count > 0:
            source_combo.addItem(f"ListenBrainz ({listen_count} escuchas)")
        
        if source_combo.count() == 0:
            source_combo.addItem("No hay datos de escuchas")
            source_combo.setEnabled(False)
            stats_type_combo.setEnabled(False)
            return
        else:
            source_combo.setEnabled(True)
            stats_type_combo.setEnabled(True)
        
        # Cargar estadísticas iniciales si hay datos
        self.update_listen_stats()

    def update_listen_stats(self):
        """Actualiza las estadísticas de escuchas según la fuente y tipo seleccionados."""
        source_combo = self.findChild(QComboBox, "combo_source")
        stats_type_combo = self.findChild(QComboBox, "combo_stats_type")
        listen_stats_stack = self.findChild(QStackedWidget, "stacked_listen_stats")
        
        if not source_combo or not stats_type_combo or not listen_stats_stack:
            return
            
        if source_combo.currentText().startswith("No hay datos"):
            return
        
        source_type = "lastfm" if "LastFM" in source_combo.currentText() else "listenbrainz"
        stats_type = stats_type_combo.currentIndex()
        
        # Seleccionar la página correspondiente
        listen_stats_stack.setCurrentIndex(stats_type)
        
        # Implementar las estadísticas según el tipo
        if stats_type == 0:  # Top Artistas
            self.load_top_artists_stats(source_type)
        elif stats_type == 1:  # Top Álbumes
            self.load_top_albums_stats(source_type)
        elif stats_type == 2:  # Escuchas por Género
            self.load_genre_listen_stats(source_type)
        elif stats_type == 3:  # Escuchas por Sello
            self.load_label_listen_stats(source_type)
        elif stats_type == 4:  # Tendencias Temporales
            self.load_temporal_listen_stats(source_type)

    def load_top_artists_stats(self, source_type):
        """Carga estadísticas de top artistas."""
        # Obtener referencias a los widgets del UI
        table = self.findChild(QTableWidget, "table_artists")
        chart_container = self.findChild(QWidget, "chart_container_artists")
        
        if not table or not chart_container:
            logging.error(f"No se encontraron widgets para top artistas: table={table is not None}, chart_container={chart_container is not None}")
            return
                
        # Limpiar la tabla
        table.setRowCount(0)
        
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
        
        # Crear el gráfico de barras para los top artistas
        layout = self.ensure_widget_has_layout(chart_container)
        self.clear_layout(layout)
        
        if results:
            chart_view = ChartFactory.create_bar_chart(
                results[:10],  # Solo mostrar los top 10 para el gráfico
                "Top 10 Artistas",
                x_label="Artista",
                y_label="Escuchas"
            )
            layout.addWidget(chart_view)
        else:
            no_data = QLabel("No hay datos de escuchas disponibles.")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("font-size: 14px; color: gray; padding: 20px;")
            layout.addWidget(no_data)

    def load_top_albums_stats(self, source_type):
        """Carga estadísticas de top álbumes."""
        # Obtener la página actual
        page = self.findChild(QWidget, "page_top_albums")
        
        if not page:
            logging.error("No se encontró la página page_top_albums")
            return
        
        # Verificar si ya existe la estructura de widgets
        existing_splitter = page.findChild(QSplitter)
        existing_table = page.findChild(QTableWidget)
        existing_chart_container = None
        
        if existing_splitter:
            # Si ya existe un splitter, buscar el contenedor de gráficos
            for i in range(existing_splitter.count()):
                widget = existing_splitter.widget(i)
                if widget.objectName() == "chart_panel":
                    existing_chart_container = widget.findChild(QWidget, "chart_container")
                    break
        
        if not existing_splitter:
            # Crear un splitter para tabla y gráfico
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Panel para la tabla
            table_panel = QWidget()
            table_panel.setObjectName("table_panel")
            table_layout = QVBoxLayout(table_panel)
            
            table = QTableWidget()
            table.setObjectName("table_albums")
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Álbum", "Artista", "Escuchas"])
            
            # Configurar comportamiento de la tabla
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.horizontalHeader().setStretchLastSection(True)
            
            table_layout.addWidget(table)
            
            # Panel para el gráfico
            chart_panel = QWidget()
            chart_panel.setObjectName("chart_panel")
            chart_layout = QVBoxLayout(chart_panel)
            
            chart_container = QWidget()
            chart_container.setObjectName("chart_container")
            chart_container_layout = QVBoxLayout(chart_container)
            
            chart_layout.addWidget(chart_container)
            
            # Añadir los paneles al splitter
            splitter.addWidget(table_panel)
            splitter.addWidget(chart_panel)
            
            # Configurar proporciones iniciales
            splitter.setSizes([400, 600])
            
            # Limpiar el layout de la página y añadir el splitter
            self.clear_layout(page.layout())
            page.layout().addWidget(splitter)
        else:
            # Usar los widgets existentes
            table = existing_table
            chart_container = existing_chart_container
        
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
        
        # Crear el gráfico de barras para los top álbumes
        layout = self.ensure_widget_has_layout(chart_container)
        self.clear_layout(layout)
        
        if results:
            # Transformar los datos para el gráfico (solo necesitamos album y count)
            album_data = [(f"{album} - {artist}", count) for album, artist, count in results[:10]]
            
            chart_view = ChartFactory.create_bar_chart(
                album_data,
                "Top 10 Álbumes",
                x_label="Álbum",
                y_label="Escuchas"
            )
            layout.addWidget(chart_view)
        else:
            no_data = QLabel("No hay datos de álbumes disponibles.")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("font-size: 14px; color: gray; padding: 20px;")
            layout.addWidget(no_data)

    def load_genre_listen_stats(self, source_type):
        """Carga estadísticas de escuchas por género."""
        # Obtener la página actual
        page = self.findChild(QWidget, "page_genre_listen")
        
        if not page:
            return
            
        # Limpiar página
        self.clear_layout(page.layout())
        
        # Añadir título
        # title = QLabel("Escuchas por Género")
        # title.setStyleSheet("font-size: 16px; font-weight: bold;")
        # page.layout().addWidget(title)
        
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
        chart_view = ChartFactory.create_pie_chart(
            results,
            "Distribución de Escuchas por Género"
        )
        chart_layout.addWidget(chart_view)
        
        # Añadir los paneles al splitter
        splitter.addWidget(table_panel)
        splitter.addWidget(chart_panel)
        
        # Configurar proporciones iniciales
        splitter.setSizes([400, 600])
        
        page.layout().addWidget(splitter)

    def load_label_listen_stats(self, source_type):
        """Carga estadísticas de escuchas por sello discográfico."""
        # Obtener la página actual
        page = self.findChild(QWidget, "page_label_listen")
        
        if not page:
            return
            
        # Limpiar página
        self.clear_layout(page.layout())
        
        # Añadir título
        # title = QLabel("Escuchas por Sello Discográfico")
        # title.setStyleSheet("font-size: 16px; font-weight: bold;")
        # page.layout().addWidget(title)
        
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
        chart_view = ChartFactory.create_pie_chart(
            results,
            "Escuchas por Sello Discográfico"
        )
        chart_layout.addWidget(chart_view)
        
        # Añadir los paneles al splitter
        splitter.addWidget(table_panel)
        splitter.addWidget(chart_panel)
        
        # Configurar proporciones iniciales
        splitter.setSizes([400, 600])
        
        page.layout().addWidget(splitter)

    def update_time_chart(self):
        """Actualiza el gráfico temporal según la unidad seleccionada."""
        # Obtener la página actual y widgets necesarios
        combo_time_unit = self.findChild(QComboBox, "combo_time_unit")
        chart_container = self.findChild(QWidget, "chart_container_temporal")
        combo_source = self.findChild(QComboBox, "combo_source")
        
        if not combo_time_unit or not chart_container or not combo_source:
            return
            
        # Determinar el tipo de fuente
        source_type = "lastfm" if "LastFM" in combo_source.currentText() else "listenbrainz"
        time_unit = combo_time_unit.currentText()
        
        # Limpiar el contenedor
        self.clear_layout(chart_container.layout())
        
        # Determinar la consulta SQL según la unidad temporal
        if source_type == "lastfm":
            date_field = "scrobble_date"
            table = "scrobbles"
        else:
            date_field = "listen_date"
            table = "listens"
        
        cursor = self.conn.cursor()
        
        if time_unit == "Día":
            sql = f"""
                SELECT date({date_field}) as date_group, COUNT(*) as count
                FROM {table}
                GROUP BY date_group
                ORDER BY date_group;
            """
        elif time_unit == "Semana":
            sql = f"""
                SELECT strftime('%Y-%W', {date_field}) as date_group, COUNT(*) as count
                FROM {table}
                GROUP BY date_group
                ORDER BY date_group;
            """
        elif time_unit == "Mes":
            sql = f"""
                SELECT strftime('%Y-%m', {date_field}) as date_group, COUNT(*) as count
                FROM {table}
                GROUP BY date_group
                ORDER BY date_group;
            """
        else:  # Año
            sql = f"""
                SELECT strftime('%Y', {date_field}) as date_group, COUNT(*) as count
                FROM {table}
                GROUP BY date_group
                ORDER BY date_group;
            """
        
        cursor.execute(sql)
        results = cursor.fetchall()
        
        # Crear el gráfico temporal
        chart_view = ChartFactory.create_line_chart(
            results,
            f"Escuchas por {time_unit}",
            x_label="Fecha",
            y_label="Escuchas",
            date_axis=True  # Indicar que es un eje de fechas
        )
        chart_container.layout().addWidget(chart_view)

    def load_temporal_listen_stats(self, source_type):
        """Carga estadísticas temporales de escuchas (por día, mes, año)."""
        # Esta función ahora simplemente llama a update_time_chart
        # ya que los widgets ya están en el UI
        self.update_time_chart()

 
    def load_label_stats(self):
        """Carga estadísticas sobre sellos discográficos."""
        logging.info("Iniciando carga de estadísticas de sellos")
        
        if not self.conn:
            logging.error("No hay conexión a la base de datos")
            return
        
        # Cargar la tabla de sellos
        self.load_label_table()
        
        # Cargar gráfico principal de sellos
        self.load_label_chart()
        
        # Cargar combo de décadas y preparar datos
        self.load_decade_data()
        
        logging.info("Finalizada carga de estadísticas de sellos")

    def load_label_table(self):
        """Carga la tabla de sellos discográficos."""
        # Limpiar tabla
        self.table_labels.setRowCount(0)
        
        # Consultar datos
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT label, COUNT(*) as album_count
            FROM albums
            WHERE label IS NOT NULL AND label != ''
            GROUP BY label
            ORDER BY album_count DESC
            LIMIT 50;
        """)
        
        label_results = cursor.fetchall()
        logging.info(f"Número de sellos encontrados: {len(label_results)}")
        
        # Llenar la tabla
        self.table_labels.setRowCount(len(label_results))
        for i, (label, count) in enumerate(label_results):
            self.table_labels.setItem(i, 0, QTableWidgetItem(label))
            self.table_labels.setItem(i, 1, QTableWidgetItem(str(count)))
        
        self.table_labels.resizeColumnsToContents()
        
        # Guardar los resultados para usarlos en los gráficos
        self.label_results = label_results

    def load_label_chart(self):
        """Carga el gráfico principal de sellos."""
        # Asegurar que tiene layout sin duplicarlo
        layout = self.ensure_layout(self.chart_container_labels)
        
        # Limpiar el contenedor
        self.clear_layout(layout)
        
        # Comprobar si tenemos datos para mostrar
        if not hasattr(self, 'label_results') or not self.label_results:
            no_data = QLabel("No hay datos de sellos disponibles")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_data)
            return
        
        # Crear gráfico
        chart_view = ChartFactory.create_pie_chart(
            self.label_results[:15] if len(self.label_results) > 15 else self.label_results,
            "Distribución de Álbumes por Sello"
        )
        
        if chart_view:
            layout.addWidget(chart_view)
            logging.info("Gráfico de sellos creado correctamente")
        else:
            error_label = QLabel("No se pudo crear el gráfico")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)

    def load_decade_data(self):
        """Carga los datos de décadas y popula el combo."""
        logging.info("Cargando datos por década")
        
        # Asegurar que tiene layout sin duplicarlo
        layout = self.ensure_layout(self.decade_chart_container)
        
        # Limpiar el contenedor
        self.clear_layout(layout)
        
        # Consultar datos para el combo de décadas
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT SUBSTR(year, 1, 3) || '0' as decade
            FROM albums
            WHERE year IS NOT NULL AND year != '' 
            AND label IS NOT NULL AND label != ''
            AND CAST(year AS INTEGER) > 1900
            ORDER BY decade;
        """)
        decades = cursor.fetchall()
        
        # Imprimir décadas encontradas
        decade_values = [row[0] for row in decades if row[0].isdigit()]
        logging.info(f"Décadas encontradas: {decade_values}")
        
        # Limpiar combo
        self.combo_decade.blockSignals(True)  # Bloquear señales mientras actualizamos
        self.combo_decade.clear()
        
        # Llenar con décadas
        for decade in decade_values:
            self.combo_decade.addItem(f"{decade}s")
        
        logging.info(f"Combo década actualizado con {self.combo_decade.count()} elementos")
        
        # Preparar datos para el gráfico por década
        cursor.execute("""
            SELECT CAST(SUBSTR(year, 1, 3) || '0' AS INTEGER) as decade,
                label, COUNT(*) as count
            FROM albums
            WHERE label IS NOT NULL AND label != '' 
            AND year IS NOT NULL AND year != ''
            AND CAST(year AS INTEGER) > 1900
            GROUP BY decade, label
            ORDER BY count DESC;
        """)
        decade_data = cursor.fetchall()
        
        # Procesar datos por década
        self.decades_summary = {}
        
        for decade, label, count in decade_data:
            if decade not in self.decades_summary:
                self.decades_summary[decade] = []
            self.decades_summary[decade].append((label, count))
        
        logging.info(f"Datos por década procesados: {len(self.decades_summary)} décadas")
        
        # Reconectar el combo box a su handler
        try:
            self.combo_decade.currentIndexChanged.disconnect()
        except:
            pass
        
        self.combo_decade.currentIndexChanged.connect(self.update_decade_chart)
        
        # Actualizar gráfico inicial sólo si hay elementos
        if self.combo_decade.count() > 0:
            self.combo_decade.setCurrentIndex(0)
            self.combo_decade.blockSignals(False)  # Desbloquear señales
            logging.info(f"Seleccionada década inicial: {self.combo_decade.currentText()}")
            self.update_decade_chart()
        else:
            self.combo_decade.blockSignals(False)
            no_data = QLabel("No hay datos por década disponibles")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_data)
            logging.warning("No hay décadas disponibles")

    def update_decade_chart(self):
        """Actualiza el gráfico por década seleccionada."""
        logging.info("Iniciando actualización de gráfico por década")
        
        # Verificar que el combo tiene elementos
        if self.combo_decade.count() == 0:
            logging.warning("Combo de décadas está vacío")
            return
            
        # Obtener el valor seleccionado
        selected_decade_text = self.combo_decade.currentText()
        logging.info(f"Década seleccionada: {selected_decade_text}")
        
        # Asegurar que hay un layout en el contenedor
        layout = self.ensure_layout(self.decade_chart_container)
        
        # Limpiar el contenedor
        self.clear_layout(layout)
        
        # Extraer el valor numérico de la década
        try:
            selected_decade = int(selected_decade_text.replace('s', '').replace("'", ""))
            logging.info(f"Valor numérico de década: {selected_decade}")
        except (ValueError, AttributeError) as e:
            logging.error(f"Error al extraer valor numérico de década '{selected_decade_text}': {e}")
            error_label = QLabel(f"Error al interpretar década: {selected_decade_text}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)
            return
        
        # Verificar si tenemos datos para esa década
        if not hasattr(self, 'decades_summary') or selected_decade not in self.decades_summary:
            logging.error(f"No hay datos para la década {selected_decade}")
            no_data = QLabel(f"No hay datos disponibles para los {selected_decade_text}.")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_data)
            return
        
        # Obtener datos para esa década
        decade_data = self.decades_summary[selected_decade]
        logging.info(f"Datos para década {selected_decade}: {len(decade_data)} elementos")
        
        # Crear gráfico
        chart_view = ChartFactory.create_pie_chart(
            decade_data[:15] if len(decade_data) > 15 else decade_data,
            f"Sellos en los {selected_decade_text}"
        )
        
        if chart_view:
            layout.addWidget(chart_view)
            logging.info(f"Gráfico por década {selected_decade_text} creado correctamente")
        else:
            error_label = QLabel("No se pudo crear el gráfico")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)
            logging.error("Error creando gráfico por década")

    def ensure_layout(self, widget, layout_type=QVBoxLayout):
        """Ensures a widget has a layout without creating duplicates."""
        if widget is None:
            return None
            
        layout = widget.layout()
        if layout is None:
            layout = layout_type(widget)
            logging.info(f"Created new {layout_type.__name__} for {widget.objectName()}")
        return layout
            
    def load_time_stats(self):
        """Carga estadísticas temporales (por año de lanzamiento de discos)."""
        if not self.conn:
            return
        
        # Obtener referencias a los widgets
        chart_container_years = self.findChild(QWidget, "chart_container_years")
        table_decades = self.findChild(QTableWidget, "table_decades")
        chart_container_decades = self.findChild(QWidget, "chart_container_decades")
        
        if not chart_container_years or not table_decades or not chart_container_decades:
            return
            
        # Limpiar tabla
        table_decades.setRowCount(0)
        
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
        self.clear_layout(chart_container_years.layout())
        chart_view = ChartFactory.create_line_chart(
            years_data,
            "Distribución de Álbumes por Año",
            x_label="Año",
            y_label="Número de Álbumes"
        )
        chart_container_years.layout().addWidget(chart_view)
        
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
        table_decades.setRowCount(len(sorted_decades))
        for i, (decade, count) in enumerate(sorted_decades):
            decade_str = f"{decade}s"
            table_decades.setItem(i, 0, QTableWidgetItem(decade_str))
            table_decades.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table_decades.resizeColumnsToContents()
        
        # Crear gráfico de distribución por década
        self.clear_layout(chart_container_decades.layout())
        decade_chart = ChartFactory.create_bar_chart(
            [(f"{decade}s", count) for decade, count in sorted_decades],
            "Distribución por Década",
            x_label="Década",
            y_label="Número de Álbumes"
        )
        chart_container_decades.layout().addWidget(decade_chart)

    def load_country_stats(self):
        """Carga estadísticas por país de origen de artistas."""
        if not self.conn:
            return
        
        # Obtener referencias a los widgets
        table_countries = self.findChild(QTableWidget, "table_countries")
        chart_container_countries = self.findChild(QWidget, "chart_container_countries")
        
        if not table_countries or not chart_container_countries:
            return
            
        # Limpiar tabla
        table_countries.setRowCount(0)
        
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
        table_countries.setRowCount(len(results))
        for i, (country, count) in enumerate(results):
            table_countries.setItem(i, 0, QTableWidgetItem(country))
            table_countries.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table_countries.resizeColumnsToContents()
        
        # Crear gráfico para países
        self.clear_layout(chart_container_countries.layout())
        chart_view = ChartFactory.create_pie_chart(
            results,
            "Distribución por País de Origen"
        )
        chart_container_countries.layout().addWidget(chart_view)


    def create_pie_chart(self, data, title, limit=15):
        """
        Crea un gráfico de pastel.
        :param data: Lista de tuplas (nombre, valor)
        :param title: Título del gráfico
        :param limit: Límite de elementos a mostrar (los demás se agrupan como "Otros")
        :return: QWidget con el gráfico
        """
        try:
            if not data:
                logging.warning("No hay datos para crear el gráfico de pastel")
                label = QLabel("No hay datos disponibles")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                return label
            
            if self.is_charts_available():
                # Crear serie de datos para el gráfico
                series = QPieSeries()
                
                # Si hay demasiados datos, agrupar los menos frecuentes como "Otros"
                if len(data) > limit:
                    # Ordenar y tomar los top N
                    sorted_data = sorted(data, key=lambda x: x[1], reverse=True)
                    top_items = sorted_data[:limit-1]
                    
                    # Calcular la suma de los restantes
                    other_sum = sum(count for _, count in sorted_data[limit-1:])
                    
                    # Añadir los elementos principales
                    for name, value in top_items:
                        series.append(str(name), value)
                    
                    # Añadir la categoría "Otros"
                    if other_sum > 0:
                        series.append("Otros", other_sum)
                else:
                    # Añadir todos los elementos
                    for name, value in data:
                        series.append(str(name), value)
                
                # Destacar las porciones al hacer hover
                for slice_index in range(series.count()):
                    slice = series.slices()[slice_index]
                    slice.setExploded(True)
                    slice.setExplodeDistanceFactor(0.05)
                    slice.setLabelVisible(True)
                    slice.setLabelPosition(QPieSlice.LabelPosition.LabelOutside)
                    slice.setLabelArmLengthFactor(0.2)
                    
                    # Calcular porcentaje para la etiqueta
                    percent = (slice.percentage() * 100)
                    slice.setLabel(f"{slice.label()}: {percent:.1f}%")
                
                # Crear el chart y configurarlo
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle(title)
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
                
                # Crear el widget con el chart
                chart_view = QChartView(chart)
                chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                return chart_view
            else:
                # Alternativa de texto si no hay gráficos disponibles
                text_widget = QWidget()
                layout = QVBoxLayout(text_widget)
                
                label_title = QLabel(title)
                label_title.setStyleSheet("font-weight: bold; font-size: 14px;")
                layout.addWidget(label_title)
                
                # Mostrar datos como texto
                for name, value in data[:limit]:
                    label = QLabel(f"{name}: {value}")
                    layout.addWidget(label)
                
                if len(data) > limit:
                    label = QLabel(f"... y {len(data) - limit} más")
                    layout.addWidget(label)
                    
                return text_widget
        except Exception as e:
            logging.error(f"Error al crear gráfico de pastel: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
            # Devolver un widget con mensaje de error
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_label = QLabel(f"Error al crear gráfico: {str(e)}")
            error_label.setStyleSheet("color: red;")
            error_layout.addWidget(error_label)
            return error_widget



    def load_feed_stats(self):
        """Carga estadísticas de feeds."""
        if not self.conn:
            return
        
        # Obtener referencias a los widgets
        label_feeds_title = self.findChild(QLabel, "label_feeds_title")
        table_entity = self.findChild(QTableWidget, "table_entity")
        chart_container_entity = self.findChild(QWidget, "chart_container_entity")
        table_feeds = self.findChild(QTableWidget, "table_feeds") 
        chart_container_feeds = self.findChild(QWidget, "chart_container_feeds")
        
        if not label_feeds_title or not table_entity or not chart_container_entity or not table_feeds or not chart_container_feeds:
            return
            
        # Limpiar tablas
        table_entity.setRowCount(0)
        table_feeds.setRowCount(0)
        
        # Verificar si hay datos de feeds
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM feeds;")
        feed_count = cursor.fetchone()[0]
        
        if feed_count == 0:
            # Mostrar mensaje de no datos
            self.clear_layout(chart_container_entity.layout())
            self.clear_layout(chart_container_feeds.layout())
            
            no_data = QLabel("No hay datos de feeds disponibles en la base de datos.")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("font-size: 14px; color: gray; padding: 20px;")
            
            chart_container_entity.layout().addWidget(no_data)
            return
        
        # Consultar feeds por tipo de entidad
        cursor.execute("""
            SELECT entity_type, COUNT(*) as feed_count
            FROM feeds
            GROUP BY entity_type
            ORDER BY feed_count DESC;
        """)
        
        entity_results = cursor.fetchall()
        
        # Llenar la tabla de entidades
        table_entity.setRowCount(len(entity_results))
        for i, (entity_type, count) in enumerate(entity_results):
            table_entity.setItem(i, 0, QTableWidgetItem(entity_type))
            table_entity.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table_entity.resizeColumnsToContents()
        
        # Crear gráfico para tipos de entidad
        self.clear_layout(chart_container_entity.layout())
        entity_chart = ChartFactory.create_pie_chart(
            entity_results,
            "Feeds por Tipo de Entidad"
        )
        chart_container_entity.layout().addWidget(entity_chart)
        
        # Consultar feeds por nombre
        cursor.execute("""
            SELECT feed_name, COUNT(*) as post_count
            FROM feeds
            GROUP BY feed_name
            ORDER BY post_count DESC;
        """)
        
        feed_results = cursor.fetchall()
        
        # Llenar la tabla de feeds
        table_feeds.setRowCount(len(feed_results))
        for i, (feed_name, count) in enumerate(feed_results):
            table_feeds.setItem(i, 0, QTableWidgetItem(feed_name))
            table_feeds.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table_feeds.resizeColumnsToContents()
        
        # Crear gráfico para nombres de feed
        self.clear_layout(chart_container_feeds.layout())
        feed_chart = ChartFactory.create_bar_chart(
            feed_results[:10],  # Mostrar solo los 10 principales
            "Top 10 Feeds por Publicaciones",
            x_label="Feed",
            y_label="Publicaciones"
        )
        chart_container_feeds.layout().addWidget(feed_chart)

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

    def clear_layout(self, layout):
        """Elimina todos los widgets de un layout de manera segura."""
        if layout is None:
            return
        
        try:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)  # Disconnect from parent first
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())
                    item.layout().setParent(None)
        except Exception as e:
            logging.error(f"Error en clear_layout: {e}")

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

    def ensure_widget_has_layout(self, widget, layout_type=QVBoxLayout):
        """Asegura que un widget tenga un layout asignado, creándolo si es necesario."""
        if widget is None:
            logging.error("Widget es None en ensure_widget_has_layout")
            return None
        
        try:
            # Si el widget no tiene layout, crearle uno
            layout = widget.layout()
            if layout is None:
                logging.info(f"Creando nuevo layout para widget {widget.objectName()}")
                layout = layout_type(widget)
            else:
                logging.info(f"Usando layout existente para widget {widget.objectName()}")
            return layout
        except Exception as e:
            logging.error(f"Error en ensure_widget_has_layout: {e}")
            return None


    def get_layout_safely(self, widget):
        """
        Versión mejorada que garantiza la obtención o creación de un layout funcional.
        Maneja casos extremos y problemas comunes de layouts en PyQt.
        """
        if widget is None:
            logging.error("Widget es None en get_layout_safely")
            return None
            
        widget_name = widget.objectName()
        logging.info(f"Intentando obtener layout para '{widget_name}'")
        
        # PASO 1: Diagnóstico inicial y verificación básica
        widget, existing_layout = self.diagnose_widget_layout(widget_name)
        
        # PASO 2: Si encontramos un layout que parece válido, intentar usarlo directamente
        if existing_layout and hasattr(existing_layout, 'addWidget') and callable(existing_layout.addWidget):
            try:
                # Prueba de funcionalidad - intentar crear y añadir un widget invisible
                test_widget = QLabel("test")
                test_widget.setVisible(False)
                existing_layout.addWidget(test_widget)
                existing_layout.removeWidget(test_widget)
                test_widget.deleteLater()
                
                logging.info(f"Layout existente para '{widget_name}' es funcional")
                return existing_layout
            except Exception as e:
                logging.warning(f"Layout existente para '{widget_name}' no es funcional: {e}")
                # Continuar al siguiente paso - no retornar
        
        # PASO 3: Enfoque más drástico - remover todos los hijos y layouts existentes
        logging.info(f"Reconstruyendo layout para '{widget_name}' desde cero")
        
        # Eliminar todos los widgets hijos
        for child in widget.children():
            if isinstance(child, QWidget):
                child.setParent(None)
                child.deleteLater()
        
        # Enfoque nuclear: recrear el layout completamente
        try:
            # Primero, tratar de eliminar cualquier layout existente aunque no sea detectable
            old_layout = widget.layout()
            if old_layout:
                # En PyQt, no podemos simplemente eliminar un layout, pero podemos reemplazarlo
                dummy = QVBoxLayout()
                widget.setLayout(dummy)
                
            # Finalmente, crear un nuevo layout limpio
            new_layout = QVBoxLayout(widget)
            
            # Verificación final
            if not widget.layout() or not hasattr(widget.layout(), 'addWidget'):
                logging.error(f"Falló la creación final del layout para '{widget_name}'")
                return None
                
            logging.info(f"Layout recreado exitosamente para '{widget_name}'")
            return new_layout
        except Exception as e:
            logging.error(f"Error fatal recreando layout: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None


    def diagnose_widget_layout(self, widget_name):
        """Función de diagnóstico profundo para entender el estado de un widget y su layout"""
        widget = self.findChild(QWidget, widget_name)
        if not widget:
            logging.error(f"DIAGNÓSTICO: Widget '{widget_name}' no encontrado")
            return None, None

        logging.info(f"DIAGNÓSTICO: Widget '{widget_name}' encontrado, tipo: {type(widget).__name__}")
        
        # Examinar el layout
        layout = widget.layout()
        if layout:
            logging.info(f"DIAGNÓSTICO: Layout existente tipo: {type(layout).__name__}, dirección memoria: {id(layout)}")
            # Verificar si el layout tiene métodos esenciales
            has_add_widget = hasattr(layout, 'addWidget') and callable(layout.addWidget)
            has_count = hasattr(layout, 'count') and callable(layout.count)
            logging.info(f"DIAGNÓSTICO: Layout tiene addWidget: {has_add_widget}, tiene count: {has_count}")
            
            # Ver cuántos elementos tiene
            try:
                count = layout.count()
                logging.info(f"DIAGNÓSTICO: Layout tiene {count} elementos")
            except Exception as e:
                logging.error(f"DIAGNÓSTICO: Error al llamar layout.count(): {e}")
        else:
            logging.info(f"DIAGNÓSTICO: Widget no tiene layout directamente asociado")
        
        # Buscar layouts entre los hijos
        layouts_found = []
        for child in widget.children():
            if isinstance(child, QVBoxLayout) or isinstance(child, QHBoxLayout):
                layouts_found.append((type(child).__name__, id(child)))
        
        if layouts_found:
            logging.info(f"DIAGNÓSTICO: Encontrados {len(layouts_found)} layouts entre los hijos: {layouts_found}")
        else:
            logging.info(f"DIAGNÓSTICO: No se encontraron layouts entre los hijos")
        
        return widget, layout




    def debug_ui_structure(self, parent_widget=None):
        """Prints the UI widget hierarchy to help debug widget issues."""
        if parent_widget is None:
            parent_widget = self
            
        def print_widget_tree(widget, level=0):
            indent = "  " * level
            object_name = widget.objectName() or "[unnamed]"
            class_name = widget.__class__.__name__
            logging.info(f"{indent}- {class_name} '{object_name}'")
            
            # Print layout information if it exists
            layout = widget.layout()
            if layout:
                layout_name = layout.__class__.__name__
                layout_count = layout.count() if hasattr(layout, 'count') else 'unknown'
                logging.info(f"{indent}  Layout: {layout_name} with {layout_count} items")
            
            # Recursively print children
            for child in widget.children():
                if isinstance(child, QWidget):
                    print_widget_tree(child, level + 1)
        
        logging.info("--- UI WIDGET HIERARCHY ---")
        print_widget_tree(parent_widget)
        logging.info("---------------------------")