from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLabel, QPushButton)
from PyQt6.QtCore import Qt
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tools.chart_utils import ChartFactory

class TimeSubmodule:
    """
    Submodule to handle time-related statistics and visualizations.
    """
    
    def __init__(self, stats_module, db_connection, helper_functions=None, widgets=None):
        """
        Initialize the time submodule.
        
        Args:
            stats_module: Reference to the main StatsModule
            db_connection: Database connection
            helper_functions: Dictionary of helper functions from the main module
        """
        self.stats_module = stats_module
        self.conn = db_connection
        
        # Store helper functions if provided
        self.helper_functions = helper_functions or {}
        self.clear_layout = self.helper_functions.get('clear_layout', self._default_clear_layout)
        self.ensure_widget_has_layout = self.helper_functions.get('ensure_widget_has_layout', self._default_ensure_layout)
        
        # Data cache
        self.artist_year_data = None
        self.artist_decade_data = None
        self.album_year_data = None
        self.album_decade_data = None
        self.label_year_data = None
        self.label_decade_data = None
        
        # Initialize UI references
        self._init_ui_references()

        # Verify UI components
        self._verify_ui_components()
    
    def _init_ui_references(self):
        """Initialize references to UI elements."""
        # Main stacked widget
        self.stackedWidget_time = getattr(self.stats_module, 'stackedWidget_time', None)
        
        # Button references
        self.time_button_artist = getattr(self.stats_module, 'time_button_artist', None)
        self.time_button_album = getattr(self.stats_module, 'time_button_album', None)
        self.time_button_labels = getattr(self.stats_module, 'time_button_labels', None)
        self.time_button_genres = getattr(self.stats_module, 'time_button_genres', None)
        self.time_button_feeds = getattr(self.stats_module, 'time_button_feeds', None)
        self.time_button_listens = getattr(self.stats_module, 'time_button_listens', None)
        self.time_button_info = getattr(self.stats_module, 'time_button_info', None)
        
        # Page references
        self.time_page_inicio = getattr(self.stats_module, 'time_page_inicio', None)
        self.time_page_artists = getattr(self.stats_module, 'time_page_artists', None)
        self.time_page_albums = getattr(self.stats_module, 'time_page_albums', None)
        self.time_page_labels = getattr(self.stats_module, 'time_page_labels', None)
        self.time_page_genres = getattr(self.stats_module, 'time_page_genres', None)
        self.time_page_feeds = getattr(self.stats_module, 'time_page_feeds', None)
        self.time_page_listens = getattr(self.stats_module, 'time_page_listens', None)
        self.time_page_info = getattr(self.stats_module, 'time_page_info', None)
        
        # Artists page widgets
        self.widget_time_artists_top = getattr(self.stats_module, 'widget_time_artists_top', None)
        self.widget_time_artists_bott = getattr(self.stats_module, 'widget_time_artists_bott', None)
        self.table_time_artists_top = getattr(self.stats_module, 'table_time_artists_top', None)
        self.table_time_artists_bott = getattr(self.stats_module, 'table_time_artists_bott', None)
        self.chart_time_artists_top = getattr(self.stats_module, 'chart_time_artists_top', None)
        self.chart_time_artists_bott = getattr(self.stats_module, 'chart_time_artists_bott', None)
        
        # Albums page widgets
        self.widget_time_albums_top = getattr(self.stats_module, 'widget_time_albums_top', None) 
        self.widget_time_albums_bott = getattr(self.stats_module, 'widget_time_albums_bott', None)
        self.table_time_albums_top = getattr(self.stats_module, 'table_time_albums_top', None)
        self.table_time_albums_bott = getattr(self.stats_module, 'table_time_albums_bott', None)
        self.chart_time_albums_top = getattr(self.stats_module, 'chart_time_albums_top', None)
        self.chart_time_albums_bott = getattr(self.stats_module, 'chart_time_albums_bott', None)
        
        # Labels page widgets
        self.widget_time_labels_top = getattr(self.stats_module, 'widget_time_labels_top', None)
        self.widget_time_labels_bott = getattr(self.stats_module, 'widget_time_labels_bott', None)
        self.table_time_labels_top = getattr(self.stats_module, 'table_time_labels_top', None)
        self.table_time_labels_bott = getattr(self.stats_module, 'table_time_labels_bott', None)
        self.chart_time_labels_top = getattr(self.stats_module, 'chart_time_labels_top', None)
        self.chart_time_labels_bott = getattr(self.stats_module, 'chart_time_labels_bott', None)
   
        # Genres page widgets
        self.widget_time_genres_top = getattr(self.stats_module, 'widget_time_genres_top', None)
        self.widget_time_genres_bott = getattr(self.stats_module, 'widget_time_genres_bott', None)
        self.table_time_genres_top = getattr(self.stats_module, 'table_time_genres_top', None)
        self.table_time_genres_bott = getattr(self.stats_module, 'table_time_genres_bott', None)
        self.chart_time_genres_top = getattr(self.stats_module, 'chart_time_genres_top', None)
        self.chart_time_genres_bott = getattr(self.stats_module, 'chart_time_genres_bott', None)
        
        # Feeds page widgets
        self.widget_time_feeds_top = getattr(self.stats_module, 'widget_time_feeds_top', None)
        self.widget_time_feeds_bott = getattr(self.stats_module, 'widget_time_feeds_bott', None)
        self.table_time_feeds_top = getattr(self.stats_module, 'table_time_feeds_top', None)
        self.table_time_feeds_bott = getattr(self.stats_module, 'table_time_feeds_bott', None)
        self.chart_time_feeds_top = getattr(self.stats_module, 'chart_time_feeds_top', None)
        self.chart_time_feeds_bott = getattr(self.stats_module, 'chart_time_feeds_bott', None)
        
        # Listens page widgets

    def _default_clear_layout(self, layout):
        """Default implementation of clear_layout."""
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
    
    def _default_ensure_layout(self, widget, layout_type=QVBoxLayout):
        """Default implementation of ensure_widget_has_layout."""
        if widget is None:
            return None
            
        layout = widget.layout()
        if layout is None:
            layout = layout_type()
            widget.setLayout(layout)
        return layout
    
    def setup_connections(self):
        """Set up UI signal connections."""
        if self.time_button_artist:
            self.time_button_artist.clicked.connect(self.show_artists_page)
        
        if self.time_button_album:
            self.time_button_album.clicked.connect(self.show_albums_page)
            
        if self.time_button_labels:
            self.time_button_labels.clicked.connect(self.show_labels_page)
    
  
    def load_time_stats(self):
        """Load initial time-related statistics."""
        if not self.conn:
            logging.error("No database connection available")
            return
        
        # Access widgets through the parent module
        stackedWidget_time = getattr(self.stats_module, 'stackedWidget_time', None)
        time_page_inicio = getattr(self.stats_module, 'time_page_inicio', None)
        
        # Load data for each category
        self.load_artist_time_data()
        self.load_album_time_data()
        self.load_label_time_data()
        
        # Make sure we're on the first page
        if stackedWidget_time and time_page_inicio:
            stackedWidget_time.setCurrentWidget(time_page_inicio)
    
    def show_artists_page(self):
        """Show the artists time statistics page."""
        if self.stackedWidget_time and self.time_page_artists:
            self.stackedWidget_time.setCurrentWidget(self.time_page_artists)
            self.update_artists_view()

    def show_albums_page(self):
        """Show the albums time statistics page."""
        if self.stackedWidget_time and self.time_page_albums:
            self.stackedWidget_time.setCurrentWidget(self.time_page_albums)
            self.update_albums_view()

    def show_labels_page(self):
        """Show the labels time statistics page."""
        if self.stackedWidget_time and self.time_page_labels:
            self.stackedWidget_time.setCurrentWidget(self.time_page_labels)
            self.update_labels_view()
    
    def load_artist_time_data(self):
        """Load artist time data from the database."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        # Artists by year of formation
        try:
            cursor.execute("""
                SELECT 
                    formed_year, 
                    COUNT(*) as artist_count
                FROM 
                    artists
                WHERE 
                    formed_year IS NOT NULL 
                    AND formed_year != 0
                GROUP BY 
                    formed_year
                ORDER BY 
                    formed_year;
            """)
            
            self.artist_year_data = cursor.fetchall()
            logging.info(f"Loaded {len(self.artist_year_data)} artist year records")
            
            # Artists by decade of formation
            cursor.execute("""
                SELECT 
                    (formed_year / 10) * 10 as decade, 
                    COUNT(*) as artist_count
                FROM 
                    artists
                WHERE 
                    formed_year IS NOT NULL 
                    AND formed_year != 0
                GROUP BY 
                    decade
                ORDER BY 
                    decade;
            """)
            
            self.artist_decade_data = cursor.fetchall()
            logging.info(f"Loaded {len(self.artist_decade_data)} artist decade records")
            
        except Exception as e:
            logging.error(f"Error loading artist time data: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def load_album_time_data(self):
        """Load album time data from the database."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        # Albums by year of release
        try:
            cursor.execute("""
                SELECT 
                    CASE
                        WHEN LENGTH(year) >= 4 THEN SUBSTR(year, 1, 4)
                        ELSE year
                    END as release_year, 
                    COUNT(*) as album_count
                FROM 
                    albums
                WHERE 
                    year IS NOT NULL 
                    AND year != ''
                GROUP BY 
                    release_year
                ORDER BY 
                    release_year;
            """)
            
            self.album_year_data = cursor.fetchall()
            logging.info(f"Loaded {len(self.album_year_data)} album year records")
            
            # Albums by decade of release - modified to avoid REGEXP
            cursor.execute("""
                SELECT 
                    CASE
                        WHEN LENGTH(year) >= 4 AND SUBSTR(year, 1, 4) GLOB '[0-9][0-9][0-9][0-9]' 
                        THEN (CAST(SUBSTR(year, 1, 4) AS INTEGER) / 10) * 10
                        ELSE NULL
                    END as decade, 
                    COUNT(*) as album_count
                FROM 
                    albums
                WHERE 
                    year IS NOT NULL 
                    AND year != ''
                    AND LENGTH(year) >= 4
                    AND SUBSTR(year, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
                GROUP BY 
                    decade
                ORDER BY 
                    decade;
            """)
            
            self.album_decade_data = cursor.fetchall()
            logging.info(f"Loaded {len(self.album_decade_data)} album decade records")
            
        except Exception as e:
            logging.error(f"Error loading album time data: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def load_label_time_data(self):
        """Load label time data from the database."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        # Labels by year of foundation
        try:
            cursor.execute("""
                SELECT 
                    founded_year, 
                    COUNT(*) as label_count
                FROM 
                    labels
                WHERE 
                    founded_year IS NOT NULL 
                    AND founded_year != 0
                GROUP BY 
                    founded_year
                ORDER BY 
                    founded_year;
            """)
            
            self.label_year_data = cursor.fetchall()
            logging.info(f"Loaded {len(self.label_year_data)} label year records")
            
            # Labels by decade of foundation
            cursor.execute("""
                SELECT 
                    (founded_year / 10) * 10 as decade, 
                    COUNT(*) as label_count
                FROM 
                    labels
                WHERE 
                    founded_year IS NOT NULL 
                    AND founded_year != 0
                GROUP BY 
                    decade
                ORDER BY 
                    decade;
            """)
            
            self.label_decade_data = cursor.fetchall()
            logging.info(f"Loaded {len(self.label_decade_data)} label decade records")
            
        except Exception as e:
            logging.error(f"Error loading label time data: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def update_artists_view(self):
        """Update the artists time statistics view."""
        # Make sure we have data
        if not self.artist_year_data or not self.artist_decade_data:
            self.load_artist_time_data()
        
        # Update top table with years
        if self.table_time_artists_top:
            self.table_time_artists_top.clear()
            self.table_time_artists_top.setColumnCount(2)
            self.table_time_artists_top.setHorizontalHeaderLabels(["Año", "Artistas"])
            
            self.table_time_artists_top.setRowCount(len(self.artist_year_data))
            for i, (year, count) in enumerate(self.artist_year_data):
                self.table_time_artists_top.setItem(i, 0, QTableWidgetItem(str(year)))
                self.table_time_artists_top.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_time_artists_top.resizeColumnsToContents()
        
        # Update bottom table with decades
        if self.table_time_artists_bott:
            self.table_time_artists_bott.clear()
            self.table_time_artists_bott.setColumnCount(2)
            self.table_time_artists_bott.setHorizontalHeaderLabels(["Década", "Artistas"])
            
            self.table_time_artists_bott.setRowCount(len(self.artist_decade_data))
            for i, (decade, count) in enumerate(self.artist_decade_data):
                decade_label = f"{decade}s"
                self.table_time_artists_bott.setItem(i, 0, QTableWidgetItem(decade_label))
                self.table_time_artists_bott.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_time_artists_bott.resizeColumnsToContents()
        
        # Create artist formation year chart for top section
        if self.chart_time_artists_top:
            chart_layout = self.ensure_widget_has_layout(self.chart_time_artists_top)
            self.clear_layout(chart_layout)
            
            # Title
            title = QLabel("Artistas por Año de Formación")
            title.setStyleSheet("font-size: 14px; font-weight: bold;")
            chart_layout.addWidget(title)
            
            # Create chart
            year_chart = ChartFactory.create_bar_chart(
                self.artist_year_data[-30:] if len(self.artist_year_data) > 30 else self.artist_year_data,
                "Artistas por Año de Formación",
                x_label="Año",
                y_label="Artistas"
            )
            
            if year_chart:
                chart_layout.addWidget(year_chart)
        
        # Create decade chart for bottom section
        if self.chart_time_artists_bott:
            chart_layout = self.ensure_widget_has_layout(self.chart_time_artists_bott)
            self.clear_layout(chart_layout)
            
            # Title
            decade_title = QLabel("Artistas por Década de Formación")
            decade_title.setStyleSheet("font-size: 14px; font-weight: bold;")
            chart_layout.addWidget(decade_title)
            
            # Create decade chart
            decade_chart = ChartFactory.create_pie_chart(
                [(f"{decade}s", count) for decade, count in self.artist_decade_data],
                "Artistas por Década de Formación"
            )
            
            if decade_chart:
                chart_layout.addWidget(decade_chart)
        
        # Connect table click handlers
        if self.table_time_artists_top:
            try:
                self.table_time_artists_top.itemClicked.disconnect()
            except:
                pass
            self.table_time_artists_top.itemClicked.connect(
                lambda item: self.show_artists_by_year(int(self.table_time_artists_top.item(item.row(), 0).text()))
            )
        
        if self.table_time_artists_bott:
            try:
                self.table_time_artists_bott.itemClicked.disconnect()
            except:
                pass
            self.table_time_artists_bott.itemClicked.connect(
                lambda item: self.show_artists_by_decade(int(self.table_time_artists_bott.item(item.row(), 0).text().replace('s', '')))
            )
    
 
    def update_albums_view(self):
        """Update the albums time statistics view."""
        # Make sure we have data
        if not self.album_year_data or not self.album_decade_data:
            self.load_album_time_data()
        
        # Update top table with years
        if self.table_time_albums_top:
            self.table_time_albums_top.clear()
            self.table_time_albums_top.setColumnCount(2)
            self.table_time_albums_top.setHorizontalHeaderLabels(["Año", "Álbumes"])
            
            self.table_time_albums_top.setRowCount(len(self.album_year_data))
            for i, (year, count) in enumerate(self.album_year_data):
                self.table_time_albums_top.setItem(i, 0, QTableWidgetItem(str(year)))
                self.table_time_albums_top.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_time_albums_top.resizeColumnsToContents()
        
        # Update bottom table with decades
        if self.table_time_albums_bott:
            self.table_time_albums_bott.clear()
            self.table_time_albums_bott.setColumnCount(2)
            self.table_time_albums_bott.setHorizontalHeaderLabels(["Década", "Álbumes"])
            
            self.table_time_albums_bott.setRowCount(len(self.album_decade_data))
            for i, (decade, count) in enumerate(self.album_decade_data):
                decade_label = f"{decade}s"
                self.table_time_albums_bott.setItem(i, 0, QTableWidgetItem(decade_label))
                self.table_time_albums_bott.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_time_albums_bott.resizeColumnsToContents()
        
        # Create album release year chart for top section
        if self.chart_time_albums_top:
            chart_layout = self.ensure_widget_has_layout(self.chart_time_albums_top)
            self.clear_layout(chart_layout)
            
            # Title
            title = QLabel("Álbumes por Año de Lanzamiento")
            title.setStyleSheet("font-size: 14px; font-weight: bold;")
            chart_layout.addWidget(title)
            
            # Create chart - use line chart for chronological data
            year_chart = ChartFactory.create_line_chart(
                self.album_year_data[-30:] if len(self.album_year_data) > 30 else self.album_year_data,
                "Álbumes por Año de Lanzamiento",
                x_label="Año",
                y_label="Álbumes"
            )
            
            if year_chart:
                chart_layout.addWidget(year_chart)
        
        # Create decade chart for bottom section
        if self.chart_time_albums_bott:
            chart_layout = self.ensure_widget_has_layout(self.chart_time_albums_bott)
            self.clear_layout(chart_layout)
            
            # Title
            decade_title = QLabel("Álbumes por Década de Lanzamiento")
            decade_title.setStyleSheet("font-size: 14px; font-weight: bold;")
            chart_layout.addWidget(decade_title)
            
            # Create decade chart
            decade_chart = ChartFactory.create_bar_chart(
                [(f"{decade}s", count) for decade, count in self.album_decade_data],
                "Álbumes por Década de Lanzamiento",
                x_label="Década",
                y_label="Álbumes"
            )
            
            if decade_chart:
                chart_layout.addWidget(decade_chart)
        
        # Connect table click handlers
        if self.table_time_albums_top:
            try:
                self.table_time_albums_top.itemClicked.disconnect()
            except:
                pass
            self.table_time_albums_top.itemClicked.connect(
                lambda item: self.show_albums_by_year(self.table_time_albums_top.item(item.row(), 0).text())
            )
        
        if self.table_time_albums_bott:
            try:
                self.table_time_albums_bott.itemClicked.disconnect()
            except:
                pass
            self.table_time_albums_bott.itemClicked.connect(
                lambda item: self.show_albums_by_decade(int(self.table_time_albums_bott.item(item.row(), 0).text().replace('s', '')))
            )
    


    def update_labels_view(self):
        """Update the labels time statistics view."""
        # Make sure we have data
        if not self.label_year_data or not self.label_decade_data:
            self.load_label_time_data()
        
        # Update top table with years
        if self.table_time_labels_top:
            self.table_time_labels_top.clear()
            self.table_time_labels_top.setColumnCount(2)
            self.table_time_labels_top.setHorizontalHeaderLabels(["Año", "Sellos"])
            
            self.table_time_labels_top.setRowCount(len(self.label_year_data))
            for i, (year, count) in enumerate(self.label_year_data):
                self.table_time_labels_top.setItem(i, 0, QTableWidgetItem(str(year)))
                self.table_time_labels_top.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_time_labels_top.resizeColumnsToContents()
        
        # Update bottom table with decades
        if self.table_time_labels_bott:
            self.table_time_labels_bott.clear()
            self.table_time_labels_bott.setColumnCount(2)
            self.table_time_labels_bott.setHorizontalHeaderLabels(["Década", "Sellos"])
            
            self.table_time_labels_bott.setRowCount(len(self.label_decade_data))
            for i, (decade, count) in enumerate(self.label_decade_data):
                decade_label = f"{decade}s"
                self.table_time_labels_bott.setItem(i, 0, QTableWidgetItem(decade_label))
                self.table_time_labels_bott.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_time_labels_bott.resizeColumnsToContents()
        
        # Create label foundation year chart for top section
        if self.chart_time_labels_top:
            chart_layout = self.ensure_widget_has_layout(self.chart_time_labels_top)
            self.clear_layout(chart_layout)
            
            # Title
            title = QLabel("Sellos por Año de Fundación")
            title.setStyleSheet("font-size: 14px; font-weight: bold;")
            chart_layout.addWidget(title)
            
            # Create chart
            year_chart = ChartFactory.create_bar_chart(
                self.label_year_data[-30:] if len(self.label_year_data) > 30 else self.label_year_data,
                "Sellos por Año de Fundación",
                x_label="Año",
                y_label="Sellos"
            )
            
            if year_chart:
                chart_layout.addWidget(year_chart)
        
        # Create decade chart for bottom section
        if self.chart_time_labels_bott:
            chart_layout = self.ensure_widget_has_layout(self.chart_time_labels_bott)
            self.clear_layout(chart_layout)
            
            # Title
            decade_title = QLabel("Sellos por Década de Fundación")
            decade_title.setStyleSheet("font-size: 14px; font-weight: bold;")
            chart_layout.addWidget(decade_title)
            
            # Create decade chart
            decade_chart = ChartFactory.create_pie_chart(
                [(f"{decade}s", count) for decade, count in self.label_decade_data],
                "Sellos por Década de Fundación"
            )
            
            if decade_chart:
                chart_layout.addWidget(decade_chart)
        
        # Connect table click handlers
        if self.table_time_labels_top:
            try:
                self.table_time_labels_top.itemClicked.disconnect()
            except:
                pass
            self.table_time_labels_top.itemClicked.connect(
                lambda item: self.show_labels_by_year(int(self.table_time_labels_top.item(item.row(), 0).text()))
            )
        
        if self.table_time_labels_bott:
            try:
                self.table_time_labels_bott.itemClicked.disconnect()
            except:
                pass
            self.table_time_labels_bott.itemClicked.connect(
                lambda item: self.show_labels_by_decade(int(self.table_time_labels_bott.item(item.row(), 0).text().replace('s', '')))
            )

    def show_artists_by_year(self, year):
        """Show artists formed in a specific year in the top chart area."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    name,
                    origin,
                    total_albums
                FROM 
                    artists
                WHERE 
                    formed_year = ?
                ORDER BY 
                    name;
            """, (year,))
            
            artists = cursor.fetchall()
            
            if artists and self.chart_time_artists_top:
                chart_layout = self.ensure_widget_has_layout(self.chart_time_artists_top)
                self.clear_layout(chart_layout)
                
                title = QLabel(f"Artistas Formados en {year}")
                title.setStyleSheet("font-size: 14px; font-weight: bold;")
                chart_layout.addWidget(title)
                
                # Create a pie chart showing distribution
                chart_data = [(name, albums or 0) for name, origin, albums in artists]
                chart = ChartFactory.create_pie_chart(
                    chart_data,
                    f"Artistas Formados en {year}",
                    limit=15
                )
                
                if chart:
                    chart_layout.addWidget(chart)
        except Exception as e:
            logging.error(f"Error showing artists by year {year}: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def show_artists_by_decade(self, decade):
        """Show artists formed in a specific decade in the bottom chart area."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    name,
                    origin,
                    formed_year,
                    total_albums
                FROM 
                    artists
                WHERE 
                    formed_year >= ?
                    AND formed_year < ? + 10
                ORDER BY 
                    formed_year, name;
            """, (decade, decade))
            
            artists = cursor.fetchall()
            
            if artists and self.chart_time_artists_bott:
                chart_layout = self.ensure_widget_has_layout(self.chart_time_artists_bott)
                self.clear_layout(chart_layout)
                
                title = QLabel(f"Artistas Formados en los {decade}s")
                title.setStyleSheet("font-size: 14px; font-weight: bold;")
                chart_layout.addWidget(title)
                
                # Create a pie chart showing country distribution
                country_data = {}
                for _, origin, _, _ in artists:
                    if origin:
                        if origin in country_data:
                            country_data[origin] += 1
                        else:
                            country_data[origin] = 1
                
                if country_data:
                    country_chart_data = [(country, count) for country, count in country_data.items()]
                    country_chart = ChartFactory.create_pie_chart(
                        country_chart_data,
                        f"Países de Artistas de los {decade}s",
                    )
                    
                    if country_chart:
                        chart_layout.addWidget(country_chart)
        except Exception as e:
            logging.error(f"Error showing artists by decade {decade}: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def show_albums_by_year(self, year):
        """Show albums released in a specific year in the top chart area."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    a.name as album_name,
                    (SELECT name FROM artists WHERE id = a.artist_id) as artist_name,
                    a.total_tracks
                FROM 
                    albums a
                WHERE 
                    a.year LIKE ? || '%'
                ORDER BY 
                    artist_name, album_name;
            """, (year,))
            
            albums = cursor.fetchall()
            
            if albums and self.chart_time_albums_top:
                chart_layout = self.ensure_widget_has_layout(self.chart_time_albums_top)
                self.clear_layout(chart_layout)
                
                title = QLabel(f"Álbumes Lanzados en {year}")
                title.setStyleSheet("font-size: 14px; font-weight: bold;")
                chart_layout.addWidget(title)
                
                # Create a pie chart showing artist distribution
                artist_data = {}
                for _, artist, _ in albums:
                    if artist:
                        if artist in artist_data:
                            artist_data[artist] += 1
                        else:
                            artist_data[artist] = 1
                
                if artist_data:
                    artist_chart_data = [(artist, count) for artist, count in artist_data.items()]
                    artist_chart = ChartFactory.create_pie_chart(
                        artist_chart_data,
                        f"Artistas con Álbumes en {year}",
                        limit=15
                    )
                    
                    if artist_chart:
                        chart_layout.addWidget(artist_chart)
        except Exception as e:
            logging.error(f"Error showing albums by year {year}: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def show_albums_by_decade(self, decade):
        """Show albums released in a specific decade in the bottom chart area."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        try:
            # Get the decade range
            decade_start = decade
            decade_end = decade + 9
            
            cursor.execute("""
                SELECT 
                    a.genre, 
                    COUNT(*) as album_count
                FROM 
                    albums a
                WHERE 
                    CAST(SUBSTR(a.year, 1, 4) AS INTEGER) >= ?
                    AND CAST(SUBSTR(a.year, 1, 4) AS INTEGER) <= ?
                    AND a.genre IS NOT NULL 
                    AND a.genre != ''
                GROUP BY 
                    a.genre
                ORDER BY 
                    album_count DESC
                LIMIT 15;
            """, (decade_start, decade_end))
            
            genres = cursor.fetchall()
            
            if genres and self.chart_time_albums_bott:
                chart_layout = self.ensure_widget_has_layout(self.chart_time_albums_bott)
                self.clear_layout(chart_layout)
                
                title = QLabel(f"Géneros de Álbumes de los {decade}s")
                title.setStyleSheet("font-size: 14px; font-weight: bold;")
                chart_layout.addWidget(title)
                
                # Create a pie chart showing genre distribution
                genre_chart = ChartFactory.create_pie_chart(
                    genres,
                    f"Géneros de Álbumes de los {decade}s"
                )
                
                if genre_chart:
                    chart_layout.addWidget(genre_chart)
        except Exception as e:
            logging.error(f"Error showing albums by decade {decade}: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def show_labels_by_year(self, year):
        """Show labels founded in a specific year in the top chart area."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    name,
                    country,
                    mb_type
                FROM 
                    labels
                WHERE 
                    founded_year = ?
                ORDER BY 
                    name;
            """, (year,))
            
            labels = cursor.fetchall()
            
            if labels and self.chart_time_labels_top:
                chart_layout = self.ensure_widget_has_layout(self.chart_time_labels_top)
                self.clear_layout(chart_layout)
                
                title = QLabel(f"Sellos Fundados en {year}")
                title.setStyleSheet("font-size: 14px; font-weight: bold;")
                chart_layout.addWidget(title)
                
                # Create a pie chart showing country distribution
                country_data = {}
                for _, country, _ in labels:
                    if country:
                        if country in country_data:
                            country_data[country] += 1
                        else:
                            country_data[country] = 1
                
                if country_data:
                    country_chart_data = [(country, count) for country, count in country_data.items()]
                    country_chart = ChartFactory.create_pie_chart(
                        country_chart_data,
                        f"Países de Sellos Fundados en {year}"
                    )
                    
                    if country_chart:
                        chart_layout.addWidget(country_chart)
        except Exception as e:
            logging.error(f"Error showing labels by year {year}: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def show_labels_by_decade(self, decade):
        """Show labels founded in a specific decade in the bottom chart area."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    mb_type, 
                    COUNT(*) as label_count
                FROM 
                    labels
                WHERE 
                    founded_year >= ?
                    AND founded_year < ? + 10
                    AND mb_type IS NOT NULL 
                    AND mb_type != ''
                GROUP BY 
                    mb_type
                ORDER BY 
                    label_count DESC;
            """, (decade, decade))
            
            types = cursor.fetchall()
            
            if types and self.chart_time_labels_bott:
                chart_layout = self.ensure_widget_has_layout(self.chart_time_labels_bott)
                self.clear_layout(chart_layout)
                
                title = QLabel(f"Tipos de Sellos de los {decade}s")
                title.setStyleSheet("font-size: 14px; font-weight: bold;")
                chart_layout.addWidget(title)
                
                # Create a pie chart showing type distribution
                type_chart = ChartFactory.create_pie_chart(
                    types,
                    f"Tipos de Sellos de los {decade}s"
                )
                
                if type_chart:
                    chart_layout.addWidget(type_chart)
                
                # Also get albums by labels from this decade
                cursor.execute("""
                    SELECT 
                        l.name,
                        COUNT(a.id) as album_count
                    FROM 
                        labels l
                    JOIN 
                        albums a ON a.label = l.name
                    WHERE 
                        l.founded_year >= ?
                        AND l.founded_year < ? + 10
                    GROUP BY
                        l.name
                    ORDER BY
                        album_count DESC
                    LIMIT 15;
                """, (decade, decade))
                
                label_albums = cursor.fetchall()
                
                if label_albums:
                    album_title = QLabel(f"Álbumes por Sello de los {decade}s")
                    album_title.setStyleSheet("font-size: 14px; font-weight: bold;")
                    chart_layout.addWidget(album_title)
                    
                    album_chart = ChartFactory.create_bar_chart(
                        label_albums,
                        f"Álbumes por Sello de los {decade}s",
                        x_label="Sello",
                        y_label="Álbumes"
                    )
                    
                    if album_chart:
                        chart_layout.addWidget(album_chart)
        except Exception as e:
            logging.error(f"Error showing labels by decade {decade}: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def handle_table_click(self, table_name, item):
        """Handle clicks on the tables."""
        row = item.row()
        
        if table_name == 'table_time_artists':
            if self.table_time_artists:
                year_item = self.table_time_artists.item(row, 0)
                if year_item:
                    try:
                        year = int(year_item.text())
                        self.show_artists_by_year(year)
                    except ValueError:
                        pass
        
        elif table_name == 'table_time_albums':
            if self.table_time_albums:
                year_item = self.table_time_albums.item(row, 0)
                if year_item:
                    try:
                        year = year_item.text()  # Could be a string like '2022-01'
                        self.show_albums_by_year(year)
                    except ValueError:
                        pass
        
        elif table_name == 'table_time_labels':
            if self.table_time_labels:
                year_item = self.table_time_labels.item(row, 0)
                if year_item:
                    try:
                        year = int(year_item.text())
                        self.show_labels_by_year(year)
                    except ValueError:
                        pass
    
   


    def _verify_ui_components(self):
        """Verify that UI components exist and log their status."""
        
        # Verificar stackedWidget
        if self.stackedWidget_time:
            logging.info(f"stackedWidget_time encontrado con {self.stackedWidget_time.count()} páginas")
            
            # Listar todas las páginas
            for i in range(self.stackedWidget_time.count()):
                page = self.stackedWidget_time.widget(i)
                logging.info(f"  Página {i}: {page.objectName()}")
        else:
            logging.error("stackedWidget_time no encontrado")
        
        # Verificar páginas específicas
        pages = [
            'time_page_inicio', 'time_page_artists', 'time_page_albums',
            'time_page_labels', 'time_page_genres', 'time_page_feeds',
            'time_page_listens', 'time_page_info'
        ]
        for page_name in pages:
            page = getattr(self, page_name, None)
            if page:
                logging.info(f"{page_name} encontrado")
            else:
                logging.warning(f"{page_name} no encontrado")
        
        # Verificar tablas
        tables = [
            'table_time_artists_top', 'table_time_artists_bott',
            'table_time_albums_top', 'table_time_albums_bott',
            'table_time_labels_top', 'table_time_labels_bott',
            'table_time_genres', 'table_time_feeds', 'table_time_listens',
            'table_time_info'
        ]
        for table_name in tables:
            table = getattr(self, table_name, None)
            if table:
                logging.info(f"{table_name} encontrado")
            else:
                logging.warning(f"{table_name} no encontrado")
        
        # Verificar contenedores de gráficos
        charts = [
            'chart_time_artists_top', 'chart_time_artists_bott',
            'chart_time_albums_top', 'chart_time_albums_bott',
            'chart_time_labels_top', 'chart_time_labels_bott',
            'chart_time_genres', 'chart_time_feeds', 'chart_time_listens',
            'chart_time_info'
        ]
        for chart_name in charts:
            chart = getattr(self, chart_name, None)
            if chart:
                logging.info(f"{chart_name} encontrado")
            else:
                logging.warning(f"{chart_name} no encontrado")


    def on_artist_year_selected(self, item):
        """Handle selection of a year in the artists top table."""
        row = item.row()
        if self.table_time_artists_top:
            year_item = self.table_time_artists_top.item(row, 0)
            if year_item:
                try:
                    year = int(year_item.text())
                    self.show_artists_by_year(year)
                except ValueError:
                    pass

    def on_artist_decade_selected(self, item):
        """Handle selection of a decade in the artists bottom table."""
        row = item.row()
        if self.table_time_artists_bott:
            decade_item = self.table_time_artists_bott.item(row, 0)
            if decade_item:
                try:
                    decade = int(decade_item.text().replace('s', ''))
                    self.show_artists_by_decade(decade)
                except ValueError:
                    pass

    def on_album_year_selected(self, item):
        """Handle selection of a year in the albums top table."""
        row = item.row()
        if self.table_time_albums_top:
            year_item = self.table_time_albums_top.item(row, 0)
            if year_item:
                try:
                    year = year_item.text()  # Could be a string like '2022-01'
                    self.show_albums_by_year(year)
                except ValueError:
                    pass

    def on_album_decade_selected(self, item):
        """Handle selection of a decade in the albums bottom table."""
        row = item.row()
        if self.table_time_albums_bott:
            decade_item = self.table_time_albums_bott.item(row, 0)
            if decade_item:
                try:
                    decade = int(decade_item.text().replace('s', ''))
                    self.show_albums_by_decade(decade)
                except ValueError:
                    pass

    def on_label_year_selected(self, item):
        """Handle selection of a year in the labels top table."""
        row = item.row()
        if self.table_time_labels_top:
            year_item = self.table_time_labels_top.item(row, 0)
            if year_item:
                try:
                    year = int(year_item.text())
                    self.show_labels_by_year(year)
                except ValueError:
                    pass

    def on_label_decade_selected(self, item):
        """Handle selection of a decade in the labels bottom table."""
        row = item.row()
        if self.table_time_labels_bott:
            decade_item = self.table_time_labels_bott.item(row, 0)
            if decade_item:
                try:
                    decade = int(decade_item.text().replace('s', ''))
                    self.show_labels_by_decade(decade)
                except ValueError:
                    pass

def load_feeds_time_data(self):
    """Loads temporal statistics about feeds (by year and decade)."""
    if not self.conn:
        return
        
    cursor = self.conn.cursor()
    
    # Create containers for the data
    year_chart_container = self.chart_time_feeds
    table_feeds = self.table_time_feeds
    
    # Clear any existing content
    layout = self.ensure_widget_has_layout(year_chart_container)
    self.clear_layout(layout)
    
    # Configure the table
    if table_feeds:
        table_feeds.setColumnCount(3)
        table_feeds.setHorizontalHeaderLabels(["Año", "Feed", "Publicaciones"])
        table_feeds.setRowCount(0)
    
    try:
        # Query artist formation years data
        cursor.execute("""
            SELECT 
                ar.formed_year as year, 
                COUNT(f.id) as feed_count
            FROM 
                feeds f
            JOIN 
                artists ar ON f.entity_id = ar.id AND f.entity_type = 'artist'
            WHERE 
                ar.formed_year IS NOT NULL AND ar.formed_year > 0
            GROUP BY 
                ar.formed_year
            ORDER BY 
                ar.formed_year;
        """)
        
        artist_year_data = cursor.fetchall()
        
        # Query album release years data
        cursor.execute("""
            SELECT 
                SUBSTR(a.year, 1, 4) as year, 
                COUNT(f.id) as feed_count
            FROM 
                feeds f
            JOIN 
                albums a ON f.entity_id = a.id AND f.entity_type = 'album'
            WHERE 
                a.year IS NOT NULL AND a.year != ''
                AND SUBSTR(a.year, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
            GROUP BY 
                year
            ORDER BY 
                year;
        """)
        
        album_year_data = cursor.fetchall()
        
        # Create a splitter for the two charts
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create container for artist feeds chart
        artist_container = QWidget()
        artist_layout = QVBoxLayout(artist_container)
        artist_title = QLabel("Feeds por Año de Formación de Artistas")
        artist_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        artist_layout.addWidget(artist_title)
        
        # Create container for album feeds chart
        album_container = QWidget()
        album_layout = QVBoxLayout(album_container)
        album_title = QLabel("Feeds por Año de Lanzamiento de Álbumes")
        album_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        album_layout.addWidget(album_title)
        
        # Create and add charts
        if artist_year_data:
            artist_chart = ChartFactory.create_pie_chart(
                artist_year_data,
                "Feeds por Año de Formación"
            )
            if artist_chart:
                artist_layout.addWidget(artist_chart)
        else:
            no_data = QLabel("No hay datos de feeds por año de formación")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("color: gray;")
            artist_layout.addWidget(no_data)
            
        if album_year_data:
            album_chart = ChartFactory.create_pie_chart(
                album_year_data,
                "Feeds por Año de Lanzamiento"
            )
            if album_chart:
                album_layout.addWidget(album_chart)
        else:
            no_data = QLabel("No hay datos de feeds por año de lanzamiento")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("color: gray;")
            album_layout.addWidget(no_data)
            
        # Add containers to splitter
        splitter.addWidget(artist_container)
        splitter.addWidget(album_container)
        
        # Add splitter to main layout
        layout.addWidget(splitter)
        
        # Fill the table with combined year data
        if table_feeds:
            # Combine the data from both sources
            year_data = {}
            
            # Process artist data
            for year, count in artist_year_data:
                if year not in year_data:
                    year_data[year] = {"artist": 0, "album": 0}
                year_data[year]["artist"] = count
            
            # Process album data
            for year, count in album_year_data:
                if year not in year_data:
                    year_data[year] = {"artist": 0, "album": 0}
                year_data[year]["album"] = count
            
            # Fill the table
            table_feeds.setRowCount(len(year_data) * 2)  # Two rows per year (artist and album)
            row_index = 0
            
            for year, counts in sorted(year_data.items()):
                if counts["artist"] > 0:
                    table_feeds.setItem(row_index, 0, QTableWidgetItem(str(year)))
                    table_feeds.setItem(row_index, 1, QTableWidgetItem("Artistas"))
                    table_feeds.setItem(row_index, 2, QTableWidgetItem(str(counts["artist"])))
                    row_index += 1
                
                if counts["album"] > 0:
                    table_feeds.setItem(row_index, 0, QTableWidgetItem(str(year)))
                    table_feeds.setItem(row_index, 1, QTableWidgetItem("Álbumes"))
                    table_feeds.setItem(row_index, 2, QTableWidgetItem(str(counts["album"])))
                    row_index += 1
            
            # Adjust row count if needed
            if row_index < table_feeds.rowCount():
                table_feeds.setRowCount(row_index)
            
            # Resize columns
            table_feeds.resizeColumnsToContents()
            
            # Connect table selection
            try:
                table_feeds.itemClicked.disconnect()
            except:
                pass
            table_feeds.itemClicked.connect(self.on_feed_year_selected)
        
        # Now load the decade data
        self.load_feeds_decade_data()
        
    except Exception as e:
        logging.error(f"Error loading feed time data: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        error_label = QLabel(f"Error cargando datos de feeds por tiempo: {str(e)}")
        error_label.setStyleSheet("color: red;")
        layout.addWidget(error_label)

def load_feeds_decade_data(self):
    """Loads decade-based feed statistics."""
    if not self.conn:
        return
        
    cursor = self.conn.cursor()
    
    # Define the containers
    chart_container = self.chart_time_feeds_bott
    table_feeds_bott = self.table_time_feeds_bott
    
    # Clear any existing content
    layout = self.ensure_widget_has_layout(chart_container)
    self.clear_layout(layout)
    
    # Configure the table
    if table_feeds_bott:
        table_feeds_bott.setColumnCount(3)
        table_feeds_bott.setHorizontalHeaderLabels(["Década", "Feed", "Publicaciones"])
        table_feeds_bott.setRowCount(0)
    
    try:
        # Query artist formation decades data
        cursor.execute("""
            SELECT 
                (formed_year / 10) * 10 as decade, 
                COUNT(f.id) as feed_count
            FROM 
                feeds f
            JOIN 
                artists ar ON f.entity_id = ar.id AND f.entity_type = 'artist'
            WHERE 
                ar.formed_year IS NOT NULL AND ar.formed_year > 0
            GROUP BY 
                decade
            ORDER BY 
                decade;
        """)
        
        artist_decade_data = cursor.fetchall()
        
        # Query album release decades data
        cursor.execute("""
            SELECT 
                (CAST(SUBSTR(a.year, 1, 4) AS INTEGER) / 10) * 10 as decade, 
                COUNT(f.id) as feed_count
            FROM 
                feeds f
            JOIN 
                albums a ON f.entity_id = a.id AND f.entity_type = 'album'
            WHERE 
                a.year IS NOT NULL AND a.year != ''
                AND SUBSTR(a.year, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
            GROUP BY 
                decade
            ORDER BY 
                decade;
        """)
        
        album_decade_data = cursor.fetchall()
        
        # Create a splitter for the two charts
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create container for artist feeds chart
        artist_container = QWidget()
        artist_layout = QVBoxLayout(artist_container)
        artist_title = QLabel("Feeds por Década de Formación de Artistas")
        artist_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        artist_layout.addWidget(artist_title)
        
        # Create container for album feeds chart
        album_container = QWidget()
        album_layout = QVBoxLayout(album_container)
        album_title = QLabel("Feeds por Década de Lanzamiento de Álbumes")
        album_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        album_layout.addWidget(album_title)
        
        # Prepare data for charts
        artist_chart_data = [(f"{decade}s", count) for decade, count in artist_decade_data]
        album_chart_data = [(f"{decade}s", count) for decade, count in album_decade_data]
        
        # Create and add charts
        if artist_chart_data:
            artist_chart = ChartFactory.create_pie_chart(
                artist_chart_data,
                "Feeds por Década de Formación"
            )
            if artist_chart:
                artist_layout.addWidget(artist_chart)
        else:
            no_data = QLabel("No hay datos de feeds por década de formación")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("color: gray;")
            artist_layout.addWidget(no_data)
            
        if album_chart_data:
            album_chart = ChartFactory.create_pie_chart(
                album_chart_data,
                "Feeds por Década de Lanzamiento"
            )
            if album_chart:
                album_layout.addWidget(album_chart)
        else:
            no_data = QLabel("No hay datos de feeds por década de lanzamiento")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("color: gray;")
            album_layout.addWidget(no_data)
            
        # Add containers to splitter
        splitter.addWidget(artist_container)
        splitter.addWidget(album_container)
        
        # Add splitter to main layout
        layout.addWidget(splitter)
        
        # Fill the table with combined decade data
        if table_feeds_bott:
            # Combine the data from both sources
            decade_data = {}
            
            # Process artist data
            for decade, count in artist_decade_data:
                decade_str = f"{decade}s"
                if decade_str not in decade_data:
                    decade_data[decade_str] = {"artist": 0, "album": 0}
                decade_data[decade_str]["artist"] = count
            
            # Process album data
            for decade, count in album_decade_data:
                decade_str = f"{decade}s"
                if decade_str not in decade_data:
                    decade_data[decade_str] = {"artist": 0, "album": 0}
                decade_data[decade_str]["album"] = count
            
            # Fill the table
            table_feeds_bott.setRowCount(len(decade_data) * 2)  # Two rows per decade (artist and album)
            row_index = 0
            
            for decade, counts in sorted(decade_data.items()):
                if counts["artist"] > 0:
                    table_feeds_bott.setItem(row_index, 0, QTableWidgetItem(decade))
                    table_feeds_bott.setItem(row_index, 1, QTableWidgetItem("Artistas"))
                    table_feeds_bott.setItem(row_index, 2, QTableWidgetItem(str(counts["artist"])))
                    row_index += 1
                
                if counts["album"] > 0:
                    table_feeds_bott.setItem(row_index, 0, QTableWidgetItem(decade))
                    table_feeds_bott.setItem(row_index, 1, QTableWidgetItem("Álbumes"))
                    table_feeds_bott.setItem(row_index, 2, QTableWidgetItem(str(counts["album"])))
                    row_index += 1
            
            # Adjust row count if needed
            if row_index < table_feeds_bott.rowCount():
                table_feeds_bott.setRowCount(row_index)
            
            # Resize columns
            table_feeds_bott.resizeColumnsToContents()
            
            # Connect table selection
            try:
                table_feeds_bott.itemClicked.disconnect()
            except:
                pass
            table_feeds_bott.itemClicked.connect(self.on_feed_decade_selected)
            
    except Exception as e:
        logging.error(f"Error loading feed decade data: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        error_label = QLabel(f"Error cargando datos de feeds por década: {str(e)}")
        error_label.setStyleSheet("color: red;")
        layout.addWidget(error_label)

def on_feed_year_selected(self, item):
    """Handle selection of a year in the feeds table."""
    row = item.row()
    if self.table_time_feeds:
        year_item = self.table_time_feeds.item(row, 0)
        feed_type_item = self.table_time_feeds.item(row, 1)
        
        if year_item and feed_type_item:
            try:
                year = year_item.text()
                feed_type = feed_type_item.text()
                self.show_feeds_by_year(year, feed_type)
            except Exception as e:
                logging.error(f"Error handling feed year selection: {e}")
                import traceback
                logging.error(traceback.format_exc())

def on_feed_decade_selected(self, item):
    """Handle selection of a decade in the feeds decade table."""
    row = item.row()
    if self.table_time_feeds_bott:
        decade_item = self.table_time_feeds_bott.item(row, 0)
        feed_type_item = self.table_time_feeds_bott.item(row, 1)
        
        if decade_item and feed_type_item:
            try:
                decade = decade_item.text().replace('s', '')  # Remove 's' from '1990s'
                feed_type = feed_type_item.text()
                self.show_feeds_by_decade(decade, feed_type)
            except Exception as e:
                logging.error(f"Error handling feed decade selection: {e}")
                import traceback
                logging.error(traceback.format_exc())

def show_feeds_by_year(self, year, feed_type):
    """Show feeds detail for a specific year."""
    if not self.conn:
        return
        
    # Get the chart container for displaying year details
    chart_container = self.chart_time_feeds
    
    # Ensure it has a layout
    layout = self.ensure_widget_has_layout(chart_container)
    
    # Clear the container
    self.clear_layout(layout)
    
    cursor = self.conn.cursor()
    try:
        # Different query based on feed type
        if feed_type == "Artistas":
            # Get feeds for artists formed in the specified year
            cursor.execute("""
                SELECT 
                    ar.name as entity_name, 
                    f.feed_name,
                    COUNT(f.id) as feed_count
                FROM 
                    feeds f
                JOIN 
                    artists ar ON f.entity_id = ar.id AND f.entity_type = 'artist'
                WHERE 
                    ar.formed_year = ?
                GROUP BY 
                    entity_name, f.feed_name
                ORDER BY 
                    feed_count DESC;
            """, (year,))
        else:  # "Álbumes"
            # Get feeds for albums released in the specified year
            cursor.execute("""
                SELECT 
                    a.name as entity_name, 
                    f.feed_name,
                    COUNT(f.id) as feed_count
                FROM 
                    feeds f
                JOIN 
                    albums a ON f.entity_id = a.id AND f.entity_type = 'album'
                WHERE 
                    SUBSTR(a.year, 1, 4) = ?
                GROUP BY 
                    entity_name, f.feed_name
                ORDER BY 
                    feed_count DESC;
            """, (year,))
        
        results = cursor.fetchall()
        
        # Create charts based on results
        if results:
            # Title for the section
            title = QLabel(f"Feeds de {feed_type} del año {year}")
            title.setStyleSheet("font-weight: bold; font-size: 16px;")
            layout.addWidget(title)
            
            # Create splitter for entity and feed charts
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Entity chart container
            entity_container = QWidget()
            entity_layout = QVBoxLayout(entity_container)
            entity_title = QLabel(f"{feed_type} con más feeds")
            entity_title.setStyleSheet("font-weight: bold;")
            entity_layout.addWidget(entity_title)
            
            # Feed chart container
            feed_container = QWidget()
            feed_layout = QVBoxLayout(feed_container)
            feed_title = QLabel("Distribución por feed")
            feed_title.setStyleSheet("font-weight: bold;")
            feed_layout.addWidget(feed_title)
            
            # Aggregate data for charts
            entity_data = {}
            feed_data = {}
            
            for entity, feed_name, count in results:
                # Aggregate for entity chart
                if entity in entity_data:
                    entity_data[entity] += count
                else:
                    entity_data[entity] = count
                
                # Aggregate for feed chart
                if feed_name in feed_data:
                    feed_data[feed_name] += count
                else:
                    feed_data[feed_name] = count
            
            # Convert to list of tuples for charts
            entity_chart_data = sorted([(entity, count) for entity, count in entity_data.items()], key=lambda x: x[1], reverse=True)
            feed_chart_data = sorted([(feed, count) for feed, count in feed_data.items()], key=lambda x: x[1], reverse=True)
            
            # Create and add entity chart
            if entity_chart_data:
                # Limit to top 15 for better visualization
                chart_data = entity_chart_data[:15] if len(entity_chart_data) > 15 else entity_chart_data
                entity_chart = ChartFactory.create_pie_chart(
                    chart_data,
                    f"{feed_type} con más feeds en {year}"
                )
                if entity_chart:
                    entity_layout.addWidget(entity_chart)
            else:
                no_data = QLabel(f"No hay datos de {feed_type.lower()} para el año {year}")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray;")
                entity_layout.addWidget(no_data)
            
            # Create and add feed chart
            if feed_chart_data:
                # Limit to top 15 for better visualization
                chart_data = feed_chart_data[:15] if len(feed_chart_data) > 15 else feed_chart_data
                feed_chart = ChartFactory.create_pie_chart(
                    chart_data,
                    f"Feeds para {feed_type.lower()} de {year}"
                )
                if feed_chart:
                    feed_layout.addWidget(feed_chart)
            else:
                no_data = QLabel(f"No hay datos de feeds para {feed_type.lower()} del año {year}")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray;")
                feed_layout.addWidget(no_data)
            
            # Add containers to splitter
            splitter.addWidget(entity_container)
            splitter.addWidget(feed_container)
            
            # Add splitter to main layout
            layout.addWidget(splitter)
            
        else:
            no_data = QLabel(f"No hay datos de feeds para {feed_type.lower()} del año {year}")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("color: gray; font-size: 14px;")
            layout.addWidget(no_data)
            
    except Exception as e:
        logging.error(f"Error showing feeds by year: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        error_label = QLabel(f"Error: {str(e)}")
        error_label.setStyleSheet("color: red;")
        layout.addWidget(error_label)

def show_feeds_by_decade(self, decade, feed_type):
    """Show feeds detail for a specific decade."""
    if not self.conn:
        return
        
    # Get the chart container for displaying decade details
    chart_container = self.chart_time_feeds_bott
    
    # Ensure it has a layout
    layout = self.ensure_widget_has_layout(chart_container)
    
    # Clear the container
    self.clear_layout(layout)
    
    cursor = self.conn.cursor()
    try:
        # Convert decade to integer for calculations
        decade_int = int(decade)
        decade_start = decade_int
        decade_end = decade_int + 9
        
        # Different query based on feed type
        if feed_type == "Artistas":
            # Get feeds for artists formed in the specified decade
            cursor.execute("""
                SELECT 
                    ar.name as entity_name, 
                    f.feed_name,
                    COUNT(f.id) as feed_count
                FROM 
                    feeds f
                JOIN 
                    artists ar ON f.entity_id = ar.id AND f.entity_type = 'artist'
                WHERE 
                    ar.formed_year >= ? AND ar.formed_year <= ?
                GROUP BY 
                    entity_name, f.feed_name
                ORDER BY 
                    feed_count DESC;
            """, (decade_start, decade_end))
        else:  # "Álbumes"
            # Get feeds for albums released in the specified decade
            cursor.execute("""
                SELECT 
                    a.name as entity_name, 
                    f.feed_name,
                    COUNT(f.id) as feed_count
                FROM 
                    feeds f
                JOIN 
                    albums a ON f.entity_id = a.id AND f.entity_type = 'album'
                WHERE 
                    CAST(SUBSTR(a.year, 1, 4) AS INTEGER) >= ? 
                    AND CAST(SUBSTR(a.year, 1, 4) AS INTEGER) <= ?
                GROUP BY 
                    entity_name, f.feed_name
                ORDER BY 
                    feed_count DESC;
            """, (decade_start, decade_end))
        
        results = cursor.fetchall()
        
        # Create charts based on results
        if results:
            # Title for the section
            title = QLabel(f"Feeds de {feed_type} de la década {decade}s")
            title.setStyleSheet("font-weight: bold; font-size: 16px;")
            layout.addWidget(title)
            
            # Create splitter for entity and feed charts
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Entity chart container
            entity_container = QWidget()
            entity_layout = QVBoxLayout(entity_container)
            entity_title = QLabel(f"{feed_type} con más feeds")
            entity_title.setStyleSheet("font-weight: bold;")
            entity_layout.addWidget(entity_title)
            
            # Feed chart container
            feed_container = QWidget()
            feed_layout = QVBoxLayout(feed_container)
            feed_title = QLabel("Distribución por feed")
            feed_title.setStyleSheet("font-weight: bold;")
            feed_layout.addWidget(feed_title)
            
            # Aggregate data for charts
            entity_data = {}
            feed_data = {}
            
            for entity, feed_name, count in results:
                # Aggregate for entity chart
                if entity in entity_data:
                    entity_data[entity] += count
                else:
                    entity_data[entity] = count
                
                # Aggregate for feed chart
                if feed_name in feed_data:
                    feed_data[feed_name] += count
                else:
                    feed_data[feed_name] = count
            
            # Convert to list of tuples for charts
            entity_chart_data = sorted([(entity, count) for entity, count in entity_data.items()], key=lambda x: x[1], reverse=True)
            feed_chart_data = sorted([(feed, count) for feed, count in feed_data.items()], key=lambda x: x[1], reverse=True)
            
            # Create and add entity chart
            if entity_chart_data:
                # Limit to top 15 for better visualization
                chart_data = entity_chart_data[:15] if len(entity_chart_data) > 15 else entity_chart_data
                entity_chart = ChartFactory.create_pie_chart(
                    chart_data,
                    f"{feed_type} con más feeds en {decade}s"
                )
                if entity_chart:
                    entity_layout.addWidget(entity_chart)
            else:
                no_data = QLabel(f"No hay datos de {feed_type.lower()} para la década {decade}s")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray;")
                entity_layout.addWidget(no_data)
            
            # Create and add feed chart
            if feed_chart_data:
                # Limit to top 15 for better visualization
                chart_data = feed_chart_data[:15] if len(feed_chart_data) > 15 else feed_chart_data
                feed_chart = ChartFactory.create_pie_chart(
                    chart_data,
                    f"Feeds para {feed_type.lower()} de {decade}s"
                )
                if feed_chart:
                    feed_layout.addWidget(feed_chart)
            else:
                no_data = QLabel(f"No hay datos de feeds para {feed_type.lower()} de la década {decade}s")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray;")
                feed_layout.addWidget(no_data)
            
            # Add containers to splitter
            splitter.addWidget(entity_container)
            splitter.addWidget(feed_container)
            
            # Add splitter to main layout
            layout.addWidget(splitter)
            
        else:
            no_data = QLabel(f"No hay datos de feeds para {feed_type.lower()} de la década {decade}s")
            no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data.setStyleSheet("color: gray; font-size: 14px;")
            layout.addWidget(no_data)
            
    except Exception as e:
        logging.error(f"Error showing feeds by decade: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        error_label = QLabel(f"Error: {str(e)}")
        error_label.setStyleSheet("color: red;")
        layout.addWidget(error_label)


    def load_genre_time_data(self):
        """Loads temporal statistics about genre distribution (by year and decade)."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        # Create containers for the data
        year_chart_container = self.chart_time_genres
        table_genres = self.table_time_genres
        
        # Clear any existing content
        layout = self.ensure_widget_has_layout(year_chart_container)
        self.clear_layout(layout)
        
        # Configure the table
        if table_genres:
            table_genres.setColumnCount(3)
            table_genres.setHorizontalHeaderLabels(["Año", "Género", "Canciones"])
            table_genres.setRowCount(0)
        
        try:
            # Query genre distribution by year (limit to recent 20 years for visualization)
            cursor.execute("""
                SELECT 
                    SUBSTR(a.year, 1, 4) as year,
                    s.genre,
                    COUNT(*) as song_count
                FROM 
                    songs s
                JOIN 
                    albums a ON s.album = a.name
                WHERE 
                    s.genre IS NOT NULL 
                    AND s.genre != ''
                    AND a.year IS NOT NULL 
                    AND a.year != ''
                    AND SUBSTR(a.year, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
                GROUP BY 
                    year, s.genre
                ORDER BY 
                    year DESC, song_count DESC;
            """)
            
            year_genre_data = cursor.fetchall()
            
            # Process data for visualization
            years_data = {}
            all_years = set()
            all_genres = {}
            
            for year, genre, count in year_genre_data:
                all_years.add(year)
                if year not in years_data:
                    years_data[year] = {}
                years_data[year][genre] = count
                
                # Track total counts for each genre
                if genre in all_genres:
                    all_genres[genre] += count
                else:
                    all_genres[genre] = count
            
            # Get top genres by total count
            top_genres = sorted(all_genres.items(), key=lambda x: x[1], reverse=True)[:5]
            top_genre_names = [genre for genre, _ in top_genres]
            
            # Get years in order (limiting to most recent 15)
            sorted_years = sorted(list(all_years), reverse=True)[:15]
            sorted_years.reverse()  # Put in ascending order for chart
            
            # Prepare data for stacked bar chart
            # For each year, get counts for top genres
            year_data_for_chart = []
            for year in sorted_years:
                year_counts = []
                for genre in top_genre_names:
                    count = years_data.get(year, {}).get(genre, 0)
                    year_counts.append((genre, count))
                year_data_for_chart.append((year, year_counts))
            
            # Create custom chart here - we'll use a series of bars for each year
            # Since we can't do stacked bars directly, we'll create a custom layout
            
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
            chart_widget = QWidget()
            chart_layout = QHBoxLayout(chart_widget)
            chart_layout.setSpacing(10)
            
            # Create a color map for genres
            colors = ChartFactory.CHART_COLORS
            genre_colors = {}
            for i, genre in enumerate(top_genre_names):
                genre_colors[genre] = colors[i % len(colors)]
            
            # Create a bar for each year with segments for each genre
            for year, genre_counts in year_data_for_chart:
                year_widget = QWidget()
                year_layout = QVBoxLayout(year_widget)
                year_layout.setSpacing(0)
                year_layout.setContentsMargins(0, 0, 0, 0)
                
                # Year label at bottom
                year_label = QLabel(year)
                year_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Create bars for each genre
                bars_widget = QWidget()
                bars_layout = QVBoxLayout(bars_widget)
                bars_layout.setSpacing(0)
                bars_layout.setContentsMargins(0, 0, 0, 0)
                
                # Calculate total height
                total_count = sum(count for _, count in genre_counts)
                max_height = 300  # Maximum bar height in pixels
                
                # Create segments for each genre in reverse order (bottom to top)
                for genre, count in reversed(genre_counts):
                    if count > 0:
                        # Calculate segment height proportional to count
                        segment_height = int((count / total_count) * max_height)
                        
                        # Create a colored segment for this genre
                        segment = QFrame()
                        segment.setFixedSize(30, segment_height)
                        segment.setStyleSheet(f"background-color: {genre_colors.get(genre, '#cccccc')};")
                        
                        # Add a small tooltip
                        segment.setToolTip(f"{genre}: {count} canciones")
                        
                        # Add to layout
                        bars_layout.addWidget(segment)
                        
                        # Also add a bit of margin if not the last segment
                        if genre != genre_counts[-1][0]:
                            spacer = QFrame()
                            spacer.setFixedSize(30, 1)
                            spacer.setStyleSheet("background-color: #ffffff;")
                            bars_layout.addWidget(spacer)
                
                # Add spacer to push bars to the bottom
                bars_layout.addStretch()
                
                # Add to year layout
                year_layout.addWidget(bars_widget)
                year_layout.addWidget(year_label)
                
                # Make the year widget clickable
                year_widget.mousePressEvent = lambda event, y=year: self.show_genres_by_year(y)
                
                # Add to chart layout
                chart_layout.addWidget(year_widget)
            
            # Add legend
            legend_widget = QWidget()
            legend_layout = QVBoxLayout(legend_widget)
            legend_layout.setSpacing(5)
            
            legend_title = QLabel("Géneros:")
            legend_title.setStyleSheet("font-weight: bold;")
            legend_layout.addWidget(legend_title)
            
            for genre, _ in top_genres:
                genre_item = QWidget()
                genre_item_layout = QHBoxLayout(genre_item)
                genre_item_layout.setSpacing(5)
                genre_item_layout.setContentsMargins(0, 0, 0, 0)
                
                color_box = QFrame()
                color_box.setFixedSize(15, 15)
                color_box.setStyleSheet(f"background-color: {genre_colors.get(genre, '#cccccc')};")
                
                genre_label = QLabel(genre)
                
                genre_item_layout.addWidget(color_box)
                genre_item_layout.addWidget(genre_label)
                
                legend_layout.addWidget(genre_item)
            
            legend_layout.addStretch()
            
            # Add to main layout with appropriate spacing
            splitter = QSplitter(Qt.Orientation.Horizontal)
            splitter.addWidget(chart_widget)
            splitter.addWidget(legend_widget)
            splitter.setSizes([700, 200])  # Adjust based on your UI
            
            scroll_area.setWidget(splitter)
            layout.addWidget(scroll_area)
            
            # Fill the table with genre data by year
            if table_genres and year_genre_data:
                table_genres.setRowCount(len(year_genre_data))
                
                for i, (year, genre, count) in enumerate(year_genre_data):
                    table_genres.setItem(i, 0, QTableWidgetItem(year))
                    table_genres.setItem(i, 1, QTableWidgetItem(genre))
                    table_genres.setItem(i, 2, QTableWidgetItem(str(count)))
                
                # Resize columns
                table_genres.resizeColumnsToContents()
                
                # Connect table selection
                try:
                    table_genres.itemClicked.disconnect()
                except:
                    pass
                table_genres.itemClicked.connect(self.on_genre_year_selected)
            
            # Now load the decade data
            self.load_genre_decade_data()
            
        except Exception as e:
            logging.error(f"Error loading genre time data: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
            error_label = QLabel(f"Error cargando datos de géneros por tiempo: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)

    def get_top_genres(self, limit=5):
        """Get the top N genres by total song count."""
        if not self.conn:
            return []
            
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                genre, 
                COUNT(*) as song_count
            FROM 
                songs
            WHERE 
                genre IS NOT NULL 
                AND genre != ''
            GROUP BY 
                genre
            ORDER BY 
                song_count DESC
            LIMIT ?;
        """, (limit,))
        
        return cursor.fetchall()

    def load_genre_decade_data(self):
        """Loads decade-based genre statistics."""
        if not self.conn:
            return
            
        cursor = self.conn.cursor()
        
        # Define the containers
        chart_container = self.chart_time_genres_bott
        
        # Clear any existing content
        layout = self.ensure_widget_has_layout(chart_container)
        self.clear_layout(layout)
        
        try:
            # Query genre distribution by decade
            cursor.execute("""
                SELECT 
                    (CAST(SUBSTR(a.year, 1, 4) AS INTEGER) / 10) * 10 as decade,
                    s.genre,
                    COUNT(*) as song_count
                FROM 
                    songs s
                JOIN 
                    albums a ON s.album = a.name
                WHERE 
                    s.genre IS NOT NULL 
                    AND s.genre != ''
                    AND a.year IS NOT NULL 
                    AND a.year != ''
                    AND SUBSTR(a.year, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
                GROUP BY 
                    decade, s.genre
                ORDER BY 
                    decade, song_count DESC;
            """)
            
            decade_genre_data = cursor.fetchall()
            
            # Process data for visualization
            decades_data = {}
            all_decades = set()
            all_genres = {}
            
            for decade, genre, count in decade_genre_data:
                decade_str = f"{decade}s"
                all_decades.add(decade_str)
                if decade_str not in decades_data:
                    decades_data[decade_str] = {}
                decades_data[decade_str][genre] = count
                
                # Track total counts for each genre
                if genre in all_genres:
                    all_genres[genre] += count
                else:
                    all_genres[genre] = count
            
            # Get top genres by total count
            top_genres = sorted(all_genres.items(), key=lambda x: x[1], reverse=True)[:5]
            top_genre_names = [genre for genre, _ in top_genres]
            
            # Get decades in order
            sorted_decades = sorted(list(all_decades))
            
            # Create title
            title = QLabel("Distribución de Géneros por Década")
            title.setStyleSheet("font-weight: bold; font-size: 16px;")
            layout.addWidget(title)
            
            # Create custom chart widget similar to year chart
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
            chart_widget = QWidget()
            chart_layout = QHBoxLayout(chart_widget)
            chart_layout.setSpacing(10)
            
            # Create a color map for genres
            colors = ChartFactory.CHART_COLORS
            genre_colors = {}
            for i, genre in enumerate(top_genre_names):
                genre_colors[genre] = colors[i % len(colors)]
            
            # Create a bar for each decade with segments for each genre
            for decade in sorted_decades:
                genre_counts = []
                for genre in top_genre_names:
                    count = decades_data.get(decade, {}).get(genre, 0)
                    genre_counts.append((genre, count))
                
                decade_widget = QWidget()
                decade_layout = QVBoxLayout(decade_widget)
                decade_layout.setSpacing(0)
                decade_layout.setContentsMargins(0, 0, 0, 0)
                
                # Decade label at bottom
                decade_label = QLabel(decade)
                decade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Create bars for each genre
                bars_widget = QWidget()
                bars_layout = QVBoxLayout(bars_widget)
                bars_layout.setSpacing(0)
                bars_layout.setContentsMargins(0, 0, 0, 0)
                
                # Calculate total height
                total_count = sum(count for _, count in genre_counts)
                max_height = 300  # Maximum bar height in pixels
                
                # Create segments for each genre in reverse order (bottom to top)
                for genre, count in reversed(genre_counts):
                    if count > 0:
                        # Calculate segment height proportional to count
                        segment_height = int((count / total_count) * max_height)
                        
                        # Create a colored segment for this genre
                        segment = QFrame()
                        segment.setFixedSize(40, segment_height)
                        segment.setStyleSheet(f"background-color: {genre_colors.get(genre, '#cccccc')};")
                        
                        # Add a small tooltip
                        segment.setToolTip(f"{genre}: {count} canciones")
                        
                        # Add to layout
                        bars_layout.addWidget(segment)
                        
                        # Also add a bit of margin if not the last segment
                        if genre != genre_counts[-1][0]:
                            spacer = QFrame()
                            spacer.setFixedSize(40, 1)
                            spacer.setStyleSheet("background-color: #ffffff;")
                            bars_layout.addWidget(spacer)
                
                # Add spacer to push bars to the bottom
                bars_layout.addStretch()
                
                # Add to decade layout
                decade_layout.addWidget(bars_widget)
                decade_layout.addWidget(decade_label)
                
                # Make the decade widget clickable
                decade_widget.mousePressEvent = lambda event, d=decade: self.show_genres_by_decade(d.replace('s', ''))
                
                # Add to chart layout
                chart_layout.addWidget(decade_widget)
            
            # Add legend
            legend_widget = QWidget()
            legend_layout = QVBoxLayout(legend_widget)
            legend_layout.setSpacing(5)
            
            legend_title = QLabel("Géneros:")
            legend_title.setStyleSheet("font-weight: bold;")
            legend_layout.addWidget(legend_title)
            
            for genre, _ in top_genres:
                genre_item = QWidget()
                genre_item_layout = QHBoxLayout(genre_item)
                genre_item_layout.setSpacing(5)
                genre_item_layout.setContentsMargins(0, 0, 0, 0)
                
                color_box = QFrame()
                color_box.setFixedSize(15, 15)
                color_box.setStyleSheet(f"background-color: {genre_colors.get(genre, '#cccccc')};")
                
                genre_label = QLabel(genre)
                
                genre_item_layout.addWidget(color_box)
                genre_item_layout.addWidget(genre_label)
                
                legend_layout.addWidget(genre_item)
            
            legend_layout.addStretch()
            
            # Add to main layout with appropriate spacing
            splitter = QSplitter(Qt.Orientation.Horizontal)
            splitter.addWidget(chart_widget)
            splitter.addWidget(legend_widget)
            splitter.setSizes([700, 200])  # Adjust based on your UI
            
            scroll_area.setWidget(splitter)
            layout.addWidget(scroll_area)
            
        except Exception as e:
            logging.error(f"Error loading genre decade data: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
            error_label = QLabel(f"Error cargando datos de géneros por década: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)

    def on_genre_year_selected(self, item):
        """Handle selection of a year in the genre table."""
        row = item.row()
        if self.table_time_genres:
            year_item = self.table_time_genres.item(row, 0)
            
            if year_item:
                try:
                    year = year_item.text()
                    self.show_genres_by_year(year)
                except Exception as e:
                    logging.error(f"Error handling genre year selection: {e}")
                    import traceback
                    logging.error(traceback.format_exc())

    def show_genres_by_year(self, year):
        """Show genre distribution for a specific year."""
        if not self.conn:
            return
            
        # Get the chart container
        chart_container = self.chart_time_genres
        
        # Ensure it has a layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Clear the container
        self.clear_layout(layout)
        
        cursor = self.conn.cursor()
        try:
            # Query for genres in the specified year
            cursor.execute("""
                SELECT 
                    s.genre, 
                    COUNT(*) as song_count
                FROM 
                    songs s
                JOIN 
                    albums a ON s.album = a.name
                WHERE 
                    SUBSTR(a.year, 1, 4) = ?
                    AND s.genre IS NOT NULL 
                    AND s.genre != ''
                GROUP BY 
                    s.genre
                ORDER BY 
                    song_count DESC;
            """, (year,))
            
            results = cursor.fetchall()
            
            if results:
                # Title for the chart
                title = QLabel(f"Distribución de Géneros en {year}")
                title.setStyleSheet("font-weight: bold; font-size: 16px;")
                layout.addWidget(title)
                
                # Create pie chart
                chart_view = ChartFactory.create_pie_chart(
                    results,
                    f"Géneros en {year}"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info(f"Chart for genres in year {year} created successfully")
                else:
                    error_label = QLabel("No se pudo crear el gráfico")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
            else:
                no_data = QLabel(f"No hay datos de géneros para el año {year}")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error showing genres by year: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)

    def show_genres_by_decade(self, decade):
        """Show genre distribution for a specific decade."""
        if not self.conn:
            return
            
        # Get the chart container
        chart_container = self.chart_time_genres_bott
        
        # Ensure it has a layout
        layout = self.ensure_widget_has_layout(chart_container)
        
        # Clear the container
        self.clear_layout(layout)
        
        cursor = self.conn.cursor()
        try:
            # Convert decade to integer
            decade_int = int(decade)
            decade_start = decade_int
            decade_end = decade_int + 9
            
            # Query for genres in the specified decade
            cursor.execute("""
                SELECT 
                    s.genre, 
                    COUNT(*) as song_count
                FROM 
                    songs s
                JOIN 
                    albums a ON s.album = a.name
                WHERE 
                    CAST(SUBSTR(a.year, 1, 4) AS INTEGER) >= ? 
                    AND CAST(SUBSTR(a.year, 1, 4) AS INTEGER) <= ?
                    AND s.genre IS NOT NULL 
                    AND s.genre != ''
                GROUP BY 
                    s.genre
                ORDER BY 
                    song_count DESC;
            """, (decade_start, decade_end))
            
            results = cursor.fetchall()
            
            if results:
                # Title for the chart
                title = QLabel(f"Distribución de Géneros en los {decade}s")
                title.setStyleSheet("font-weight: bold; font-size: 16px;")
                layout.addWidget(title)
                
                # Create pie chart
                chart_view = ChartFactory.create_pie_chart(
                    results,
                    f"Géneros en los {decade}s"
                )
                
                if chart_view:
                    layout.addWidget(chart_view)
                    logging.info(f"Chart for genres in decade {decade}s created successfully")
                else:
                    error_label = QLabel("No se pudo crear el gráfico")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)
            else:
                no_data = QLabel(f"No hay datos de géneros para la década {decade}s")
                no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data.setStyleSheet("color: gray; font-size: 14px;")
                layout.addWidget(no_data)
                
        except Exception as e:
            logging.error(f"Error showing genres by decade: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)