from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, 
                            QComboBox, QLabel, QTableWidget, QTableWidgetItem,
                            QProgressBar, QSplitter, QMessageBox, QPushButton,
                            QScrollArea, QTextEdit, QFrame)
from PyQt6.QtCore import Qt
from PyQt6 import uic
import sqlite3
import os
import sys
from pathlib import Path
import logging

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule, PROJECT_ROOT
from tools.chart_utils import ChartFactory
from tools.stats.callbacks_submodule import StatsCallbackHandler
from tools.stats.feeds_callbacks import FeedfunctionssCallbackHandler
from tools.stats.time_callbacks import TimeCallbackHandler

module_path = str(Path(__file__).parent / "submodules" / "stats")
if module_path not in sys.path:
    sys.path.append(module_path)
from feeds_submodule import FeedsSubmodule
from time_submodule import TimeSubmodule

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
    
    def __init__(self, db_path=None, lastfm_username=None, musicbrainz_username=None, **kwargs):
        self.db_path = db_path
        self.lastfm_username = lastfm_username
        self.musicbrainz_username = musicbrainz_username
        self.conn = None
        self.current_category = None
        
        # Initialize callback handler before super().__init__
        # This ensures it's available when needed during initialization
        self.callback_handler = StatsCallbackHandler(self)
        self.FeedsSubmodule = FeedsSubmodule
        super().__init__(**kwargs)

        # Verify charts availability
        self.charts_available = ChartFactory.is_charts_available()
        if not self.charts_available:
            logging.warning("PyQt6.QtCharts no está disponible. Los gráficos se mostrarán como texto.")
        
        # Initialize submodules after UI is ready
        self.init_submodules()


    def init_ui(self):
        """Inicializa la interfaz de usuario utilizando el archivo UI."""
        # Intentamos cargar desde el archivo UI
        ui_path = Path(PROJECT_ROOT, "ui", "stats", "stats_module.ui")
        
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
                
                # Inicializar la base de datos
                self.init_database()
                
                # Verificar la conexión a la base de datos antes de cargar datos
                if not self.ensure_db_connection():
                    self.show_connection_error()
                    return True
                    
                # Carga de datos iniciales
                self.load_initial_data()
                            
                # Setup country navigation if we have the stacked widget
                if hasattr(self, 'stackedWidget_countries'):
                    self.setup_country_navigation()



                return True
            except Exception as e:
                logging.error(f"Error al cargar el archivo UI: {e}")
                import traceback
                logging.error(traceback.format_exc())
        else:
            logging.error(f"No se encontró el archivo UI en: {ui_path}")
        
        # Si no se pudo cargar el UI, mostrar mensaje de error
        error_layout = QVBoxLayout(self)
        error_label = QLabel("Error: No se pudo cargar la interfaz. Compruebe el archivo UI.")
        error_label.setStyleSheet("color: red; font-weight: bold;")
        error_layout.addWidget(error_label)
        return False
    
    
    


    def init_submodules(self):
        """Initialize the submodules for the stats module."""
        # Only initialize if UI is ready
        if not hasattr(self, 'category_combo'):
            logging.error("Cannot initialize submodules: UI not ready")
            return
                
        try:
            # Prepare helper functions for the submodules
            helper_functions = {
                'load_entity_type_stats': self.load_entity_type_stats,
                'load_feed_names_stats': self.load_feed_names_stats if hasattr(self, 'load_feed_names_stats') else None,
                'clear_layout': self.clear_layout,
                'ensure_widget_has_layout': self.ensure_widget_has_layout
            }
            
            # Initialize time submodule
            try:
                # Create TimeSubmodule instance directly
                time_submodule = TimeSubmodule(self, self.conn, helper_functions=helper_functions)
                # Register it with the callback handler
                self.callback_handler.register_submodule('time', time_submodule)
                logging.info("Registered time submodule successfully")
                
                # Setup time callback handler if available
                if hasattr(time_submodule, 'setup_connections'):
                    time_submodule.setup_connections()
                    logging.info("Set up time submodule connections")
                    
            except Exception as e:
                logging.error(f"Error initializing time submodule: {e}")
                import traceback
                logging.error(traceback.format_exc())
            
            # Initialize feeds submodule
            try:
                # Create FeedsSubmodule instance directly
                feeds_submodule = FeedsSubmodule(self, self.conn, self.lastfm_username, self.musicbrainz_username, helper_functions=helper_functions)
                # Register it with the callback handler
                self.callback_handler.register_submodule('feeds', feeds_submodule)
                logging.info("Registered feeds submodule successfully")
                
                # Setup feeds connections if available
                if hasattr(feeds_submodule, 'setup_connections'):
                    feeds_submodule.setup_connections()
                    logging.info("Set up feeds submodule connections")
                   
            except Exception as e:
                logging.error(f"Error initializing feeds submodule: {e}")
                import traceback
                logging.error(traceback.format_exc())

            # Inicializar submódulo de artistas
            try:
                from modules.submodules.stats.artistas_submodule import ArtistsSubmodule
                artists_submodule = ArtistsSubmodule(self, self.conn, self.lastfm_username, self.musicbrainz_username, helper_functions=helper_functions)
                self.callback_handler.register_submodule('artists', artists_submodule)
                logging.info("Registro exitoso del submódulo de artistas")
                
                # Configurar conexiones del submódulo de artistas
                if hasattr(artists_submodule, 'setup_connections'):
                    artists_submodule.setup_connections()
                    logging.info("Conexiones del submódulo de artistas configuradas")
            except Exception as e:
                logging.error(f"Error al inicializar el submódulo de artistas: {e}")
                import traceback
                logging.error(traceback.format_exc())

        except Exception as e:
            logging.error(f"Error initializing submodules: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def on_category_changed(self, index):
        """Handler for category change events."""
        logging.info(f"Category change event received: index={index}")


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
        """Initializes the layouts of all chart containers safely."""
        try:
            # List of chart container names
            chart_containers = [
                "chart_container_missing",
                "chart_container_genres",
                "chart_container_artists",
                "chart_container_labels",
                "decade_chart_container",
                "chart_container_years",
                "chart_container_decades",
                "chart_container_entity",
                "chart_container_feeds",
                "chart_container_temporal",
                "chart_container_countries",
                "chart_countries_artists", 
            ]
            
            # Initialize each container
            for container_name in chart_containers:
                container = self.findChild(QWidget, container_name)
                if container:
                    logging.info(f"Initializing layout for {container_name}")
                    # Only create a layout if the widget doesn't already have one
                    if container.layout() is None:
                        layout = QVBoxLayout(container)
                        logging.info(f"Created new QVBoxLayout for {container_name}")
                    else:
                        logging.info(f"Container {container_name} already has a layout: {type(container.layout()).__name__}")
                else:
                    logging.error(f"Container not found: {container_name}")
        
        except Exception as e:
            logging.error(f"Error initializing chart containers: {e}")
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
        if hasattr(self, 'combo_decade'):
            # Desconectar primero (por si ya tenía conexiones)
            try:
                self.combo_decade.currentIndexChanged.disconnect()
            except:
                pass
            # Conectar de nuevo
            self.combo_decade.currentIndexChanged.connect(self.update_decade_chart)
            logging.info("Combo de décadas conectado correctamente")
        else:
            logging.warning("No se encontró el combo de décadas para conectar")

        # Conexión del combo de categorías de datos ausentes
        if hasattr(self, 'ausentes_tabla_combo'):
            self.ausentes_tabla_combo.currentIndexChanged.connect(lambda: self.load_missing_data_stats())

        # Conectar la selección de la tabla de géneros
        if hasattr(self, 'table_genres'):
            try:
                self.table_genres.itemClicked.disconnect()  # Desconectar conexiones previas
            except:
                pass
            self.table_genres.itemClicked.connect(self.on_genre_selected)
            logging.info("Tabla de géneros conectada correctamente")
        else:
            logging.warning("No se encontró la tabla de géneros para conectar")
        
        # Configurar navegación entre vistas de géneros
        self.setup_genre_chart_navigation()

        if hasattr(self, 'table_labels'):
            self.table_labels.itemClicked.connect(self.on_label_selected)
            logging.info("Tabla de sellos conectada correctamente")
        
        # Conectar el botón de desglose por género
        if hasattr(self, 'sellos_artistas_button'):
            try:
                self.sellos_artistas_button.clicked.disconnect()
            except:
                pass
            self.sellos_artistas_button.clicked.connect(self.on_show_label_genres)
            logging.info("Botón de géneros por sello conectado correctamente")


        
    def init_database(self):
        """Inicializa la conexión a la base de datos."""
        if not self.db_path:
            # Intentar encontrar la base de datos en ubicaciones típicas
            possible_paths = [
                Path(PROJECT_ROOT, ".db", "sqlite", "music.db"),
                Path(os.path.expanduser("~"), ".config", "musicapp", "music.db")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.db_path = path
                    logging.info(f"Base de datos encontrada en: {path}")
                    break
        
        if self.db_path and os.path.exists(self.db_path):
            try:
                if self.conn:
                    try:
                        self.conn.close()
                    except:
                        pass
                        
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
                
                # Verificar conexión con una consulta simple
                cursor = self.conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                logging.info(f"Conectado a la base de datos: {self.db_path}")
                return True
            except Exception as e:
                logging.error(f"Error al conectar a la base de datos: {e}")
                import traceback
                logging.error(traceback.format_exc())
                return False
        else:
            logging.error(f"No se encontró la base de datos. Path actual: {self.db_path}")
            return False
            
    def load_initial_data(self):
        """Carga los datos iniciales para la vista actual."""
        # Cargamos los datos para la primera categoría por defecto
        self.change_category(0)
        

    def show_connection_error(self):
        """Muestra un mensaje de error de conexión en la interfaz."""
        # Encuentra un widget adecuado para mostrar el error
        content_widget = self.findChild(QWidget, "stats_content")
        if not content_widget:
            content_widget = self
        
        # Limpia el layout existente
        if content_widget.layout():
            self.clear_layout(content_widget.layout())
        else:
            content_widget.setLayout(QVBoxLayout())
        
        # Crear mensaje de error
        error_label = QLabel("No se pudo conectar a la base de datos. Por favor verifica la conexión.")
        error_label.setStyleSheet("color: red; font-size: 16px; padding: 20px;")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Añade botón para reintentar
        retry_button = QPushButton("Reintentar conexión")
        retry_button.clicked.connect(self.retry_connection)
        
        # Añade widgets al layout
        content_widget.layout().addWidget(error_label)
        content_widget.layout().addWidget(retry_button)
        content_widget.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)

    def retry_connection(self):
        """Intenta reconectarse a la base de datos."""
        if self.ensure_db_connection():
            # Volver a cargar los datos
            self.load_initial_data()
        else:
            # Mostrar mensaje de error actualizado
            self.show_connection_error()


    def change_category(self, index):
        """Cambia la categoría de estadísticas mostrada."""
        try:
            # Verificar conexión antes de proceder
            if not self.ensure_db_connection():
                self.show_connection_error()
                return
                    
            self.current_category = self.category_combo.currentText()
            logging.info(f"Cambiando a categoría: {self.current_category} (índice {index})")
            
            # Antes del cambio
            logging.debug(f"Índice actual del stacked_widget: {self.stacked_widget.currentIndex()}")
            
            # Establecer el índice correcto
            self.stacked_widget.setCurrentIndex(index)
            
            # Después del cambio
            logging.debug(f"Nuevo índice del stacked_widget: {self.stacked_widget.currentIndex()}")
            
            # Cargar los datos para la categoría seleccionada
            if self.current_category == "Datos Ausentes":
                self.load_missing_data_stats()
            elif self.current_category == "Géneros":
                self.load_genre_stats()
            elif self.current_category == "Escuchas":
                self.load_listening_stats()
            elif self.current_category == "Sellos":
                # Verificar si estamos realmente en la página de sellos
                self.load_label_stats()
            elif self.current_category == "Tiempo":
                self.load_time_stats()
            elif self.current_category == "Países":
                self.load_country_stats()
            elif self.current_category == "Feeds":
                # Use the submodule through the callback handler
                if hasattr(self, 'callback_handler'):
                    self.callback_handler.redirect_to_submodule('load_feed_stats', 'feeds')
                else:
                    logging.error("callback_handler not initialized")
            elif self.current_category == "Artistas":
                # Usar el submódulo a través del manejador de callbacks
                if hasattr(self, 'callback_handler'):
                    # Primero asegurarse de que estamos en la página correcta del stacked widget
                    page_artists = self.findChild(QWidget, "page_artists") 
                    if page_artists:
                        # Buscar el índice de la página
                        for i in range(self.stacked_widget.count()):
                            if self.stacked_widget.widget(i) == page_artists:
                                self.stacked_widget.setCurrentIndex(i)
                                break
                    
                    # Ahora cargar los datos
                    self.callback_handler.redirect_to_submodule('load_artist_stats', 'artists')
                else:
                    logging.error("callback_handler no inicializado")
            
            # Notify about category change after data is loaded
            if hasattr(self, 'callback_handler'):
                self.callback_handler.trigger_event('after_category_changed', index, self.current_category)
            else:
                logging.error("callback_handler not initialized")
                
        except Exception as e:
            logging.error(f"Error en change_category: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def load_missing_data_stats(self):
        """Carga estadísticas sobre datos ausentes en la BD según el tipo seleccionado."""
        if not self.conn:
            return
        
        # Verificar que tenemos los widgets necesarios
        required_widgets = ['table_missing_data', 'label_summary', 'widget_chart_container_missing']
        for widget_name in required_widgets:
            if not hasattr(self, widget_name):
                logging.error(f"Widget '{widget_name}' no encontrado en la UI")
                return
        
        # Obtener referencias directas a los widgets
        table = self.table_missing_data
        summary_label = self.label_summary
        chart_container = self.widget_chart_container_missing
        
        # Usar el combo si existe
        if hasattr(self, 'ausentes_tabla_combo'):
            selected_type = self.ausentes_tabla_combo.currentText()
        else:
            selected_type = "TODAS"
        
        # Limpiar tabla
        table.setRowCount(0)
        
        # Según el tipo seleccionado, determinar las tablas a analizar
        if selected_type == "ARTISTAS":
            results = self.analyze_missing_artist_data()
        elif selected_type == "ALBUMS":
            results = self.analyze_missing_album_data()
        elif selected_type == "CANCIONES":
            results = self.analyze_missing_song_data()
        elif selected_type == "SELLOS":
            results = self.analyze_missing_label_data()
        else:
            # Comportamiento original: analizar todas las tablas
            results = self.analyze_all_missing_data()
        
        # Mostrar resultados en la tabla
        self.display_missing_data_results(results, table, summary_label, chart_container)

    def analyze_all_missing_data(self):
        """Analiza datos ausentes en todas las tablas (comportamiento original)."""
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
        
        return results

    def analyze_missing_artist_data(self):
        """Analiza datos ausentes relacionados con artistas."""
        cursor = self.conn.cursor()
        results = []
        
        # Primero analizar columnas de la tabla artistas
        cursor.execute("PRAGMA table_info(artists);")
        columns = cursor.fetchall()
        
        # Contar artistas totales
        cursor.execute("SELECT COUNT(*) FROM artists;")
        total_artists = cursor.fetchone()[0]
        
        # Analizar cada columna de artistas
        for col in columns:
            col_name = col[1]
            
            # Excluir columnas de ID y timestamps automáticos
            if col_name.lower() == 'id' or col_name.endswith('_id') or \
            col_name.endswith('_timestamp') or col_name == 'last_updated':
                continue
            
            # Contar valores no nulos
            cursor.execute(f"SELECT COUNT(*) FROM artists WHERE {col_name} IS NOT NULL AND {col_name} != '';")
            filled = cursor.fetchone()[0]
            
            # Calcular porcentaje de completitud
            completeness = (filled / total_artists) * 100 if total_artists > 0 else 100
            
            results.append(("artists", col_name, completeness))
        
        # Ahora analizar relaciones con otras tablas
        # Artistas sin redes sociales
        cursor.execute("""
            SELECT COUNT(*) 
            FROM artists a
            LEFT JOIN artists_networks n ON a.id = n.artist_id
            WHERE n.artist_id IS NULL;
        """)
        missing_networks = cursor.fetchone()[0]
        completeness = 100 - ((missing_networks / total_artists) * 100) if total_artists > 0 else 100
        results.append(("artists_networks", "vínculos a redes", completeness))
        
        # Artistas sin feeds
        cursor.execute("""
            SELECT COUNT(*) 
            FROM artists a
            LEFT JOIN (SELECT DISTINCT entity_id FROM feeds WHERE entity_type='artist') f 
            ON a.id = f.entity_id
            WHERE f.entity_id IS NULL;
        """)
        missing_feeds = cursor.fetchone()[0]
        completeness = 100 - ((missing_feeds / total_artists) * 100) if total_artists > 0 else 100
        results.append(("feeds", "noticias del artista", completeness))
        
        # Artistas sin escuchas (lastfm)
        query = f"""
            SELECT COUNT(*) 
            FROM artists a
            LEFT JOIN (SELECT DISTINCT artist_id FROM scrobbles_{self.lastfm_username}) s 
            ON a.id = s.artist_id
            WHERE s.artist_id IS NULL;
        """
        cursor.execute(query)
        missing_scrobbles = cursor.fetchone()[0]
        completeness = 100 - ((missing_scrobbles / total_artists) * 100) if total_artists > 0 else 100
        results.append(("scrobbles", "escuchas lastfm", completeness))
        
        # Artistas sin escuchas (listenbrainz)
        query = f"""
            SELECT COUNT(*) 
            FROM artists a
            LEFT JOIN (SELECT DISTINCT artist_id FROM listens_{self.musicbrainz_username}) s 
            ON a.id = s.artist_id
            WHERE s.artist_id IS NULL;
        """
        cursor.execute(query)
        missing_listens = cursor.fetchone()[0]
        completeness = 100 - ((missing_listens / total_artists) * 100) if total_artists > 0 else 100
        results.append(("listens", "escuchas listenbrainz", completeness))
        
        return results

    def analyze_missing_album_data(self):
        """Analiza datos ausentes relacionados con álbumes."""
        cursor = self.conn.cursor()
        results = []
        
        # Primero analizar columnas de la tabla albums
        cursor.execute("PRAGMA table_info(albums);")
        columns = cursor.fetchall()
        
        # Contar álbumes totales
        cursor.execute("SELECT COUNT(*) FROM albums;")
        total_albums = cursor.fetchone()[0]
        
        # Analizar cada columna de albums
        for col in columns:
            col_name = col[1]
            
            # Excluir columnas de ID y timestamps automáticos
            if col_name.lower() == 'id' or col_name.endswith('_id') or \
            col_name.endswith('_timestamp') or col_name == 'last_updated':
                continue
            
            # Contar valores no nulos
            cursor.execute(f"SELECT COUNT(*) FROM albums WHERE {col_name} IS NOT NULL AND {col_name} != '';")
            filled = cursor.fetchone()[0]
            
            # Calcular porcentaje de completitud
            completeness = (filled / total_albums) * 100 if total_albums > 0 else 100
            
            results.append(("albums", col_name, completeness))
        
        # Álbumes sin datos MusicBrainz
        cursor.execute("""
            SELECT COUNT(*) 
            FROM albums a
            LEFT JOIN mb_release_group mb ON a.id = mb.album_id
            WHERE mb.album_id IS NULL;
        """)
        missing_mb = cursor.fetchone()[0]
        completeness = 100 - ((missing_mb / total_albums) * 100) if total_albums > 0 else 100
        results.append(("mb_release_group", "datos musicbrainz", completeness))
        
        # Álbumes sin feeds
        cursor.execute("""
            SELECT COUNT(*) 
            FROM albums a
            LEFT JOIN (SELECT DISTINCT entity_id FROM feeds WHERE entity_type='album') f 
            ON a.id = f.entity_id
            WHERE f.entity_id IS NULL;
        """)
        missing_feeds = cursor.fetchone()[0]
        completeness = 100 - ((missing_feeds / total_albums) * 100) if total_albums > 0 else 100
        results.append(("feeds", "noticias del álbum", completeness))
        
        # Álbumes sin datos wikidata
        cursor.execute("""
            SELECT COUNT(*) 
            FROM albums a
            LEFT JOIN mb_wikidata w ON a.id = w.album_id
            WHERE w.album_id IS NULL;
        """)
        missing_wikidata = cursor.fetchone()[0]
        completeness = 100 - ((missing_wikidata / total_albums) * 100) if total_albums > 0 else 100
        results.append(("mb_wikidata", "datos wikidata", completeness))
        
        return results

    def analyze_missing_song_data(self):
        """Analiza datos ausentes relacionados con canciones."""
        cursor = self.conn.cursor()
        results = []
        
        # Primero analizar columnas de la tabla songs
        cursor.execute("PRAGMA table_info(songs);")
        columns = cursor.fetchall()
        
        # Contar canciones totales
        cursor.execute("SELECT COUNT(*) FROM songs;")
        total_songs = cursor.fetchone()[0]
        
        # Analizar cada columna de songs
        for col in columns:
            col_name = col[1]
            
            # Excluir columnas de ID y timestamps automáticos
            if col_name.lower() == 'id' or col_name.endswith('_id') or \
            col_name.endswith('_timestamp') or col_name == 'last_updated':
                continue
            
            # Contar valores no nulos
            cursor.execute(f"SELECT COUNT(*) FROM songs WHERE {col_name} IS NOT NULL AND {col_name} != '';")
            filled = cursor.fetchone()[0]
            
            # Calcular porcentaje de completitud
            completeness = (filled / total_songs) * 100 if total_songs > 0 else 100
            
            results.append(("songs", col_name, completeness))
        
        # Canciones sin letras
        cursor.execute("""
            SELECT COUNT(*) 
            FROM songs s
            LEFT JOIN lyrics l ON s.id = l.track_id
            WHERE l.track_id IS NULL;
        """)
        missing_lyrics = cursor.fetchone()[0]
        completeness = 100 - ((missing_lyrics / total_songs) * 100) if total_songs > 0 else 100
        results.append(("lyrics", "letras", completeness))
        
        # Canciones sin enlaces
        cursor.execute("""
            SELECT COUNT(*) 
            FROM songs s
            LEFT JOIN song_links sl ON s.id = sl.song_id
            WHERE sl.song_id IS NULL;
        """)
        missing_links = cursor.fetchone()[0]
        completeness = 100 - ((missing_links / total_songs) * 100) if total_songs > 0 else 100
        results.append(("song_links", "enlaces", completeness))
        
        # Canciones sin escuchas (lastfm)
        query = f"""
            SELECT COUNT(*) 
            FROM songs s
            LEFT JOIN (SELECT DISTINCT song_id FROM scrobbles_{self.lastfm_username}) sc ON s.id = sc.song_id
            WHERE sc.song_id IS NULL;
        """
        cursor.execute(query)
        missing_scrobbles = cursor.fetchone()[0]
        completeness = 100 - ((missing_scrobbles / total_songs) * 100) if total_songs > 0 else 100
        results.append(("scrobbles", "escuchas lastfm", completeness))
        
        # Canciones sin escuchas (listenbrainz)
        query = f"""
            SELECT COUNT(*) 
            FROM songs s
            LEFT JOIN (SELECT DISTINCT song_id FROM listens_{self.musicbrainz_username}) l ON s.id = l.song_id
            WHERE l.song_id IS NULL;
        """
        cursor.execute(query)
        missing_listens = cursor.fetchone()[0]
        completeness = 100 - ((missing_listens / total_songs) * 100) if total_songs > 0 else 100
        results.append(("listens", "escuchas listenbrainz", completeness))
        
        return results

    def analyze_missing_label_data(self):
        """Analiza datos ausentes relacionados con sellos discográficos."""
        cursor = self.conn.cursor()
        results = []
        
        # Primero analizar columnas de la tabla labels
        cursor.execute("PRAGMA table_info(labels);")
        columns = cursor.fetchall()
        
        # Contar sellos totales
        cursor.execute("SELECT COUNT(*) FROM labels;")
        total_labels = cursor.fetchone()[0]
        
        # Analizar cada columna de labels
        for col in columns:
            col_name = col[1]
            
            # Excluir columnas de ID y timestamps automáticos
            if col_name.lower() == 'id' or col_name.endswith('_id') or \
            col_name.endswith('_timestamp') or col_name == 'last_updated':
                continue
            
            # Contar valores no nulos
            cursor.execute(f"SELECT COUNT(*) FROM labels WHERE {col_name} IS NOT NULL AND {col_name} != '';")
            filled = cursor.fetchone()[0]
            
            # Calcular porcentaje de completitud
            completeness = (filled / total_labels) * 100 if total_labels > 0 else 100
            
            results.append(("labels", col_name, completeness))
        
        # Sellos sin relaciones con otros sellos
        cursor.execute("""
            SELECT COUNT(*) 
            FROM labels l
            LEFT JOIN (
                SELECT DISTINCT source_label_id AS label_id FROM label_relationships
                UNION
                SELECT DISTINCT target_label_id AS label_id FROM label_relationships
            ) r ON l.id = r.label_id
            WHERE r.label_id IS NULL;
        """)
        missing_relationships = cursor.fetchone()[0]
        completeness = 100 - ((missing_relationships / total_labels) * 100) if total_labels > 0 else 100
        results.append(("label_relationships", "relaciones entre sellos", completeness))
        
        # Sellos sin álbumes asociados
        cursor.execute("""
            SELECT COUNT(*) 
            FROM labels l
            LEFT JOIN label_release_relationships lrr ON l.id = lrr.label_id
            WHERE lrr.label_id IS NULL;
        """)
        missing_releases = cursor.fetchone()[0]
        completeness = 100 - ((missing_releases / total_labels) * 100) if total_labels > 0 else 100
        results.append(("label_release_relationships", "relaciones con álbumes", completeness))
        
        # Sellos sin datos wikidata
        cursor.execute("""
            SELECT COUNT(*) 
            FROM labels l
            LEFT JOIN mb_wikidata w ON l.id = w.label_id
            WHERE w.label_id IS NULL;
        """)
        missing_wikidata = cursor.fetchone()[0]
        completeness = 100 - ((missing_wikidata / total_labels) * 100) if total_labels > 0 else 100
        results.append(("mb_wikidata", "datos wikidata", completeness))
        
        return results

    def on_genre_label_selected(self, item):
        """Maneja la selección de un sello en la tabla de géneros por sello."""
        if not self.conn:
            logging.error("No hay conexión a la base de datos")
            return
        
        # Obtener el sello seleccionado (siempre en la primera columna)
        row = item.row()
        label = self.table_labels_genres.item(row, 0).text()
        logging.info(f"Sello seleccionado en tabla de géneros: {label}")
        
        # Almacenar el sello seleccionado
        self.selected_label = label
        
        # Importante: No limpiar todo el layout de la página, solo actualizar el gráfico
        if hasattr(self, 'chart_container_genres'):
            # Asegurar que el widget tiene layout
            chart_layout = self.ensure_widget_has_layout(self.chart_container_genres)
            
            # Limpiar SOLO el contenedor del gráfico, no toda la página
            self.clear_layout(chart_layout)
            
            # Cargar los géneros para este sello
            self.load_genres_by_label_chart(label, chart_layout)

    def on_album_label_selected(self, item):
        """Maneja la selección de un sello en la tabla de álbumes por sello."""
        if not self.conn:
            logging.error("No hay conexión a la base de datos")
            return
        
        # Obtener el sello seleccionado (siempre en la primera columna)
        row = item.row()
        label = self.sellos_tabla_albumes.item(row, 0).text()
        logging.info(f"Sello seleccionado en tabla de álbumes: {label}")
        
        # Almacenar el sello seleccionado
        self.selected_label = label
        
        # Cargar los álbumes para este sello
        self.load_albums_by_label(label)



    def on_label_selected(self, item):
        """Maneja la selección de un sello en la tabla de sellos."""
        if not self.conn:
            logging.error("No hay conexión a la base de datos")
            return
        
        # Obtener el sello seleccionado (siempre en la primera columna)
        row = item.row()
        label = self.table_labels.item(row, 0).text()
        logging.info(f"Sello seleccionado: {label}")
        
        # Almacenar el sello seleccionado para usarlo con otras funciones
        self.selected_label = label
        
        # Cargar el gráfico de artistas para este sello
        self.load_artists_by_label(label)
        
        # Cambiar a la vista de artistas en el stacked widget
        if hasattr(self, 'chart_sello_stacked'):
            self.chart_sello_stacked.setCurrentIndex(1)  # Establecer a la página chart_sello_artistas

    def load_genres_by_label_chart(self, label, layout):
        """
        Carga y muestra un gráfico de géneros para un sello específico en el layout proporcionado.
        Esta versión NO afecta a la tabla - solo actualiza el gráfico.
        """
        # Añadir título para el gráfico
        title_label = QLabel(f"Géneros en álbumes del sello: {label}")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Consultar géneros por sello
        cursor = self.conn.cursor()
        try:
            # Consulta para géneros en canciones de álbumes del sello seleccionado
            cursor.execute("""
                SELECT 
                    s.genre, 
                    COUNT(*) as song_count
                FROM 
                    songs s
                JOIN 
                    albums a ON s.album = a.name
                WHERE 
                    a.label = ? AND
                    s.genre IS NOT NULL AND s.genre != ''
                GROUP BY 
                    s.genre
                ORDER BY 
                    song_count DESC;
            """, (label,))
            
            results = cursor.fetchall()
            
            if results:
                # Crear gráfico circular con géneros
                chart_view = ChartFactory.create_pie_chart(
                    results,
                    f"Distribución de Géneros en {label}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info(f"Gráfico de géneros para sello '{label}' creado correctamente")
                else:
                    error_label = QLabel("No se pudo crear el gráfico de géneros")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
                    
            else:
                # No hay datos
                no_data = QLabel(f"No hay datos de géneros para el sello '{label}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al consultar géneros por sello: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)


    def load_artists_by_label(self, label):
        """Carga y muestra un gráfico de artistas para un sello específico."""
        # Asegurarse de que chart_sello_artistas tenga un layout
        chart_container = self.chart_sello_artistas
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Limpiar el contenedor
        self.clear_layout(layout)
        
        # Consultar artistas por sello
        cursor = self.conn.cursor()
        try:
            # Consulta para artistas con álbumes del sello seleccionado
            cursor.execute("""
                SELECT 
                    ar.name as artist_name, 
                    COUNT(a.id) as album_count
                FROM 
                    albums a
                JOIN 
                    artists ar ON a.artist_id = ar.id
                WHERE 
                    a.label = ? AND
                    ar.name IS NOT NULL AND ar.name != ''
                GROUP BY 
                    ar.name
                ORDER BY 
                    album_count DESC
                LIMIT 15;
            """, (label,))
            
            results = cursor.fetchall()
            
            # Si la primera consulta no devuelve resultados (quizás debido a relaciones artist_id faltantes),
            # intentar una consulta alternativa
            if not results:
                cursor.execute("""
                    SELECT 
                        s.artist as artist_name, 
                        COUNT(DISTINCT s.album) as album_count
                    FROM 
                        songs s
                    JOIN 
                        albums a ON s.album = a.name
                    WHERE 
                        a.label = ? AND
                        s.artist IS NOT NULL AND s.artist != ''
                    GROUP BY 
                        s.artist
                    ORDER BY 
                        album_count DESC
                    LIMIT 15;
                """, (label,))
                
                results = cursor.fetchall()
            
            if results:
                # Crear gráfico de barras con artistas
                chart_view = ChartFactory.create_bar_chart(
                    results,
                    f"Artistas con Álbumes en {label}",
                    x_label="Artista",
                    y_label="Álbumes"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info(f"Gráfico de artistas para sello '{label}' creado correctamente")
                else:
                    error_label = QLabel("No se pudo crear el gráfico de artistas")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
                    
            else:
                # No hay datos
                no_data = QLabel(f"No hay artistas con álbumes del sello '{label}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al consultar artistas por sello: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)

    def load_genres_by_label(self, label):
        """Carga y muestra un gráfico de géneros para un sello específico."""
        # Verificamos si existe el contenedor del gráfico
        if hasattr(self, 'chart_container_genres'):
            # Obtenemos el layout
            chart_layout = self.ensure_widget_has_layout(self.chart_container_genres)
            
            # Limpiamos SOLO el contenedor del gráfico
            self.clear_layout(chart_layout)
            
            # Cargamos el gráfico en el contenedor
            self.load_genres_by_label_chart(label, chart_layout)
        else:
            logging.error("No existe el atributo chart_container_genres")

    def on_show_label_genres(self):
        """Maneja el clic en el botón 'géneros por sello'."""
        # Verificar si tenemos un sello seleccionado
        if not hasattr(self, 'selected_label'):
            # Si no hay sello seleccionado, mostrar un error o advertencia
            QMessageBox.warning(self, "Selección requerida", 
                            "Por favor, selecciona primero un sello de la tabla.")
            return
        
        # Mantener en la misma página (verticalLayout_labels_top)
        verticalLayout_labels_top = self.findChild(QWidget, "verticalLayout_labels_top")
        if verticalLayout_labels_top:
            self.stackedWidget.setCurrentWidget(verticalLayout_labels_top)
        
        # Cambiar a la vista de géneros en el stacked widget interno
        if hasattr(self, 'chart_sello_stacked'):
            self.chart_sello_stacked.setCurrentIndex(1)  # Índice para chart_sello_artistas
            logging.info("Cambiando a vista de géneros por sello")
        
        # Cargar el desglose por género para el sello seleccionado
        self.load_genres_by_label(self.selected_label)

    def on_show_label_percentages(self):
        """Maneja el clic en el botón 'porcentajes de sellos'."""
        # Mantener en la misma página (verticalLayout_labels_top)
        verticalLayout_labels_top = self.findChild(QWidget, "verticalLayout_labels_top")
        if verticalLayout_labels_top:
            self.stackedWidget.setCurrentWidget(verticalLayout_labels_top)
        
        # Cambiar a la vista de porcentajes en el stacked widget interno
        if hasattr(self, 'chart_sello_stacked'):
            self.chart_sello_stacked.setCurrentIndex(0)  # Índice para chart_sellos_porcentaje
            logging.info("Cambiando a vista de porcentajes de sellos")
        
        # Recargar el gráfico de porcentajes
        self.load_label_chart()

    def load_albums_by_label(self, label):
        """Carga y muestra un gráfico y tabla de álbumes para un sello específico."""
        logging.info(f"Cargando álbumes para el sello: {label}")
        
        # Asegurarse de que chart_sellos_albumes tenga un layout
        chart_layout = self.ensure_widget_has_layout(self.chart_sellos_albumes)
        
        # Limpiar el contenedor de gráficos
        self.clear_layout(chart_layout)
        
        # Consultar álbumes por sello
        cursor = self.conn.cursor()
        try:
            # Consulta para álbumes del sello seleccionado
            cursor.execute("""
                SELECT 
                    name as album_name, 
                    (SELECT name FROM artists WHERE id = albums.artist_id) as artist_name,
                    year,
                    CASE 
                        WHEN total_tracks IS NULL OR total_tracks = 0 THEN (
                            SELECT COUNT(*) FROM songs 
                            WHERE album = albums.name AND artist = (
                                SELECT name FROM artists WHERE id = albums.artist_id
                            )
                        ) 
                        ELSE total_tracks 
                    END as tracks_count
                FROM 
                    albums
                WHERE 
                    label = ?
                ORDER BY 
                    year DESC, name
                LIMIT 50;
            """, (label,))
            
            results = cursor.fetchall()
            logging.info(f"Consulta de álbumes retornó {len(results)} resultados")
            
            # Llenar la tabla de álbumes
            if hasattr(self, 'sellos_tabla_albumes'):
                self.sellos_tabla_albumes.setRowCount(len(results))
                
                for i, row in enumerate(results):
                    album_name = row[0] if row[0] else "Desconocido"
                    artist_name = row[1] if row[1] else "Desconocido"
                    year = row[2] if row[2] else ""
                    tracks = str(row[3]) if row[3] else "0"
                    
                    self.sellos_tabla_albumes.setItem(i, 0, QTableWidgetItem(album_name))
                    self.sellos_tabla_albumes.setItem(i, 1, QTableWidgetItem(artist_name))
                    self.sellos_tabla_albumes.setItem(i, 2, QTableWidgetItem(str(year)))
                    self.sellos_tabla_albumes.setItem(i, 3, QTableWidgetItem(tracks))
                
                self.sellos_tabla_albumes.resizeColumnsToContents()
                logging.info(f"Tabla de álbumes actualizada con {len(results)} filas")
            
            # También crear un gráfico de barras para algunos álbumes
            if results:
                # Formatear los datos para el chart (usar solo los primeros 15 álbumes)
                chart_data = [(f"{row[0]} ({row[2]})" if row[2] else row[0], row[3]) for row in results[:15]]
                
                # Crear gráfico de barras con álbumes
                chart_view = ChartFactory.create_bar_chart(
                    chart_data,
                    f"Álbumes del sello {label}",
                    x_label="Álbum",
                    y_label="Canciones"
                )
                
                if chart_view:
                    chart_layout.addWidget(chart_view)
                    logging.info(f"Gráfico de álbumes para sello '{label}' creado correctamente")
                else:
                    error_label = QLabel("No se pudo crear el gráfico de álbumes")
                    error_label.setStyleSheet("color: red;")
                    chart_layout.addWidget(error_label)
            else:
                # No hay datos
                no_data = QLabel(f"No hay álbumes del sello '{label}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                chart_layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al consultar álbumes por sello: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            chart_layout.addWidget(error_label)

    def load_label_tables(self):
        """Carga las tablas de sellos en las diferentes páginas."""
        if not self.conn:
            return
            
        try:
            cursor = self.conn.cursor()
            
            # Obtener los datos de sellos
            cursor.execute("""
                SELECT label, COUNT(*) as album_count
                FROM albums
                WHERE label IS NOT NULL AND label != ''
                GROUP BY label
                ORDER BY album_count DESC
                LIMIT 50;
            """)
            
            label_results = cursor.fetchall()
            
            # Verificar que tenemos datos
            if not label_results:
                logging.warning("No se encontraron datos de sellos para las tablas")
                return
                
            # Cargar la tabla de géneros si existe
            if hasattr(self, 'table_labels_genres'):
                self.table_labels_genres.setRowCount(len(label_results))
                for i, (label, count) in enumerate(label_results):
                    self.table_labels_genres.setItem(i, 0, QTableWidgetItem(label))
                    self.table_labels_genres.setItem(i, 1, QTableWidgetItem(str(count)))
                self.table_labels_genres.resizeColumnsToContents()
                logging.info("Tabla de sellos por géneros cargada correctamente")
            
            # Cargar la tabla de álbumes si existe
            if hasattr(self, 'sellos_tabla_albumes'):
                self.sellos_tabla_albumes.setRowCount(len(label_results))
                for i, (label, count) in enumerate(label_results):
                    self.sellos_tabla_albumes.setItem(i, 0, QTableWidgetItem(label))
                    self.sellos_tabla_albumes.setItem(i, 1, QTableWidgetItem(str(count)))
                self.sellos_tabla_albumes.resizeColumnsToContents()
                logging.info("Tabla de sellos por álbumes cargada correctamente")
                
        except Exception as e:
            logging.error(f"Error al cargar tablas de sellos: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def setup_label_connections(self):
        """Configura las conexiones específicas para la pestaña de sellos."""
        try:
            # Conectar selección de tabla de sellos principal
            if hasattr(self, 'table_labels') and self.table_labels is not None:
                try:
                    self.table_labels.itemClicked.disconnect()
                except:
                    pass
                self.table_labels.itemClicked.connect(self.on_label_selected)
                logging.info("Tabla de sellos principal conectada correctamente")
            
            # Conectar tabla de géneros por sello si existe y es válida
            table_labels_genres = self.findChild(QTableWidget, "table_labels_genres")
            if table_labels_genres is not None:
                # Verificar que el objeto es válido antes de conectarlo
                try:
                    # Tratar de acceder a alguna propiedad para verificar si es válido
                    _ = table_labels_genres.rowCount()
                    
                    try:
                        table_labels_genres.itemClicked.disconnect()
                    except:
                        pass
                    table_labels_genres.itemClicked.connect(self.on_genre_label_selected)
                    logging.info("Tabla de sellos por género conectada correctamente")
                    
                    # Guardar referencia para uso futuro
                    self.table_labels_genres = table_labels_genres
                except RuntimeError as e:
                    logging.error(f"Widget table_labels_genres no es válido: {e}")
            
            # Conectar tabla de álbumes por sello si existe
            sellos_tabla_albumes = self.findChild(QTableWidget, "sellos_tabla_albumes")
            if sellos_tabla_albumes is not None:
                try:
                    # Verificar que el objeto es válido
                    _ = sellos_tabla_albumes.rowCount()
                    
                    try:
                        sellos_tabla_albumes.itemClicked.disconnect()
                    except:
                        pass
                    sellos_tabla_albumes.itemClicked.connect(self.on_album_label_selected)
                    logging.info("Tabla de sellos por álbumes conectada correctamente")
                    
                    # Guardar referencia
                    self.sellos_tabla_albumes = sellos_tabla_albumes
                except RuntimeError as e:
                    logging.error(f"Widget sellos_tabla_albumes no es válido: {e}")
            
            # Conectar botones con verificación de existencia
            self.connect_button_safely('action_sellos_artistas', self.on_show_label_genres)
            self.connect_button_safely('action_sellos_albumes', self.on_show_label_albums)
            self.connect_button_safely('action_sellos_info', self.on_show_label_info)
            self.connect_button_safely('action_sellos_decade', self.on_show_label_decades)
            self.connect_button_safely('action_sellos_porcentajes', self.on_show_label_percentages)
            self.connect_button_safely('action_sellos_por_genero', self.on_show_sellos_generos)
        except Exception as e:
            logging.error(f"Error al configurar conexiones de sellos: {e}")
            import traceback
            logging.error(traceback.format_exc())


    def on_show_sellos_generos(self):
        """Maneja el clic en el botón 'sellos_por_genero_button' para mostrar la página de sellos por género."""
        # Acceso directo a la página mediante el atributo creado por uic
        if hasattr(self, 'sellos_por_genero'):
            # Cambiar a la página sellos_por_genero mediante el índice del widget
            self.stackedWidget.setCurrentWidget(self.sellos_por_genero)
            logging.info("Cambiando a vista de sellos_por_genero mediante botón sellos_por_genero_button")
        else:
            logging.error("No se encontró el atributo sellos_por_genero")


    def on_show_label_decades(self):
        """Maneja el clic en el botón de décadas usando atributos directos."""
        # Cambiar a la página de décadas si existe como atributo
        if hasattr(self, 'verticalLayout_labels_bottom'):
            self.stackedWidget.setCurrentWidget(self.verticalLayout_labels_bottom)
            logging.info("Cambiando a vista de décadas")
        else:
            logging.error("No existe el atributo verticalLayout_labels_bottom")


    def connect_button_safely(self, button_name, handler):
        """Conecta un botón a su manejador de forma segura, verificando su existencia."""
        button = self.findChild(QPushButton, button_name)
        
        if button is not None:
            try:
                # Verificar si el botón es válido
                _ = button.text()
                
                try:
                    button.clicked.disconnect()
                except:
                    pass
                button.clicked.connect(handler)
                logging.info(f"Botón {button_name} conectado correctamente")
                
                # Guardar referencia
                setattr(self, button_name, button)
            except RuntimeError as e:
                logging.error(f"Widget {button_name} no es válido: {e}")
        else:
            logging.warning(f"No se encontró el botón {button_name}")

    def on_show_label_albums(self):
        """Maneja el clic en el botón 'álbumes por sello'."""
        # Verificar si tenemos un sello seleccionado
        if not hasattr(self, 'selected_label'):
            # Si no hay sello seleccionado, mostrar un error o advertencia
            QMessageBox.warning(self, "Selección requerida", 
                            "Por favor, selecciona primero un sello de la tabla.")
            return
        
        # Cambiar a la página de álbumes por sello
        self.stackedWidget.setCurrentWidget(self.sellos_albumes)
        
        # Asegurarnos que la tabla existe y tiene columnas configuradas
        if hasattr(self, 'sellos_tabla_albumes'):
            if self.sellos_tabla_albumes.columnCount() == 0:
                self.sellos_tabla_albumes.setColumnCount(4)
                self.sellos_tabla_albumes.setHorizontalHeaderLabels(["Álbum", "Artista", "Año", "Pistas"])
        
        # Cargar los álbumes para el sello seleccionado
        self.load_albums_by_label(self.selected_label)

    def display_missing_data_results(self, results, table, summary_label, chart_container):
        """Muestra los resultados del análisis de datos ausentes en la UI."""
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
        if not self.ensure_db_connection():
            self.show_connection_error()
            return

        try:
            # Obtener referencias a los widgets desde el UI
            table = self.findChild(QTableWidget, "table_genres")
            chart_container = self.findChild(QWidget, "chart_container_genres")
            
            if not table or not chart_container:
                logging.error("No se encontraron los widgets necesarios para la estadística de géneros")
                return
                    
            # Limpiar tabla
            table.setRowCount(0)
            
            # Configuración de la tabla
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Género", "Canciones", "Porcentaje", "Álbumes", "Artistas"])
            
            # Consultar la distribución de géneros
            cursor = self.conn.cursor()
            
            # Primero obtener el total de canciones
            cursor.execute("SELECT COUNT(*) FROM songs WHERE genre IS NOT NULL AND genre != '';")
            total_songs_with_genre = cursor.fetchone()[0]
            
            if total_songs_with_genre == 0:
                logging.warning("No hay canciones con géneros en la base de datos")
                no_data = QLabel("No hay datos de géneros disponibles")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.clear_layout(chart_container.layout())
                chart_container.layout().addWidget(no_data)
                return
            
            # Obtener estadísticas detalladas por género
            cursor.execute("""
                SELECT 
                    genre, 
                    COUNT(*) as song_count,
                    COUNT(DISTINCT album) as album_count,
                    COUNT(DISTINCT artist) as artist_count
                FROM songs
                WHERE genre IS NOT NULL AND genre != ''
                GROUP BY genre
                ORDER BY song_count DESC;
            """)
            
            # Fetch results ONCE and store them
            genre_results = cursor.fetchall()
            logging.info(f"Found {len(genre_results)} genres in database")
            
            if not genre_results:
                logging.warning("La consulta no devolvió géneros")
                no_data = QLabel("No hay datos de géneros disponibles")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.clear_layout(chart_container.layout())
                chart_container.layout().addWidget(no_data)
                return
            
            # Mostrar resultados en la tabla
            table.setRowCount(len(genre_results))
            
            for i, row in enumerate(genre_results):
                if len(row) >= 4:  # Make sure we have all expected columns
                    genre, song_count, album_count, artist_count = row
                    percentage = (song_count / total_songs_with_genre) * 100
                    
                    # Preparar texto del género con posible recorte
                    display_genre = genre
                    if len(genre) > 20:
                        display_genre = genre[:17] + "..."
                    
                    # Crear item para el género
                    genre_item = QTableWidgetItem(display_genre)
                    if len(genre) > 20:
                        genre_item.setToolTip(genre)
                    
                    # Agregar los items a la tabla
                    table.setItem(i, 0, genre_item)
                    table.setItem(i, 1, QTableWidgetItem(str(song_count)))
                    
                    # Usar barra de progreso para el porcentaje
                    progress = QProgressBar()
                    progress.setValue(int(percentage))
                    progress.setTextVisible(True)
                    progress.setFormat(f"{percentage:.1f}%")
                    
                    table.setCellWidget(i, 2, progress)
                    
                    # Agregar columnas de álbumes y artistas
                    table.setItem(i, 3, QTableWidgetItem(str(album_count)))
                    table.setItem(i, 4, QTableWidgetItem(str(artist_count)))
            
            table.resizeColumnsToContents()
            
            # Ensure chart container has a layout
            layout = self.ensure_widget_has_layout(chart_container)
            self.clear_layout(layout)
            
            # Create chart with proper chart data format
            try:
                # Prepare chart data in the correct format
                chart_data = [(str(row[0]), row[1]) for row in genre_results[:15]] if len(genre_results) > 15 else [(str(row[0]), row[1]) for row in genre_results]
                
                # Log the chart data format
                logging.info(f"Chart data format: {chart_data[:3]} ...")
                
                chart_view = ChartFactory.create_pie_chart(
                    chart_data,
                    "Distribución de Géneros"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info("Gráfico de géneros creado correctamente")
                else:
                    error_label = QLabel("No se pudo crear el gráfico de géneros")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
                    logging.error("ChartFactory.create_pie_chart devolvió None")
            except Exception as e:
                error_label = QLabel(f"Error al crear el gráfico: {str(e)}")
                error_label.setStyleSheet("color: red;")
                layout.addWidget(error_label)
                logging.error(f"Error creando gráfico de géneros: {e}")
                import traceback
                logging.error(traceback.format_exc())
        except Exception as e:
            logging.error(f"Error general en load_genre_stats: {e}")
            import traceback
            logging.error(traceback.format_exc())



    def check_data_format(self, data, description):
        """Check if data has the correct format for chart visualization."""
        if not data:
            logging.error(f"Datos de {description} está vacío")
            return False
        
        try:
            # Check a sample of the data
            sample = data[:min(3, len(data))]
            logging.info(f"Muestra de datos para {description}: {sample}")
            
            # Verify format
            all_valid = True
            for item in sample:
                if not isinstance(item, tuple) or len(item) != 2:
                    logging.error(f"Error de formato: {item} no es una tupla de 2 elementos")
                    all_valid = False
                    break
            
            return all_valid
        except Exception as e:
            logging.error(f"Error verificando formato de datos para {description}: {e}")
            return False

    def highlight_selected_genre_row(self, row):
        """Resalta la fila del género seleccionado."""
        for i in range(self.table_genres.rowCount()):
            for j in range(self.table_genres.columnCount()):
                item = self.table_genres.item(i, j)
                if item:
                    if i == row:
                        item.setBackground(QBrush(QColor("#e0f2f1")))  # Color claro para la fila seleccionada
                    else:
                        item.setBackground(QBrush(QColor("#ffffff")))  # Color normal para las demás filas



    def on_genre_selected(self, item):
        """Maneja la selección de un género en la tabla."""
        if not self.conn:
            logging.error("No hay conexión a la base de datos")
            return
        
        # Obtener el género seleccionado (siempre está en la primera columna)
        row = item.row()
        
        # Acceso directo al widget de tabla
        table_genres = self.table_genres
        genre = table_genres.item(row, 0).text()
        
        # Si el género está truncado, obtenemos el texto completo del tooltip
        if table_genres.item(row, 0).toolTip():
            genre = table_genres.item(row, 0).toolTip()
        
        logging.info(f"Género seleccionado: {genre}")
        
        # Actualizar título usando acceso directo
        try:
            self.label_selected_genre_title.setText(f"Género: {genre}")
        except AttributeError:
            # Fallback si el acceso directo falla
            genre_title_label = self.findChild(QLabel, "label_selected_genre_title")
            if genre_title_label:
                genre_title_label.setText(f"Género: {genre}")
        
        # Cargar ambas visualizaciones
        self.load_artists_by_genre(genre)
        self.load_genre_by_decade(genre)
        
        # Asegurar que el stacked widget está visible usando acceso directo
        try:
            self.stacked_genre_charts.setVisible(True)
            self.stacked_genre_charts.setCurrentIndex(0)  # Establecer página por defecto
        except AttributeError:
            # Fallback
            stacked_genre_charts = self.findChild(QStackedWidget, "stacked_genre_charts")
            if stacked_genre_charts:
                stacked_genre_charts.setVisible(True)
                stacked_genre_charts.setCurrentIndex(0)

    def load_artists_by_genre(self, genre):
        """Carga la gráfica de artistas para un género específico."""
        # Buscar el contenedor para la gráfica
        chart_container = self.findChild(QWidget, "chart_container_artists_by_genre")
        if not chart_container:
            logging.error("No se encontró el contenedor para la gráfica de artistas por género")
            return
        
        # Asegurar que tiene layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Limpiar el contenedor
        self.clear_layout(layout)
        
        # Consultar artistas por género
        cursor = self.conn.cursor()
        try:
            # Consulta para obtener los artistas que tienen canciones del género seleccionado
            cursor.execute("""
                SELECT 
                    artist, COUNT(*) as song_count
                FROM 
                    songs
                WHERE 
                    genre = ? AND
                    artist IS NOT NULL AND artist != ''
                GROUP BY 
                    artist
                ORDER BY 
                    song_count DESC
                LIMIT 15;
            """, (genre,))
            
            # Asegurarse de que solo obtenemos dos valores por fila
            results = [(row[0], row[1]) for row in cursor.fetchall()]
            
            if results:
                # Crear gráfico de barras con los artistas
                chart_view = ChartFactory.create_bar_chart(
                    results,
                    f"Top Artistas con Género: {genre}",
                    x_label="Artista",
                    y_label="Canciones"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info(f"Gráfico de artistas para género '{genre}' creado correctamente")
                else:
                    error_label = QLabel("No se pudo crear el gráfico de artistas")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
                    
            else:
                # No hay datos
                no_data = QLabel(f"No hay artistas con canciones del género '{genre}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al consultar artistas por género: {e}")
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)

    def load_genre_by_decade(self, genre):
        """Muestra la evolución del género a lo largo de las décadas."""
        # Buscar el contenedor para la gráfica
        chart_container = self.findChild(QWidget, "chart_container_genres_year")
        if not chart_container:
            logging.error("No se encontró el contenedor para la gráfica de géneros por década")
            return
        
        # Asegurar que tiene layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Limpiar el contenedor
        self.clear_layout(layout)
        
        # Consultar datos por década
        cursor = self.conn.cursor()
        try:
            # Consulta para obtener la distribución del género por década
            cursor.execute("""
                SELECT 
                    CASE
                        WHEN s.date IS NULL OR s.date = '' THEN 'Desconocido'
                        WHEN CAST(SUBSTR(s.date, 1, 4) AS INTEGER) <= 1950 THEN 'Pre-1950'
                        ELSE CAST(CAST(SUBSTR(s.date, 1, 4) AS INTEGER) / 10 * 10 AS TEXT) || 's'
                    END as decade,
                    COUNT(*) as song_count
                FROM 
                    songs s
                WHERE 
                    s.genre = ?
                GROUP BY 
                    decade
                ORDER BY 
                    decade != 'Desconocido', decade != 'Pre-1950', decade;
            """, (genre,))
            
            # Obtener resultados como una lista de tuplas de 2 elementos
            results = cursor.fetchall()
            decade_results = []
            
            for row in results:
                # Nos aseguramos de solo tomar dos elementos
                if isinstance(row, sqlite3.Row):
                    decade_results.append((row['decade'], row['song_count']))
                elif isinstance(row, tuple) and len(row) >= 2:
                    decade_results.append((row[0], row[1]))
                else:
                    logging.error(f"Formato de fila inesperado: {row}, tipo: {type(row)}")
            
            # Verificar formato de datos
            self.check_data_format(decade_results, "géneros por década")
            
            # Verificar si hay datos para mostrar el gráfico
            if decade_results and len(decade_results) > 1:  # Más de una década o categoría
                # Preparar datos para el gráfico
                # Si hay una categoría "Desconocido", moverla al final para mejor visualización
                chart_data = []
                unknown_data = None
                
                for decade, count in decade_results:
                    if decade == "Desconocido":
                        unknown_data = (decade, count)
                    else:
                        chart_data.append((decade, count))
                
                if unknown_data:
                    chart_data.append(unknown_data)
                
                # Verificar formato final
                if not self.check_data_format(chart_data, "gráfico final por década"):
                    error_label = QLabel("Error en formato de datos para gráfico por década")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
                    return
                
                # Crear gráfico de barras por década
                chart_view = ChartFactory.create_bar_chart(
                    chart_data,
                    f"Evolución del Género '{genre}' por Década",
                    x_label="Década",
                    y_label="Canciones"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info(f"Gráfico de evolución por década para género '{genre}' creado correctamente")
                else:
                    error_label = QLabel("No se pudo crear el gráfico de evolución por década")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
                    
            elif decade_results:  # Solo una década o categoría
                # Mostrar mensaje informativo
                info_label = QLabel(f"El género '{genre}' solo aparece en una década: {decade_results[0][0]}")
                info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                info_label.setStyleSheet("color: #333; font-size: 14px; margin: 20px;")
                layout.addWidget(info_label)
                
                # Crear un gráfico simple que muestre la única década
                chart_view = ChartFactory.create_bar_chart(
                    decade_results,
                    f"Distribución del Género '{genre}'",
                    x_label="Década",
                    y_label="Canciones"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    
            else:
                # No hay datos de fecha para este género
                no_data = QLabel(f"No hay información de fechas para el género '{genre}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error al consultar la evolución del género por década: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)


    def setup_genre_chart_navigation(self):
        """Configura los botones de navegación entre las vistas de género."""
        try:
            # Acceso directo a los widgets
            # Esto funcionará si uic.loadUi creó estos atributos
            stacked_genre_charts = self.stacked_genre_charts
            btn_artists_view = self.btn_artists_view
            btn_decades_view = self.btn_decades_view
            
            if not all([stacked_genre_charts, btn_artists_view, btn_decades_view]):
                logging.error("No se pudieron acceder a todos los widgets de navegación de géneros")
                return
            
            logging.info(f"stacked_genre_charts: tiene {stacked_genre_charts.count()} páginas")
            
            # Clear existing connections to avoid duplicates
            try:
                btn_artists_view.clicked.disconnect()
            except Exception:
                pass
            
            try:
                btn_decades_view.clicked.disconnect()
            except Exception:
                pass
            
            # Direct connections to specific pages
            btn_artists_view.clicked.connect(lambda: stacked_genre_charts.setCurrentIndex(0))
            btn_decades_view.clicked.connect(lambda: stacked_genre_charts.setCurrentIndex(1))
            
            logging.info("Botones de navegación conectados directamente")
        except Exception as e:
            logging.error(f"Error al configurar navegación: {e}")
            # Fallback al método anterior si hay algún problema
            self._setup_genre_chart_navigation_fallback()

    def _setup_genre_chart_navigation_fallback(self):
        """Método alternativo para configurar la navegación si el acceso directo falla."""
        stacked_genre_charts = self.findChild(QStackedWidget, "stacked_genre_charts")
        btn_artists_view = self.findChild(QPushButton, "btn_artists_view")
        btn_decades_view = self.findChild(QPushButton, "btn_decades_view")
        
        if not all([stacked_genre_charts, btn_artists_view, btn_decades_view]):
            logging.error("No se encontraron los widgets necesarios para la navegación")
            return
            
        # Conectar directamente
        btn_artists_view.clicked.connect(lambda: stacked_genre_charts.setCurrentIndex(0))
        btn_decades_view.clicked.connect(lambda: stacked_genre_charts.setCurrentIndex(1))
        logging.info("Botones conectados por método fallback")



    def debug_button_click(self, button_name):
        """Debug function to verify button clicks."""
        stacked_genre_charts = self.findChild(QStackedWidget, "stacked_genre_charts")
        logging.info(f"Botón {button_name} ha sido clickeado!")
        
        if stacked_genre_charts:
            current = stacked_genre_charts.currentIndex()
            count = stacked_genre_charts.count()
            logging.info(f"Estado actual del stacked widget: página {current} de {count}")
            
            # Force direct page change
            if button_name == "artists":
                new_index = 0
            else:
                new_index = 1
                
            if 0 <= new_index < count:
                logging.info(f"Cambiando a página {new_index}")
                stacked_genre_charts.setCurrentIndex(new_index)
                logging.info(f"Página actual después del cambio: {stacked_genre_charts.currentIndex()}")
            else:
                logging.error(f"Índice inválido: {new_index}, máximo: {count-1}")
        else:
            logging.error("No se encontró el stacked widget para cambiar páginas")


    def change_genre_chart_page(self, index):
        """Cambia la página del stacked widget de gráficos de género."""
        stacked_genre_charts = self.findChild(QStackedWidget, "stacked_genre_charts")
        if stacked_genre_charts:
            current_index = stacked_genre_charts.currentIndex()
            if index != current_index and 0 <= index < stacked_genre_charts.count():
                logging.info(f"Cambiando vista de género de página {current_index} a {index}")
                stacked_genre_charts.setCurrentIndex(index)
                return True
            else:
                logging.warning(f"Índice de página inválido: {index}, actual: {current_index}, máximo: {stacked_genre_charts.count()-1}")
        else:
            logging.error("No se encontró el stacked widget de gráficos de género")
        return False


    def setup_genre_combo(self):
        """Configura el combo de selección de géneros."""
        combo_genres = self.findChild(QComboBox, "combo_genre_selection")
        if not combo_genres:
            return
            
        # Limpiar combo
        combo_genres.clear()
        
        # Consultar todos los géneros
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT genre
            FROM songs
            WHERE genre IS NOT NULL AND genre != ''
            ORDER BY genre;
        """)
        
        genres = [row[0] for row in cursor.fetchall()]
        
        # Añadir al combo
        for genre in genres:
            combo_genres.addItem(genre)
            
        # Conectar evento
        combo_genres.currentIndexChanged.connect(lambda: self.on_genre_combo_changed())


    def show_genre_details(self, genre):
        """Muestra estadísticas detalladas del género seleccionado."""
        details_widget = self.findChild(QWidget, "genre_details_widget")
        if not details_widget:
            return
            
        # Limpiar widgets previos
        self.clear_layout(details_widget.layout())
        
        # Consultar información adicional
        cursor = self.conn.cursor()
        
        # Número total de canciones del género
        cursor.execute("SELECT COUNT(*) FROM songs WHERE genre = ?", (genre,))
        total_songs = cursor.fetchone()[0]
        
        # Número de artistas distintos
        cursor.execute("SELECT COUNT(DISTINCT artist) FROM songs WHERE genre = ?", (genre,))
        total_artists = cursor.fetchone()[0]
        
        # Duración total
        cursor.execute("SELECT SUM(duration) FROM songs WHERE genre = ?", (genre,))
        total_duration = cursor.fetchone()[0] or 0
        hours = int(total_duration / 3600)
        minutes = int((total_duration % 3600) / 60)
        
        # Mostrar detalles
        layout = QVBoxLayout()
        
        info = QLabel(f"""
            <h3>Detalles del género: {genre}</h3>
            <p><b>Total de canciones:</b> {total_songs}</p>
            <p><b>Artistas distintos:</b> {total_artists}</p>
            <p><b>Duración total:</b> {hours}h {minutes}m</p>
        """)
        info.setTextFormat(Qt.TextFormat.RichText)
        
        layout.addWidget(info)
        details_widget.setLayout(layout)


# ESCUCHAS

                
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
        query = f"SELECT COUNT(*) FROM scrobbles_{self.lastfm_username};"
        cursor.execute(query)
        scrobble_count = cursor.fetchone()[0]
        
        # Verificar si hay datos de listens (ListenBrainz)
        query = f"SELECT COUNT(*) FROM listens_{self.musicbrainz_username};"
        cursor.execute(query)
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
            query = f"""
                SELECT artist_name, COUNT(*) as listen_count
                FROM scrobbles_{self.lastfm_username}
                GROUP BY artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """
            cursor.execute(query)
        else:  # listenbrainz
            query = f"""
                SELECT artist_name, COUNT(*) as listen_count
                FROM listens_{self.musicbrainz_username}
                GROUP BY artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """
            cursor.execute(query)
        
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
            query = f"""
                SELECT album_name, artist_name, COUNT(*) as listen_count
                FROM scrobbles_{self.lastfm_username}
                WHERE album_name IS NOT NULL AND album_name != ''
                GROUP BY album_name, artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """
            cursor.execute(query)
        else:  # listenbrainz
            query = f"""
                SELECT album_name, artist_name, COUNT(*) as listen_count
                FROM listens_{self.musicbrainz_username}
                WHERE album_name IS NOT NULL AND album_name != ''
                GROUP BY album_name, artist_name
                ORDER BY listen_count DESC
                LIMIT 50;
            """
            cursor.execute(query)
        
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
            query  = """
                SELECT s.genre, COUNT(sc.id) as listen_count
                FROM scrobbles_{self.lastfm_username} sc
                JOIN songs s ON sc.track_name = s.title AND sc.artist_name = s.artist
                WHERE s.genre IS NOT NULL AND s.genre != ''
                GROUP BY s.genre
                ORDER BY listen_count DESC;
            """
            cursor.execute(query)
        else:  # listenbrainz
            query = f"""
                SELECT s.genre, COUNT(l.id) as listen_count
                FROM listens_{self.musicbrainz_username} l
                JOIN songs s ON l.track_name = s.title AND l.artist_name = s.artist
                WHERE s.genre IS NOT NULL AND s.genre != ''
                GROUP BY s.genre
                ORDER BY listen_count DESC;
            """
            cursor.execute(query)
        
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
            query = f"""
                SELECT a.label, COUNT(sc.id) as listen_count
                FROM scrobbles_{self.lastfm_username} sc
                JOIN songs s ON sc.track_name = s.title AND sc.artist_name = s.artist
                JOIN albums a ON s.album = a.name
                WHERE a.label IS NOT NULL AND a.label != ''
                GROUP BY a.label
                ORDER BY listen_count DESC;
            """
            cursor.execute(query)
        else:  # listenbrainz
            query = f"""
                SELECT a.label, COUNT(l.id) as listen_count
                FROM listens_{self.musicbrainz_username} l
                JOIN songs s ON l.track_name = s.title AND l.artist_name = s.artist
                JOIN albums a ON s.album = a.name
                WHERE a.label IS NOT NULL AND a.label != ''
                GROUP BY a.label
                ORDER BY listen_count DESC;
            """
            cursor.execute(query)
        
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
            table = f"scrobbles_{self.lastfm_username}"
        else:
            date_field = "listen_date"
            table = f"listens_{self.musicbrainz_username}"
        
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
        
        # Primero, asegurarnos de que tenemos referencias a todos los widgets necesarios
        # Esto puede ayudar a depurar problemas de widgets inexistentes o inválidos
        self.chart_sello_stacked = self.findChild(QStackedWidget, "chart_sello_stacked")
        self.chart_container_labels = self.findChild(QWidget, "chart_container_labels")
        self.chart_sello_artistas = self.findChild(QWidget, "chart_sello_artistas")
        
        if not self.chart_sello_stacked:
            logging.error("No se encontró el widget chart_sello_stacked")
        if not self.chart_container_labels:
            logging.error("No se encontró el widget chart_container_labels")
        if not self.chart_sello_artistas:
            logging.error("No se encontró el widget chart_sello_artistas")
        
        # Cargar la tabla de sellos principal
        self.load_label_table()
        
        # Cargar las tablas en las otras páginas
        self.load_label_tables()
        
        # Cargar gráfico principal de sellos
        self.load_label_chart()
        
        # Cargar combo de décadas y preparar datos
        self.load_decade_data()
        
        # Asegurar que las conexiones estén configuradas
        self.setup_label_connections()
        
        # Configurar la página de información detallada del sello
        self.setup_label_info_page()
        
        # Asegurar que estamos en la primera página y que el gráfico de porcentajes es visible
        self.stackedWidget.setCurrentIndex(0)  # Primera página del stackedWidget principal
        
        if self.chart_sello_stacked:
            self.chart_sello_stacked.setCurrentIndex(0)  # Índice para chart_sellos_porcentaje
            logging.info(f"Estableciendo chart_sello_stacked a índice 0")
        
        logging.info("Finalizada carga de estadísticas de sellos")



    def load_label_table(self):
        """Carga la tabla de sellos discográficos."""
        logging.info("Iniciando carga de tabla de sellos")
        
        # Verificar que la tabla existe
        if not hasattr(self, 'table_labels'):
            logging.error("No se encontró el widget table_labels")
            return
        
        # Información sobre el estado actual de la tabla
        logging.info(f"Estado inicial de table_labels: filas={self.table_labels.rowCount()}, "
                    f"columnas={self.table_labels.columnCount()}, "
                    f"visible={self.table_labels.isVisible()}")
        
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
        
        if len(label_results) == 0:
            logging.warning("No se encontraron sellos en la base de datos")
            return
        
        # Llenar la tabla
        self.table_labels.setColumnCount(4)  # Asegurar que tenemos 4 columnas
        self.table_labels.setHorizontalHeaderLabels(["Sello", "Álbumes", "Artistas", "Canciones"])
        
        # Configurar la tabla para una mejor visualización
        self.table_labels.setAlternatingRowColors(True)
        self.table_labels.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_labels.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Mostrar los primeros 5 resultados para debug
        sample_data = label_results[:5]
        logging.info(f"Muestra de datos: {sample_data}")
        
        self.table_labels.setRowCount(len(label_results))
        for i, (label, count) in enumerate(label_results):
            # Verificar el formato de los valores
            logging.debug(f"Fila {i}: Sello={label}, Álbumes={count}")
            
            self.table_labels.setItem(i, 0, QTableWidgetItem(label))
            self.table_labels.setItem(i, 1, QTableWidgetItem(str(count)))
            
            # Obtener número de artistas para este sello
            cursor.execute("""
                SELECT COUNT(DISTINCT artist_id) 
                FROM albums 
                WHERE label = ?
            """, (label,))
            artist_count = cursor.fetchone()[0] or 0
            self.table_labels.setItem(i, 2, QTableWidgetItem(str(artist_count)))
            
            # Obtener número de canciones para este sello
            cursor.execute("""
                SELECT COUNT(*) 
                FROM songs s
                JOIN albums a ON s.album = a.name
                WHERE a.label = ?
            """, (label,))
            song_count = cursor.fetchone()[0] or 0
            self.table_labels.setItem(i, 3, QTableWidgetItem(str(song_count)))
        
        self.table_labels.resizeColumnsToContents()
        
        # Estado final de la tabla
        logging.info(f"Estado final de table_labels: filas={self.table_labels.rowCount()}, "
                    f"columnas={self.table_labels.columnCount()}")
        
        # Guardar los resultados para usarlos en los gráficos
        self.label_results = label_results
        logging.info("Finalizada carga de tabla de sellos")

    def load_label_chart(self):
        """Carga el gráfico principal de sellos usando atributos directos."""
        logging.info("Iniciando carga de gráfico de sellos")
        
        # Verificar que el contenedor existe como atributo directo
        if hasattr(self, 'chart_container_labels'):
            # Información sobre el estado actual del contenedor
            logging.info(f"Estado de chart_container_labels: "
                        f"visible={self.chart_container_labels.isVisible()}, "
                        f"tiene layout={self.chart_container_labels.layout() is not None}")
            
            # Asegurar que tiene layout
            layout = self.ensure_widget_has_layout(self.chart_container_labels)
            
            # Limpiar el contenedor
            self.clear_layout(layout)
            
            # Obtener datos para el gráfico (si no los tenemos ya)
            if not hasattr(self, 'label_results') or not self.label_results:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT label, COUNT(*) as album_count
                    FROM albums
                    WHERE label IS NOT NULL AND label != ''
                    GROUP BY label
                    ORDER BY album_count DESC
                    LIMIT 50;
                """)
                
                self.label_results = cursor.fetchall()
                logging.info(f"Datos para gráfico: {len(self.label_results)} sellos")
            
            # Comprobar si tenemos datos para mostrar
            if not self.label_results:
                logging.warning("No hay datos de sellos para mostrar en el gráfico")
                no_data = QLabel("No hay datos de sellos disponibles")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(no_data)
                return
            
            # Crear gráfico
            logging.info("Creando gráfico de pie para sellos")
            chart_data = self.label_results[:15] if len(self.label_results) > 15 else self.label_results
            
            chart_view = ChartFactory.create_pie_chart(
                chart_data,
                "Distribución de Álbumes por Sello"
            )
            
            if chart_view:
                # Añadir el gráfico al layout
                layout.addWidget(chart_view)
                logging.info("Gráfico de sellos añadido al layout correctamente")
            else:
                error_label = QLabel("No se pudo crear el gráfico")
                error_label.setStyleSheet("color: red;")
                layout.addWidget(error_label)
                logging.error("Falló la creación del gráfico de sellos")
        else:
            logging.error("No existe el atributo chart_container_labels")
        
        logging.info("Finalizada carga de gráfico de sellos")


    def setup_label_info_page(self):
        """Configura la página de información detallada de sellos."""
        # Configurar la tabla para que muestre todos los sellos
        if hasattr(self, 'labels_info_table'):
            # Configurar columnas
            self.labels_info_table.setColumnCount(3)
            self.labels_info_table.setHorizontalHeaderLabels(["Sello", "País", "Fundación"])
            
            # Cargar datos de todos los sellos
            self.load_all_labels_info()
        
        # Establecer conexiones para la página de información
        self.sellos_info_button = self.findChild(QPushButton, "sellos_info_button")
        if self.sellos_info_button:
            try:
                self.sellos_info_button.clicked.disconnect()
            except:
                pass
            self.sellos_info_button.clicked.connect(self.on_show_label_info)

    def load_all_labels_info(self):
        """Carga información de todos los sellos en la tabla de información."""
        if not self.conn or not hasattr(self, 'labels_info_table'):
            return
            
        cursor = self.conn.cursor()
        try:
            # Obtener todos los sellos con información básica
            cursor.execute("""
                SELECT name, country, founded_year
                FROM labels
                WHERE name IS NOT NULL AND name != ''
                ORDER BY name
            """)
            
            results = cursor.fetchall()
            
            # Configurar la tabla
            self.labels_info_table.setRowCount(len(results))
            
            # Llenar la tabla
            for i, (name, country, founded_year) in enumerate(results):
                self.labels_info_table.setItem(i, 0, QTableWidgetItem(name or ""))
                self.labels_info_table.setItem(i, 1, QTableWidgetItem(country or ""))
                self.labels_info_table.setItem(i, 2, QTableWidgetItem(str(founded_year) if founded_year else ""))
            
            # Ajustar ancho de columnas
            self.labels_info_table.resizeColumnsToContents()
            
            # Conectar evento de clic
            try:
                self.labels_info_table.itemClicked.disconnect()
            except:
                pass
            self.labels_info_table.itemClicked.connect(self.on_label_info_selected)
            
            logging.info(f"Tabla de información de sellos cargada con {len(results)} filas")
        except Exception as e:
            logging.error(f"Error al cargar información de sellos: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def on_label_info_selected(self, item):
        """Maneja la selección de un sello en la tabla de información."""
        # Obtener el sello seleccionado (primera columna)
        row = item.row()
        label_name = self.labels_info_table.item(row, 0).text()
        
        # Almacenar como sello seleccionado
        self.selected_label = label_name
        
        # Cargar información detallada en el panel de gráficos
        self.load_label_detailed_info(label_name)

  

    def on_show_label_info(self):
        """Maneja el clic en el botón 'Información del sello'."""
        # Verificar si tenemos un sello seleccionado
        if not hasattr(self, 'selected_label'):
            QMessageBox.warning(self, "Selección requerida", 
                            "Por favor, selecciona primero un sello de la tabla.")
            return
        
        # Cambiar a la página de información del sello
        self.stackedWidget.setCurrentWidget(self.labels_info)
        
        # Cargar información detallada para el sello seleccionado
        self.load_label_detailed_info(self.selected_label)


    def load_label_detailed_info(self, label_name):
        """Carga información detallada para un sello específico."""
        if not self.conn:
            logging.error("No hay conexión a la base de datos")
            return
        
        cursor = self.conn.cursor()
        
        # Obtener información básica del sello
        cursor.execute("""
            SELECT id, name, mbid, founded_year, country, description, 
                official_website, wikipedia_url, mb_type, mb_code
            FROM labels
            WHERE name = ?
        """, (label_name,))
        
        label_info = cursor.fetchone()
        
        if not label_info:
            error_label = QLabel(f"No se encontró información para el sello: {label_name}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: red;")
            
            # Limpiar ambos contenedores
            self.clear_layout(self.labels_info_chart.layout())
            self.labels_info_chart.layout().addWidget(error_label)
            
            # Limpiar la tabla
            if hasattr(self, 'labels_info_table'):
                self.labels_info_table.setRowCount(0)
            
            return
        
        # Configurar la tabla de información
        if hasattr(self, 'labels_info_table'):
            # Configurar columnas si no las tiene
            if self.labels_info_table.columnCount() == 0:
                self.labels_info_table.setColumnCount(2)
                self.labels_info_table.setHorizontalHeaderLabels(["Propiedad", "Valor"])
            
            # Limpiar tabla
            self.labels_info_table.setRowCount(0)
            
            # Datos básicos para mostrar en la tabla
            table_data = [
                ("Nombre", label_info['name']),
                ("País", label_info['country'] if label_info['country'] else "Desconocido"),
                ("Año fundación", str(label_info['founded_year']) if label_info['founded_year'] else "Desconocido"),
                ("Tipo", label_info['mb_type'] if label_info['mb_type'] else ""),
                ("Código", label_info['mb_code'] if label_info['mb_code'] else ""),
                ("MusicBrainz ID", label_info['mbid'] if label_info['mbid'] else ""),
                ("Web oficial", label_info['official_website'] if label_info['official_website'] else ""),
                ("Wikipedia", label_info['wikipedia_url'] if label_info['wikipedia_url'] else "")
            ]
            
            # Llenar la tabla
            self.labels_info_table.setRowCount(len(table_data))
            for i, (prop, value) in enumerate(table_data):
                self.labels_info_table.setItem(i, 0, QTableWidgetItem(prop))
                self.labels_info_table.setItem(i, 1, QTableWidgetItem(value))
            
            self.labels_info_table.resizeColumnsToContents()
        
        # Widget para mostrar la información markdown
        markdown_widget = QTextEdit()
        markdown_widget.setReadOnly(True)
        markdown_widget.setStyleSheet("""
            QTextEdit {
                background-color: #1a1b26;
                color: #a9b1d6;
                border: none;
                padding: 10px;
                font-family: 'Noto Sans', sans-serif;
            }
        """)
        
        # Obtener información básica del sello
        cursor.execute("""
            SELECT id, name, mbid, founded_year, country, description, 
                official_website, wikipedia_url, mb_type, mb_code
            FROM labels
            WHERE name = ?
        """, (label_name,))
        
        label_info = cursor.fetchone()
        
        if not label_info:
            markdown_widget.setText(f"# No se encontró información para el sello: {label_name}")
            self.labels_info_chart.layout().addWidget(markdown_widget)
            return
        
        # Construir el contenido markdown
        markdown_content = f"# Información del Sello: {label_name}\n\n"
        
        # Información básica
        markdown_content += "## Datos básicos\n\n"
        
        if label_info['founded_year']:
            markdown_content += f"**Año de fundación:** {label_info['founded_year']}\n\n"
        
        if label_info['country']:
            markdown_content += f"**País:** {label_info['country']}\n\n"
        
        if label_info['description']:
            markdown_content += f"**Descripción:** {label_info['description']}\n\n"
        
        if label_info['mb_type']:
            markdown_content += f"**Tipo:** {label_info['mb_type']}\n\n"
        
        # Enlaces
        markdown_content += "## Enlaces\n\n"
        
        if label_info['official_website']:
            markdown_content += f"**Sitio oficial:** {label_info['official_website']}\n\n"
        
        if label_info['wikipedia_url']:
            markdown_content += f"**Wikipedia:** {label_info['wikipedia_url']}\n\n"
        
        if label_info['mbid']:
            markdown_content += f"**MusicBrainz ID:** {label_info['mbid']}\n\n"
        
        # Obtener relaciones con otros sellos
        label_id = label_info['id']
        cursor.execute("""
            SELECT lr.relationship_type, l.name, lr.begin_date, lr.end_date
            FROM label_relationships lr
            JOIN labels l ON lr.target_label_id = l.id
            WHERE lr.source_label_id = ?
            UNION
            SELECT lr.relationship_type, l.name, lr.begin_date, lr.end_date
            FROM label_relationships lr
            JOIN labels l ON lr.source_label_id = l.id
            WHERE lr.target_label_id = ?
        """, (label_id, label_id))
        
        label_relations = cursor.fetchall()
        
        if label_relations:
            markdown_content += "## Relaciones con otros sellos\n\n"
            for relation in label_relations:
                rel_type, rel_label, begin_date, end_date = relation
                date_info = ""
                if begin_date and end_date:
                    date_info = f" ({begin_date} - {end_date})"
                elif begin_date:
                    date_info = f" (desde {begin_date})"
                elif end_date:
                    date_info = f" (hasta {end_date})"
                
                markdown_content += f"**{rel_type}** con {rel_label}{date_info}\n\n"
        
        # Obtener álbumes publicados por este sello
        cursor.execute("""
            SELECT a.name as album_name, ar.name as artist_name, a.year, 
                lrr.catalog_number, lrr.relationship_type
            FROM label_release_relationships lrr
            JOIN albums a ON lrr.album_id = a.id
            JOIN artists ar ON a.artist_id = ar.id
            WHERE lrr.label_id = ?
            ORDER BY a.year DESC, a.name
            LIMIT 30
        """, (label_id,))
        
        albums = cursor.fetchall()
        
        if albums:
            markdown_content += "## Álbumes publicados\n\n"
            markdown_content += "| Álbum | Artista | Año | № Catálogo | Tipo |\n"
            markdown_content += "|-------|---------|-----|------------|------|\n"
            
            for album in albums:
                album_name, artist_name, year, catalog, rel_type = album
                year_str = year if year else ""
                catalog_str = catalog if catalog else ""
                rel_type_str = rel_type if rel_type else "publicado"
                
                markdown_content += f"| {album_name} | {artist_name} | {year_str} | {catalog_str} | {rel_type_str} |\n"
        
        # Obtener artistas asociados a este sello
        cursor.execute("""
            SELECT DISTINCT ar.name, COUNT(DISTINCT a.id) as album_count
            FROM artists ar
            JOIN albums a ON ar.id = a.artist_id
            WHERE a.label = ?
            GROUP BY ar.name
            ORDER BY album_count DESC
            LIMIT 20
        """, (label_name,))
        
        artists = cursor.fetchall()
        
        if artists:
            markdown_content += "\n## Artistas del sello\n\n"
            markdown_content += "| Artista | Álbumes |\n"
            markdown_content += "|---------|--------|\n"
            
            for artist in artists:
                artist_name, album_count = artist
                markdown_content += f"| {artist_name} | {album_count} |\n"
        
        # Mostrar la información en el widget
        markdown_widget.setMarkdown(markdown_content)
        
        # Limpiar el layout y añadir el widget
        self.clear_layout(self.labels_info_chart.layout())
        self.labels_info_chart.layout().addWidget(markdown_widget)






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
        # Use the callback handler to redirect to the time submodule
        self.callback_handler.redirect_to_submodule('load_time_stats', 'time')



# PAISES


    def on_country_selected(self, item):
        """Handles selection of a country in the table_countries widget."""
        if not self.conn:
            logging.error("No database connection available")
            return
        
        # Get the selected country (always in the first column)
        row = item.row()
        country = self.table_countries.item(row, 0).text()
        logging.info(f"Selected country: {country}")
        
        # Store the selected country for potential future use
        self.selected_country = country
        
        # Change to the artists page in the stacked widget
        self.stackedWidget_countries.setCurrentIndex(1)
        
        # Load the chart showing artists from this country
        self.load_artists_by_country(country)

    def load_artists_by_country(self, country):
        """Loads and displays a pie chart of artists from a specific country."""
        # Find the chart container
        chart_container = self.chart_countries_artists
        
        # Ensure the container has a layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Clear the container
        self.clear_layout(layout)
        
        # Query for artists from this country
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT name, COUNT(*) as album_count
                FROM artists
                WHERE origin = ?
                GROUP BY name
                ORDER BY album_count DESC, name
                LIMIT 15;
            """, (country,))
            
            results = cursor.fetchall()
            
            if results:
                # Create a pie chart with the artists
                chart_view = ChartFactory.create_pie_chart(
                    results,
                    f"Artistas de {country}",
                    limit=15  # Limit to top 15 artists
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info(f"Artist chart for country '{country}' created successfully")
                else:
                    error_label = QLabel("No se pudo crear el gráfico de artistas")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
            else:
                # No data
                no_data = QLabel(f"No hay artistas registrados para el país '{country}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error querying artists by country: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)


    def load_country_stats(self):
        """Loads country statistics."""
        if not self.conn:
            return
        
        # Get widget references directly (without findChild)
        table_countries = self.table_countries
        chart_container_countries = self.chart_container_countries
        
        if not table_countries or not chart_container_countries:
            logging.error("Required widgets not found")
            return
                
        # Clear table
        table_countries.setRowCount(0)
        
        # Query data
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT origin, COUNT(*) as artist_count
            FROM artists
            WHERE origin IS NOT NULL AND origin != ''
            GROUP BY origin
            ORDER BY artist_count DESC;
        """)
        
        results = cursor.fetchall()
        
        # Fill the table
        table_countries.setRowCount(len(results))
        for i, (country, count) in enumerate(results):
            table_countries.setItem(i, 0, QTableWidgetItem(country))
            table_countries.setItem(i, 1, QTableWidgetItem(str(count)))
        
        table_countries.resizeColumnsToContents()
        
        # Create chart for countries
        layout = self.ensure_widget_has_layout(chart_container_countries)
        self.clear_layout(layout)
        
        chart_view = ChartFactory.create_pie_chart(
            results,
            "Distribución por País de Origen"
        )
        layout.addWidget(chart_view)
        
        # Connect the table selection event
        try:
            table_countries.itemClicked.disconnect()
        except:
            pass
        table_countries.itemClicked.connect(self.on_country_selected)
        
        # Make sure we start in the first page of the stacked widget
        self.stackedWidget_countries.setCurrentIndex(0)


    def setup_country_navigation(self):
        """Sets up navigation buttons for the country views."""
        try:
            # Connect existing buttons
            if hasattr(self, 'btn_countries_overview'):
                self.btn_countries_overview.clicked.connect(
                    lambda: self.stackedWidget_countries.setCurrentIndex(0)
                )
            
            # Connect all country buttons
            button_mappings = {
                'action_countries_artists': self.on_countries_artists_clicked,
                'action_countries_album': self.on_countries_album_clicked,
                'action_countries_feeds': self.on_countries_feeds_clicked,
                'action_countries_genre': self.on_countries_genre_clicked,
                'action_countries_time': self.on_countries_time_clicked,
                'action_countries_listens': self.on_countries_listens_clicked,
                'action_countries_info': self.on_countries_info_clicked
            }
            
            for button_name, handler in button_mappings.items():
                button = getattr(self, button_name, None)
                if button:
                    try:
                        button.clicked.disconnect()
                    except:
                        pass
                    button.clicked.connect(handler)
                    logging.info(f"Botón {button_name} conectado correctamente")
                else:
                    logging.warning(f"No se encontró el botón {button_name}")
                
        except Exception as e:
            logging.error(f"Error setting up country navigation: {e}")

    def show_country_artists_selection(self):
        """Shows a dialog to select a country if none is selected yet."""
        if not hasattr(self, 'selected_country'):
            # If no country is selected, show a message
            QMessageBox.information(
                self,
                "Selección requerida",
                "Por favor, selecciona primero un país de la tabla."
            )
            return
        
        # If a country is already selected, go to the artists view
        self.stackedWidget_countries.setCurrentIndex(1)
        # Make sure the chart is up to date
        self.load_artists_by_country(self.selected_country)


    def on_countries_artists_clicked(self):
        """Handles the countries_artists_button click to show artists from selected country."""
        # First, check if a country is selected
        if not hasattr(self, 'selected_country'):
            QMessageBox.information(
                self,
                "Selección requerida",
                "Por favor, selecciona primero un país de la tabla."
            )
            return
        
        # Change to the appropriate page in the stacked widget
        self.stackedWidget_countries.setCurrentIndex(1)
        
        # Get reference to the chart container
        chart_container = self.chart_countries_artists
        
        # Ensure the chart container has a layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Clear any existing content
        self.clear_layout(layout)
        
        # Query for artists from this country
        cursor = self.conn.cursor()
        try:
            # Query artists from the selected country
            cursor.execute("""
                SELECT name, COUNT(DISTINCT a.id) as album_count
                FROM artists ar
                JOIN albums a ON a.artist_id = ar.id
                WHERE ar.origin = ?
                GROUP BY ar.name
                ORDER BY album_count DESC, ar.name
                LIMIT 15;
            """, (self.selected_country,))
            
            results = cursor.fetchall()
            
            if results:
                # Create a bar chart with the artists
                chart_view = ChartFactory.create_bar_chart(
                    results,
                    f"Artistas de {self.selected_country}",
                    x_label="Artista",
                    y_label="Álbumes",
                    limit=15  # Limit to top 15 artists
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info(f"Artist chart for country '{self.selected_country}' created successfully")
                else:
                    error_label = QLabel("No se pudo crear el gráfico de artistas")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
            else:
                # No data
                no_data = QLabel(f"No hay artistas registrados para el país '{self.selected_country}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error querying artists by country: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)


    def on_countries_album_clicked(self):
        """Handles the countries_album_button click to show albums from selected country."""
        # First, check if a country is selected
        if not hasattr(self, 'selected_country'):
            QMessageBox.information(
                self,
                "Selección requerida",
                "Por favor, selecciona primero un país de la tabla."
            )
            return
        
        # Change to the appropriate page in the stacked widget
        self.stackedWidget_countries.setCurrentIndex(1)
        
        # Get reference to the chart container
        chart_container = self.chart_countries_artists  # Reuse the same container
        
        # Ensure the chart container has a layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Clear any existing content
        self.clear_layout(layout)
        
        # Query for albums from artists of this country
        cursor = self.conn.cursor()
        try:
            # Query albums from artists of the selected country
            cursor.execute("""
                SELECT a.name, COUNT(s.id) as song_count
                FROM albums a
                JOIN artists ar ON a.artist_id = ar.id
                LEFT JOIN songs s ON s.album = a.name AND s.artist = ar.name
                WHERE ar.origin = ?
                GROUP BY a.name
                ORDER BY song_count DESC
                LIMIT 15;
            """, (self.selected_country,))
            
            results = cursor.fetchall()
            
            if results:
                # Create a bar chart with the albums
                chart_view = ChartFactory.create_bar_chart(
                    results,
                    f"Álbumes de Artistas de {self.selected_country}",
                    x_label="Álbum",
                    y_label="Canciones",
                    limit=15  # Limit to top 15 albums
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info(f"Album chart for country '{self.selected_country}' created successfully")
                else:
                    error_label = QLabel("No se pudo crear el gráfico de álbumes")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
            else:
                # No data
                no_data = QLabel(f"No hay álbumes registrados para artistas de '{self.selected_country}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error querying albums by country: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)


    def on_countries_feeds_clicked(self):
        """Handles the countries_feeds_button click to show feeds for artist and albums from the selected country."""
        # First, check if a country is selected
        if not hasattr(self, 'selected_country'):
            QMessageBox.information(
                self,
                "Selección requerida",
                "Por favor, selecciona primero un país de la tabla."
            )
            return
        
        # Change to the appropriate page in the stacked widget
        self.stackedWidget_countries.setCurrentIndex(1)
        
        # Get reference to the chart container
        chart_container = self.chart_countries_artists  # Reuse the same container
        
        # Ensure the chart container has a layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Clear any existing content
        self.clear_layout(layout)
        
        # Create splitter for two charts
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Container for artist feeds chart
        artist_feeds_container = QWidget()
        artist_feeds_layout = QVBoxLayout(artist_feeds_container)
        artist_feeds_title = QLabel(f"Feeds de Artistas de {self.selected_country}")
        artist_feeds_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        artist_feeds_layout.addWidget(artist_feeds_title)
        
        # Container for album feeds chart
        album_feeds_container = QWidget()
        album_feeds_layout = QVBoxLayout(album_feeds_container)
        album_feeds_title = QLabel(f"Feeds de Álbumes de Artistas de {self.selected_country}")
        album_feeds_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        album_feeds_layout.addWidget(album_feeds_title)
        
        # Query feeds for artists from this country
        cursor = self.conn.cursor()
        try:
            # Artist feeds
            cursor.execute("""
                SELECT f.feed_name, COUNT(*) as feed_count
                FROM feeds f
                JOIN artists ar ON f.entity_id = ar.id AND f.entity_type = 'artist'
                WHERE ar.origin = ?
                GROUP BY f.feed_name
                ORDER BY feed_count DESC;
            """, (self.selected_country,))
            
            artist_feeds_results = cursor.fetchall()
            
            # Album feeds
            cursor.execute("""
                SELECT f.feed_name, COUNT(*) as feed_count
                FROM feeds f
                JOIN albums al ON f.entity_id = al.id AND f.entity_type = 'album'
                JOIN artists ar ON al.artist_id = ar.id
                WHERE ar.origin = ?
                GROUP BY f.feed_name
                ORDER BY feed_count DESC;
            """, (self.selected_country,))
            
            album_feeds_results = cursor.fetchall()
            
            # Create charts if we have data
            if artist_feeds_results:
                artist_chart = ChartFactory.create_pie_chart(
                    artist_feeds_results,
                    f"Feeds de Artistas de {self.selected_country}"
                )
                if artist_chart:
                    artist_feeds_layout.addWidget(artist_chart)
            else:
                no_data = QLabel(f"No hay feeds para artistas de '{self.selected_country}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                artist_feeds_layout.addWidget(no_data)
                
            if album_feeds_results:
                album_chart = ChartFactory.create_pie_chart(
                    album_feeds_results,
                    f"Feeds de Álbumes de Artistas de {self.selected_country}"
                )
                if album_chart:
                    album_feeds_layout.addWidget(album_chart)
            else:
                no_data = QLabel(f"No hay feeds para álbumes de artistas de '{self.selected_country}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                album_feeds_layout.addWidget(no_data)
            
            # Add containers to splitter and main layout
            splitter.addWidget(artist_feeds_container)
            splitter.addWidget(album_feeds_container)
            layout.addWidget(splitter)
                
        except Exception as e:
            logging.error(f"Error querying feeds by country: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)


    def get_artist_genres_safely(self, country):
        """Obtiene los géneros de artistas de forma segura sin depender de JSON válido"""
        cursor = self.conn.cursor()
        
        # Primero, obtén todos los artistas con sus tags
        cursor.execute("""
            SELECT id, name, tags 
            FROM artists 
            WHERE origin = ? AND tags IS NOT NULL AND tags != ''
        """, (country,))
        
        artists = cursor.fetchall()
        
        # Procesamos los tags manualmente
        genre_counts = {}
        for artist_id, artist_name, tags in artists:
            # Convertir tags a lista
            try:
                # Intenta varias estrategias de separación
                if ',' in tags:
                    # Formato separado por comas (más común)
                    genres = [g.strip() for g in tags.split(',')]
                elif ';' in tags:
                    # Algunos usan punto y coma
                    genres = [g.strip() for g in tags.split(';')]
                elif '|' in tags:
                    # Otros usan pipe
                    genres = [g.strip() for g in tags.split('|')]
                elif tags.startswith('[') and tags.endswith(']'):
                    # Intenta como JSON array
                    try:
                        import json
                        genres = json.loads(tags)
                    except:
                        # Si falla, trata como texto regular
                        genres = [tags[1:-1].strip()]
                else:
                    # Si no hay separadores, trátalo como un solo género
                    genres = [tags.strip()]
                
                # Contar cada género
                for genre in genres:
                    if genre:  # Ignorar vacíos
                        if genre in genre_counts:
                            genre_counts[genre] += 1
                        else:
                            genre_counts[genre] = 1
                            
            except Exception as e:
                logging.error(f"Error procesando tags para artista {artist_name}: {e}")
        
        # Convertir a formato para gráficos (lista de tuplas)
        result = [(genre, count) for genre, count in genre_counts.items()]
        result.sort(key=lambda x: x[1], reverse=True)
        
        return result



    def on_countries_genre_clicked(self):
        """Handles the countries_genre_button click to show genres for artists from the selected country."""
        # First, check if a country is selected
        if not hasattr(self, 'selected_country'):
            QMessageBox.information(
                self,
                "Selección requerida",
                "Por favor, selecciona primero un país de la tabla."
            )
            return
        
        # Change to the appropriate page in the stacked widget
        self.stackedWidget_countries.setCurrentIndex(1)
        
        # Get reference to the chart container
        chart_container = self.chart_countries_artists  # Reuse the same container
        
        # Ensure the chart container has a layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Clear any existing content
        self.clear_layout(layout)
        
        # Query for genres information - use a safer approach
        cursor = self.conn.cursor()
        try:
            # Get artist tags directly - avoid JSON parsing in SQL
            cursor.execute("""
                SELECT 
                    ar.tags
                FROM 
                    artists ar
                WHERE 
                    ar.origin = ?
                    AND ar.tags IS NOT NULL
                    AND ar.tags != ''
            """, (self.selected_country,))
            
            # Process tags in Python instead of SQL
            artist_tags_rows = cursor.fetchall()
            genre_counts = {}
            
            # Process each artist's tags
            for row in artist_tags_rows:
                tags = self.safely_parse_tags(row[0])
                for tag in tags:
                    genre_counts[tag] = genre_counts.get(tag, 0) + 1
            
            # Convert to format needed for chart
            artist_genres = [(genre, count) for genre, count in 
                            sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:15]]
            
            # Album genres - use a more reliable query
            cursor.execute("""
                SELECT 
                    a.genre, 
                    COUNT(*) as album_count
                FROM 
                    albums a
                JOIN 
                    artists ar ON a.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                    AND a.genre IS NOT NULL 
                    AND a.genre != ''
                GROUP BY 
                    a.genre
                ORDER BY 
                    album_count DESC
                LIMIT 15;
            """, (self.selected_country,))
            
            album_genres = cursor.fetchall()
            
            # Song genres - similar reliable approach
            cursor.execute("""
                SELECT 
                    s.genre, 
                    COUNT(*) as song_count
                FROM 
                    songs s
                JOIN 
                    albums a ON s.album = a.name
                JOIN 
                    artists ar ON a.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                    AND s.genre IS NOT NULL 
                    AND s.genre != ''
                GROUP BY 
                    s.genre
                ORDER BY 
                    song_count DESC
                LIMIT 15;
            """, (self.selected_country,))
            
            song_genres = cursor.fetchall()
            
            # Create splitter for three charts
            splitter = QSplitter(Qt.Orientation.Vertical)
            
            # Artist genres chart
            artist_container = QWidget()
            artist_layout = QVBoxLayout(artist_container)
            artist_title = QLabel(f"Géneros de Artistas de {self.selected_country}")
            artist_title.setStyleSheet("font-weight: bold; font-size: 14px;")
            artist_layout.addWidget(artist_title)
            
            # Album genres chart
            album_container = QWidget()
            album_layout = QVBoxLayout(album_container)
            album_title = QLabel(f"Géneros de Álbumes de {self.selected_country}")
            album_title.setStyleSheet("font-weight: bold; font-size: 14px;")
            album_layout.addWidget(album_title)
            
            # Song genres chart
            song_container = QWidget()
            song_layout = QVBoxLayout(song_container)
            song_title = QLabel(f"Géneros de Canciones de {self.selected_country}")
            song_title.setStyleSheet("font-weight: bold; font-size: 14px;")
            song_layout.addWidget(song_title)
            
            # Create the charts for each section
            if artist_genres:
                artist_chart = ChartFactory.create_pie_chart(
                    artist_genres,
                    f"Géneros de Artistas de {self.selected_country}"
                )
                if artist_chart:
                    artist_layout.addWidget(artist_chart)
            else:
                no_data = QLabel(f"No hay datos de géneros para artistas de '{self.selected_country}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                artist_layout.addWidget(no_data)
                
            if album_genres:
                album_chart = ChartFactory.create_pie_chart(
                    album_genres,
                    f"Géneros de Álbumes de Artistas de {self.selected_country}"
                )
                if album_chart:
                    album_layout.addWidget(album_chart)
            else:
                no_data = QLabel(f"No hay datos de géneros para álbumes de artistas de '{self.selected_country}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                album_layout.addWidget(no_data)
                
            if song_genres:
                song_chart = ChartFactory.create_pie_chart(
                    song_genres,
                    f"Géneros de Canciones de Artistas de {self.selected_country}"
                )
                if song_chart:
                    song_layout.addWidget(song_chart)
            else:
                no_data = QLabel(f"No hay datos de géneros para canciones de artistas de '{self.selected_country}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                song_layout.addWidget(no_data)
            
            # Add containers to splitter
            splitter.addWidget(artist_container)
            splitter.addWidget(album_container)
            splitter.addWidget(song_container)
            
            # Add splitter to main layout
            layout.addWidget(splitter)
                
        except Exception as e:
            logging.error(f"Error querying genres by country: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)


                    
    def on_countries_time_clicked(self):
        """Muestra distribución temporal de álbumes para el país seleccionado."""
        # Verificar si hay un país seleccionado
        if not hasattr(self, 'selected_country'):
            QMessageBox.information(
                self,
                "Selección requerida",
                "Por favor, selecciona primero un país de la tabla."
            )
            return
        
        # Cambiar a la página apropiada
        self.stackedWidget_countries.setCurrentIndex(1)
        
        # Obtener referencia al contenedor de gráficos
        chart_container = self.chart_countries_artists  # Reutilizamos el mismo contenedor
        
        # Asegurar que tiene layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Limpiar cualquier contenido existente
        self.clear_layout(layout)
        
        # Crear contenedor principal con layout vertical
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        
        # Crear título
        title_label = QLabel(f"Distribución temporal de álbumes de artistas de {self.selected_country}")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(title_label)
        
        # Consultar datos por año para este país
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    a.year, 
                    COUNT(*) as album_count
                FROM 
                    albums a
                JOIN 
                    artists ar ON a.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                    AND a.year IS NOT NULL 
                    AND a.year != ''
                GROUP BY 
                    a.year
                ORDER BY 
                    a.year;
            """, (self.selected_country,))
            
            year_results = cursor.fetchall()
            
            # Crear gráfico lineal con la distribución por año
            if year_results:
                # Contenedor para el gráfico lineal
                year_chart_container = QWidget()
                year_layout = QVBoxLayout(year_chart_container)
                
                # Crear gráfico lineal
                year_chart = ChartFactory.create_line_chart(
                    year_results,
                    f"Álbumes por año de artistas de {self.selected_country}",
                    x_label="Año",
                    y_label="Álbumes"
                )
                
                if year_chart:
                    year_layout.addWidget(year_chart)
                    main_layout.addWidget(year_chart_container)
                else:
                    error_label = QLabel("No se pudo crear el gráfico de distribución por año")
                    error_label.setStyleSheet("color: red;")
                    main_layout.addWidget(error_label)
            else:
                no_data = QLabel(f"No hay datos de años para álbumes de artistas de '{self.selected_country}'")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                main_layout.addWidget(no_data)
                
            # Contenedor para gráficos de década (estará inicialmente vacío)
            decade_graph_container = QWidget()
            decade_graph_layout = QVBoxLayout(decade_graph_container)
            decade_graph_layout.addWidget(QLabel("Selecciona una década para ver detalles"))
            main_layout.addWidget(decade_graph_container)
            
            # Crear contenedor para los botones de década
            decades_container = QWidget()
            decades_layout = QHBoxLayout(decades_container)
            
            # Agrupar datos por década
            decades = {}
            for year_str, count in year_results:
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
            
            # Crear botones para cada década
            for decade, count in sorted(decades.items()):
                decade_str = f"{decade}s ({count})"
                decade_btn = QPushButton(decade_str)
                decade_btn.clicked.connect(lambda checked, d=decade: self.show_decade_details(d, decade_graph_layout, self.selected_country))
                decades_layout.addWidget(decade_btn)
            
            # Añadir botones a la vista principal
            if decades:
                main_layout.addWidget(decades_container)
            else:
                no_decades = QLabel("No se pudieron determinar décadas para este país")
                no_decades.setStyleSheet("color: gray;")
                main_layout.addWidget(no_decades)
            
            # Añadir el contenedor principal al layout
            layout.addWidget(main_container)
            
        except Exception as e:
            logging.error(f"Error al consultar datos temporales para el país: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)

    def show_decade_details(self, decade, container_layout, country):
        """Muestra detalles de álbumes y artistas para una década específica."""
        # Limpiar el contenedor
        self.clear_layout(container_layout)
        
        # Añadir título
        title = QLabel(f"Detalles de la década {decade}s para {country}")
        title.setStyleSheet("font-weight: bold;")
        container_layout.addWidget(title)
        
        # Consultar datos para esta década y país
        cursor = self.conn.cursor()
        try:
            # Artistas con álbumes en esta década
            cursor.execute("""
                SELECT 
                    ar.name, 
                    COUNT(a.id) as album_count
                FROM 
                    artists ar
                JOIN 
                    albums a ON a.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                    AND a.year IS NOT NULL 
                    AND a.year != ''
                    AND CAST(a.year AS INTEGER) >= ?
                    AND CAST(a.year AS INTEGER) < ?
                GROUP BY 
                    ar.name
                ORDER BY 
                    album_count DESC
                LIMIT 15;
            """, (country, decade, decade + 10))
            
            artist_results = cursor.fetchall()
            
            # Álbumes en esta década
            cursor.execute("""
                SELECT 
                    a.name, 
                    ar.name,
                    COUNT(s.id) as song_count
                FROM 
                    albums a
                JOIN 
                    artists ar ON a.artist_id = ar.id
                LEFT JOIN 
                    songs s ON s.album = a.name AND s.artist = ar.name
                WHERE 
                    ar.origin = ?
                    AND a.year IS NOT NULL 
                    AND a.year != ''
                    AND CAST(a.year AS INTEGER) >= ?
                    AND CAST(a.year AS INTEGER) < ?
                GROUP BY 
                    a.name, ar.name
                ORDER BY 
                    song_count DESC
                LIMIT 15;
            """, (country, decade, decade + 10))
            
            album_results = cursor.fetchall()
            
            # Crear splitter horizontal para los dos gráficos
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Añadir gráfico de artistas
            artist_widget = QWidget()
            artist_layout = QVBoxLayout(artist_widget)
            artist_title = QLabel(f"Artistas con álbumes en los {decade}s")
            artist_title.setStyleSheet("font-weight: bold;")
            artist_layout.addWidget(artist_title)
            
            if artist_results:
                # Convertir datos para gráfico (artista, álbumes)
                artist_data = [(name, count) for name, count in artist_results]
                artist_chart = ChartFactory.create_bar_chart(
                    artist_data,
                    f"Artistas con álbumes en los {decade}s",
                    x_label="Artista",
                    y_label="Álbumes"
                )
                if artist_chart:
                    artist_layout.addWidget(artist_chart)
            else:
                no_data = QLabel(f"No hay artistas con álbumes en los {decade}s")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray;")
                artist_layout.addWidget(no_data)
            
            # Añadir gráfico de álbumes
            album_widget = QWidget()
            album_layout = QVBoxLayout(album_widget)
            album_title = QLabel(f"Álbumes en los {decade}s")
            album_title.setStyleSheet("font-weight: bold;")
            album_layout.addWidget(album_title)
            
            if album_results:
                # Convertir datos para gráfico (álbum - artista, canciones)
                album_data = [(f"{album} - {artist}", songs) for album, artist, songs in album_results]
                album_chart = ChartFactory.create_bar_chart(
                    album_data,
                    f"Álbumes en los {decade}s",
                    x_label="Álbum",
                    y_label="Canciones"
                )
                if album_chart:
                    album_layout.addWidget(album_chart)
            else:
                no_data = QLabel(f"No hay álbumes en los {decade}s")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray;")
                album_layout.addWidget(no_data)
            
            # Añadir widgets al splitter
            splitter.addWidget(artist_widget)
            splitter.addWidget(album_widget)
            
            # Añadir splitter al contenedor
            container_layout.addWidget(splitter)
            
        except Exception as e:
            logging.error(f"Error al mostrar detalles de década: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            container_layout.addWidget(error_label)



    def on_countries_listens_clicked(self):
        """Muestra estadísticas de escuchas por país."""
        # Cambiar a la página apropiada
        self.stackedWidget_countries.setCurrentIndex(1)
        
        # Obtener referencia al contenedor de gráficos
        chart_container = self.chart_countries_artists  # Reutilizamos el mismo contenedor
        
        # Asegurar que tiene layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Limpiar cualquier contenido existente
        self.clear_layout(layout)
        
        # Crear título
        title_label = QLabel("Distribución de escuchas por país")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(title_label)
        
        # Crear contenedores para los gráficos
        total_listens_container = QWidget()
        total_layout = QVBoxLayout(total_listens_container)
        
        artists_listens_container = QWidget()
        artists_layout = QVBoxLayout(artists_listens_container)
        
        # Consultar escuchas por país
        cursor = self.conn.cursor()
        try:
            # Primero verificamos si hay datos de scrobbles_{self.lastfm_username} o listens
            query = f"SELECT COUNT(*) FROM scrobbles_{self.lastfm_username};"
            cursor.execute(query)
            scrobble_count = cursor.fetchone()[0]
            
            query = f"SELECT COUNT(*) FROM listens_{self.musicbrainz_username};"
            cursor.execute(query)
            listen_count = cursor.fetchone()[0]
            
            if scrobble_count == 0 and listen_count == 0:
                no_data = QLabel("No hay datos de escuchas en la base de datos")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                return
            
            # Determinar qué tabla usar
            listen_table = "scrobbles_{self.lastfm_username}" if scrobble_count > 0 else "listens"
            
            # Consultar distribución por país
            cursor.execute(f"""
                SELECT 
                    ar.origin, 
                    COUNT(*) as listen_count
                FROM 
                    {listen_table} l
                JOIN 
                    artists ar ON l.artist_name = ar.name
                WHERE 
                    ar.origin IS NOT NULL 
                    AND ar.origin != ''
                GROUP BY 
                    ar.origin
                ORDER BY 
                    listen_count DESC;
            """)
            
            country_results = cursor.fetchall()
            
            if country_results:
                # Crear gráfico circular de escuchas por país
                country_chart = ChartFactory.create_pie_chart(
                    country_results,
                    "Escuchas por país de origen de los artistas"
                )
                if country_chart:
                    total_layout.addWidget(country_chart)
                
                # Añadir instrucciones para el usuario
                if hasattr(self, 'selected_country'):
                    # Si hay un país seleccionado, mostrar artistas para ese país
                    artists_title = QLabel(f"Artistas más escuchados de {self.selected_country}")
                    artists_title.setStyleSheet("font-weight: bold; font-size: 14px;")
                    artists_layout.addWidget(artists_title)
                    
                    # Consultar artistas más escuchados para el país seleccionado
                    cursor.execute(f"""
                        SELECT 
                            l.artist_name, 
                            COUNT(*) as listen_count
                        FROM 
                            {listen_table} l
                        JOIN 
                            artists ar ON l.artist_name = ar.name
                        WHERE 
                            ar.origin = ?
                        GROUP BY 
                            l.artist_name
                        ORDER BY 
                            listen_count DESC
                        LIMIT 15;
                    """, (self.selected_country,))
                    
                    artist_results = cursor.fetchall()
                    
                    if artist_results:
                        artist_chart = ChartFactory.create_bar_chart(
                            artist_results,
                            f"Artistas más escuchados de {self.selected_country}",
                            x_label="Artista",
                            y_label="Escuchas"
                        )
                        if artist_chart:
                            artists_layout.addWidget(artist_chart)
                    else:
                        no_artists = QLabel(f"No hay datos de escuchas para artistas de {self.selected_country}")
                        no_artists.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        no_artists.setStyleSheet("color: gray;")
                        artists_layout.addWidget(no_artists)
                else:
                    instructions = QLabel("Selecciona un país en la tabla para ver los artistas más escuchados")
                    instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    instructions.setStyleSheet("color: gray; font-style: italic;")
                    artists_layout.addWidget(instructions)
                
                # Crear splitter vertical para los dos contenedores
                splitter = QSplitter(Qt.Orientation.Vertical)
                splitter.addWidget(total_listens_container)
                splitter.addWidget(artists_listens_container)
                
                # Añadir splitter al layout principal
                layout.addWidget(splitter)
            else:
                no_data = QLabel("No hay datos de escuchas con información de país")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
        
        except Exception as e:
            logging.error(f"Error al consultar escuchas por país: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)


    def on_countries_info_clicked(self):
        """Muestra información detallada del país seleccionado."""
        # Verificar si hay un país seleccionado
        if not hasattr(self, 'selected_country'):
            QMessageBox.information(
                self,
                "Selección requerida",
                "Por favor, selecciona primero un país de la tabla."
            )
            return
        
        # Cambiar a la página apropiada
        self.stackedWidget_countries.setCurrentIndex(1)
        
        # Obtener referencia al contenedor
        chart_container = self.chart_countries_artists  # Reutilizamos el mismo contenedor
        
        # Asegurar que tiene layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Limpiar cualquier contenido existente
        self.clear_layout(layout)
        
        # Crear un scroll area para contener toda la información
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Widget principal que irá dentro del scroll area
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Título principal
        title = QLabel(f"Información detallada: {self.selected_country}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)
        
        # Widget para mostrar texto en formato markdown
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                font-family: 'Noto Sans', sans-serif;
            }
        """)
        
        # Recopilar toda la información
        cursor = self.conn.cursor()
        try:
            # Artistas y sus álbumes
            cursor.execute("""
                SELECT 
                    ar.name, 
                    GROUP_CONCAT(a.name || CASE WHEN a.year IS NULL THEN '' ELSE ' (' || a.year || ')' END, '; ') as albums
                FROM 
                    artists ar
                LEFT JOIN 
                    albums a ON a.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                GROUP BY 
                    ar.name
                ORDER BY 
                    ar.name;
            """, (self.selected_country,))
            
            artist_albums = cursor.fetchall()
            
            # Sellos con artistas o álbumes de este país
            cursor.execute("""
                SELECT 
                    DISTINCT a.label, 
                    COUNT(DISTINCT ar.id) as artist_count,
                    COUNT(DISTINCT a.id) as album_count
                FROM 
                    albums a
                JOIN 
                    artists ar ON a.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                    AND a.label IS NOT NULL
                    AND a.label != ''
                GROUP BY 
                    a.label
                ORDER BY 
                    artist_count DESC, album_count DESC;
            """, (self.selected_country,))
            
            labels = cursor.fetchall()
            
            # Feeds para artistas o álbumes de este país
            cursor.execute("""
                SELECT 
                    f.feed_name, 
                    f.entity_type,
                    COUNT(*) as post_count
                FROM 
                    feeds f
                JOIN 
                    artists ar ON (f.entity_type = 'artist' AND f.entity_id = ar.id)
                WHERE 
                    ar.origin = ?
                GROUP BY 
                    f.feed_name, f.entity_type
                UNION ALL
                SELECT 
                    f.feed_name, 
                    f.entity_type,
                    COUNT(*) as post_count
                FROM 
                    feeds f
                JOIN 
                    albums alb ON (f.entity_type = 'album' AND f.entity_id = alb.id)
                JOIN 
                    artists ar ON alb.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                GROUP BY 
                    f.feed_name, f.entity_type
                ORDER BY 
                    post_count DESC;
            """, (self.selected_country, self.selected_country))
            
            feeds = cursor.fetchall()
            
            # Get artist tags directly - avoid JSON parsing in SQL
            cursor.execute("""
                SELECT ar.tags
                FROM artists ar
                WHERE ar.origin = ?
                AND ar.tags IS NOT NULL
                AND ar.tags != ''
            """, (self.selected_country,))
            
            # Process tags in Python instead of SQL
            artist_tags_rows = cursor.fetchall()
            artist_genre_counts = {}
            
            # Process each artist's tags
            for row in artist_tags_rows:
                tags = self.safely_parse_tags(row[0])
                for tag in tags:
                    artist_genre_counts[tag] = artist_genre_counts.get(tag, 0) + 1
            
            # Convert to format needed for reporting
            artist_genres = [(genre, count) for genre, count in 
                            sorted(artist_genre_counts.items(), key=lambda x: x[1], reverse=True)]
            
            # Album genres - use a more reliable query
            cursor.execute("""
                SELECT 
                    a.genre, 
                    COUNT(*) as album_count
                FROM 
                    albums a
                JOIN 
                    artists ar ON a.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                    AND a.genre IS NOT NULL 
                    AND a.genre != ''
                GROUP BY 
                    a.genre
                ORDER BY 
                    album_count DESC;
            """, (self.selected_country,))
            
            album_genres = cursor.fetchall()
            
            # Song genres - similar reliable approach
            cursor.execute("""
                SELECT 
                    s.genre, 
                    COUNT(*) as song_count
                FROM 
                    songs s
                JOIN 
                    albums a ON s.album = a.name
                JOIN 
                    artists ar ON a.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                    AND s.genre IS NOT NULL 
                    AND s.genre != ''
                GROUP BY 
                    s.genre
                ORDER BY 
                    song_count DESC;
            """, (self.selected_country,))
            
            song_genres = cursor.fetchall()
            
            # Combine all genres with their sources
            genres = []
            genres.extend([('Artistas', genre, count) for genre, count in artist_genres])
            genres.extend([('Álbumes', genre, count) for genre, count in album_genres])
            genres.extend([('Canciones', genre, count) for genre, count in song_genres])
            
            # Décadas con álbumes
            cursor.execute("""
                SELECT 
                    CAST(SUBSTR(a.year, 1, 3) || '0' AS INTEGER) as decade,
                    COUNT(*) as album_count
                FROM 
                    albums a
                JOIN 
                    artists ar ON a.artist_id = ar.id
                WHERE 
                    ar.origin = ?
                    AND a.year IS NOT NULL 
                    AND a.year != ''
                    AND LENGTH(a.year) >= 4
                    AND CAST(SUBSTR(a.year, 1, 4) AS INTEGER) > 1900
                GROUP BY 
                    decade
                ORDER BY 
                    decade;
            """, (self.selected_country,))
            
            decades = cursor.fetchall()
            
            # Escuchas por año
            query = f"""
                SELECT 
                    CASE 
                        WHEN EXISTS (SELECT 1 FROM scrobbles_{self.lastfm_username} LIMIT 1) THEN 1
                        ELSE 0
                    END as has_scrobbles,
                    CASE 
                        WHEN EXISTS (SELECT 1 FROM listens_{self.musicbrainz_username} LIMIT 1) THEN 1
                        ELSE 0
                    END as has_listens;
            """
            cursor.execute(query)
            listen_info = cursor.fetchone()
            has_scrobbles = listen_info[0] == 1
            has_listens = listen_info[1] == 1
            
            listen_years = []
            if has_scrobbles:
                query = f"""
                    SELECT 
                        strftime('%Y', s.scrobble_date) as year,
                        COUNT(*) as listen_count
                    FROM 
                        scrobbles_{self.lastfm_username} s
                    JOIN 
                        artists ar ON s.artist_name = ar.name
                    WHERE 
                        ar.origin = ?
                    GROUP BY 
                        year
                    ORDER BY 
                        year;
                """
                cursor.execute(query, (self.selected_country,))
                listen_years.extend(cursor.fetchall())
            
            if has_listens:
                query = f"""
                    SELECT 
                        strftime('%Y', l.listen_date) as year,
                        COUNT(*) as listen_count
                    FROM 
                        listens_{self.musicbrainz_username} l
                    JOIN 
                        artists ar ON l.artist_name = ar.name
                    WHERE 
                        ar.origin = ?
                    GROUP BY 
                        year
                    ORDER BY 
                        year;
                """
                cursor.execute(query, (self.selected_country,))
                listen_years.extend(cursor.fetchall())
            
            # Construir el texto markdown
            markdown = f"# Información detallada: {self.selected_country}\n\n"
            
            # Artistas y álbumes
            if artist_albums:
                markdown += "## Artistas y sus álbumes\n\n"
                for artist, albums in artist_albums:
                    if albums:
                        markdown += f"### {artist}\n\n"
                        albums_list = albums.split(';')
                        for album in albums_list:
                            markdown += f"- {album.strip()}\n"
                        markdown += "\n"
                    else:
                        markdown += f"### {artist}\n\n"
                        markdown += "- No hay álbumes registrados\n\n"
            else:
                markdown += "## Artistas y sus álbumes\n\n"
                markdown += "No hay artistas registrados para este país.\n\n"
            
            # Sellos discográficos
            if labels:
                markdown += "## Sellos discográficos\n\n"
                markdown += "| Sello | Artistas | Álbumes |\n"
                markdown += "|-------|---------|--------|\n"
                
                for label, artist_count, album_count in labels:
                    markdown += f"| {label} | {artist_count} | {album_count} |\n"
                
                markdown += "\n"
            else:
                markdown += "## Sellos discográficos\n\n"
                markdown += "No hay sellos registrados para artistas de este país.\n\n"
            
            # Feeds
            if feeds:
                markdown += "## Feeds\n\n"
                markdown += "| Nombre | Tipo de entidad | Publicaciones |\n"
                markdown += "|--------|----------------|---------------|\n"
                
                for feed_name, entity_type, post_count in feeds:
                    markdown += f"| {feed_name} | {entity_type} | {post_count} |\n"
                
                markdown += "\n"
            else:
                markdown += "## Feeds\n\n"
                markdown += "No hay feeds registrados para entidades de este país.\n\n"
            
            # Géneros
            if genres:
                markdown += "## Géneros\n\n"
                
                # Agrupar por fuente
                genre_by_source = {}
                for source, genre, count in genres:
                    if source not in genre_by_source:
                        genre_by_source[source] = []
                    genre_by_source[source].append((genre, count))
                
                for source, genre_data in genre_by_source.items():
                    markdown += f"### Géneros en {source}\n\n"
                    markdown += "| Género | Cantidad |\n"
                    markdown += "|--------|----------|\n"
                    
                    for genre, count in genre_data[:10]:  # Mostrar solo los 10 primeros
                        markdown += f"| {genre} | {count} |\n"
                    
                    if len(genre_data) > 10:
                        markdown += f"| ... y {len(genre_data) - 10} más | - |\n"
                    
                    markdown += "\n"
            else:
                markdown += "## Géneros\n\n"
                markdown += "No hay información de géneros para este país.\n\n"
            
            # Décadas
            if decades:
                markdown += "## Distribución por década\n\n"
                markdown += "| Década | Álbumes |\n"
                markdown += "|--------|--------|\n"
                
                for decade, count in decades:
                    markdown += f"| {decade}s | {count} |\n"
                
                markdown += "\n"
            else:
                markdown += "## Distribución por década\n\n"
                markdown += "No hay información de décadas para álbumes de este país.\n\n"
            
            # Escuchas por año
            if listen_years:
                markdown += "## Escuchas por año\n\n"
                markdown += "| Año | Escuchas |\n"
                markdown += "|-----|----------|\n"
                
                for year, count in listen_years:
                    markdown += f"| {year} | {count} |\n"
                
                markdown += "\n"
            else:
                markdown += "## Escuchas por año\n\n"
                markdown += "No hay información de escuchas para artistas de este país.\n\n"
            
            # Establecer el texto markdown
            info_text.setMarkdown(markdown)
            
            # Añadir el widget de texto al layout principal
            main_layout.addWidget(info_text)
            
            # Asignar el widget principal al scroll area
            scroll_area.setWidget(main_widget)
            
            # Añadir el scroll area al layout del contenedor
            layout.addWidget(scroll_area)
            
        except Exception as e:
            logging.error(f"Error al generar información del país: {e}")
            import traceback
            logging.error(traceback.format_exc())
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)


    def execute_query_safely(self, query, params=None, default_return=None):
        """Safely execute a database query with error handling."""
        if not self.ensure_db_connection():
            return default_return
            
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            logging.error(f"Error executing query: {e}")
            logging.error(f"Query: {query}")
            logging.error(f"Params: {params}")
            import traceback
            logging.error(traceback.format_exc())
            return default_return

    def format_decade_from_year(self, year_str):
        """Safely convert a year string to a decade string like '1990s'."""
        try:
            if not year_str or len(year_str) < 4:
                return "Desconocido"
                
            year = int(year_str[:4])  # Take first 4 chars and convert to int
            decade = (year // 10) * 10
            return f"{decade}s"
        except (ValueError, TypeError):
            return "Desconocido"

# FEEDS 

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
        """Safely removes all widgets from a layout."""
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
            logging.error(f"Error in clear_layout: {e}")

    def ensure_db_connection(self):
        """Asegura que hay una conexión activa a la base de datos."""
        if self.conn is None or not self.is_connection_valid():
            try:
                logging.info(f"Reconectando a la base de datos: {self.db_path}")
                if self.conn:
                    try:
                        self.conn.close()
                    except:
                        pass
                
                if not self.db_path or not os.path.exists(self.db_path):
                    # Buscar la base de datos en ubicaciones comunes
                    possible_paths = [
                        Path(os.path.dirname(__file__), "data", "music.db"),
                        Path(PROJECT_ROOT, "data", "music.db"),
                        Path(os.path.expanduser("~"), ".config", "musicapp", "music.db")
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            self.db_path = path
                            logging.info(f"Base de datos encontrada en: {path}")
                            break
                
                if self.db_path and os.path.exists(self.db_path):
                    self.conn = sqlite3.connect(self.db_path)
                    self.conn.row_factory = sqlite3.Row
                    # Ejecutar una consulta simple para verificar la conexión
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    logging.info(f"Conexión a base de datos establecida correctamente: {self.db_path}")
                    return True
                else:
                    logging.error(f"No se encontró la base de datos. Path actual: {self.db_path}")
                    return False
            except Exception as e:
                logging.error(f"Error al conectar a la base de datos: {e}")
                import traceback
                logging.error(traceback.format_exc())
                return False
        return True

    def is_connection_valid(self):
        """Verifica si la conexión a la base de datos es válida."""
        if not self.conn:
            return False
        
        try:
            # Ejecutar una consulta simple para verificar la conexión
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True
        except Exception as e:
            logging.error(f"Error validando conexión DB: {e}")
            return False

    def cleanup(self):
        """Limpieza antes de cerrar el módulo."""
        if self.conn:
            try:
                self.conn.close()
            except Exception as e:
                logging.error(f"Error al cerrar la conexión DB: {e}")

    def ensure_widget_has_layout(self, widget, layout_type=QVBoxLayout):
        """Ensures a widget has a layout without creating duplicates."""
        if widget is None:
            logging.error("Widget is None in ensure_widget_has_layout")
            return None
        
        # Check if widget already has a layout
        layout = widget.layout()
        
        if layout is None:
            # Create a new layout only if one doesn't exist
            logging.info(f"Creating new layout for widget {widget.objectName()}")
            layout = layout_type()
            widget.setLayout(layout)
        else:
            # Use existing layout
            logging.debug(f"Widget {widget.objectName()} already has a layout: {type(layout).__name__}")
        
        return layout

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


    def create_splitter_with_widgets(self, left_widget, right_widget, orientation=Qt.Orientation.Horizontal, sizes=None):
        """
        Crea un splitter y coloca dos widgets en él.
        
        Args:
            left_widget (QWidget): Widget para colocar en la parte izquierda/superior
            right_widget (QWidget): Widget para colocar en la parte derecha/inferior
            orientation (Qt.Orientation): Orientación del splitter (Horizontal o Vertical)
            sizes (list, optional): Lista de dos enteros para establecer el tamaño inicial de cada sección

        Returns:
            QSplitter: El splitter configurado con los widgets
        """
        # Verificar que los widgets sean válidos
        if not isinstance(left_widget, QWidget) or not isinstance(right_widget, QWidget):
            logging.error("Los argumentos deben ser widgets válidos")
            return None
        
        try:
            # Crear un splitter con la orientación especificada
            splitter = QSplitter(orientation)
            
            # Añadir los widgets directamente al splitter
            splitter.addWidget(left_widget)
            splitter.addWidget(right_widget)
            
            # Configurar tamaños iniciales si se proporcionan
            if sizes and isinstance(sizes, list) and len(sizes) == 2:
                splitter.setSizes(sizes)
            elif orientation == Qt.Orientation.Horizontal:
                # Valores predeterminados: 40% izquierda, 60% derecha
                splitter.setSizes([400, 600])
            else:
                # Valores predeterminados para orientación vertical: 50% cada uno
                splitter.setSizes([500, 500])
                
            # Permitir colapsar cuando se mueve la divisoria al extremo
            splitter.setChildrenCollapsible(True)
            
            # Configurar para expandir cuando se redimensiona el contenedor padre
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 1)
            
            logging.info(f"Splitter creado exitosamente con widgets {left_widget.objectName()} y {right_widget.objectName()}")
            return splitter
            
        except Exception as e:
            logging.error(f"Error al crear splitter: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None


    def safely_parse_tags(self, tags_string):
        """Safely parse a tags string into a list of individual tags."""
        if not tags_string or tags_string.strip() == '':
            return []
            
        # Remove any characters that might cause JSON issues
        try:
            # Simple approach: split by comma and clean each tag
            tags = []
            for tag in tags_string.split(','):
                clean_tag = tag.strip()
                if clean_tag:
                    tags.append(clean_tag)
            return tags
        except Exception as e:
            logging.error(f"Error parsing tags string: {e}")
            return []


    def load_entity_type_stats(self):
        """Load statistics about entity types with feeds (for main page)."""
        self.FeedsSubmodule.load_entity_type_stats()