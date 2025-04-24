from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt
import logging
import sqlite3

import sys
import os

# Adjust the path to ensure we can import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tools.chart_utils import ChartFactory

class FeedsSubmodule:
    """Handles the feeds-related operations for the stats module."""
    def __init__(self, parent=None, db_connection=None, helper_functions=None):
        """
        Initialize the feeds submodule.
        
        Args:
            parent: The parent widget/module (usually StatsModule)
            db_connection: SQLite connection to the database
            helper_functions: Dict of helper functions from the parent module
        """
        self.parent = parent
        self.conn = db_connection
        self.helper_functions = helper_functions or {}
        
        # Initialize references to UI elements directly from parent
        self.init_ui_references()
        
    def init_ui_references(self):
        """Initialize references to UI elements from the parent module."""
        if not self.parent:
            logging.error("No parent module provided to FeedsSubmodule")
            return
            
        # Reference to stackedWidget directly through parent's attribute
        self.stacked_widget = self.parent.stackedWidget_2 if hasattr(self.parent, 'stackedWidget_2') else None
        
        # Get button references directly from parent
        self.btn_artists = self.parent.feeds_button_artists if hasattr(self.parent, 'feeds_button_artists') else None
        self.btn_albums = self.parent.feeds_button_albums if hasattr(self.parent, 'feeds_button_albums') else None
        self.btn_labels = self.parent.feeds_button_labels if hasattr(self.parent, 'feeds_button_labels') else None
        self.btn_genres = self.parent.feeds_button_genres if hasattr(self.parent, 'feeds_button_genres') else None
        self.btn_time = self.parent.feeds_button_time if hasattr(self.parent, 'feeds_button_time') else None
        self.btn_listens = self.parent.feeds_button_listens if hasattr(self.parent, 'feeds_button_listens') else None
        self.btn_info = self.parent.feeds_button_info if hasattr(self.parent, 'feeds_button_info') else None
        
        # Get widget containers directly from parent
        self.chart_container_entity = self.parent.chart_container_entity if hasattr(self.parent, 'chart_container_entity') else None
        self.chart_container_feeds = self.parent.chart_container_feeds if hasattr(self.parent, 'chart_container_feeds') else None
        
        # Get table widgets directly from parent
        self.table_entity = self.parent.table_entity if hasattr(self.parent, 'table_entity') else None
        self.table_feeds = self.parent.table_feeds if hasattr(self.parent, 'table_feeds') else None
        
        # Direct references to specific page widgets (add more as needed)
        self.table_feeds_artists = self.parent.table_feeds_artists if hasattr(self.parent, 'table_feeds_artists') else None
        self.table_feeds_albums = self.parent.table_feeds_albums if hasattr(self.parent, 'table_feeds_albums') else None
        self.table_feeds_genres = self.parent.table_feeds_genres if hasattr(self.parent, 'table_feeds_genres') else None
        self.table_feeds_labels = self.parent.table_feeds_labels if hasattr(self.parent, 'table_feeds_labels') else None
        
        # Chart containers from specific pages
        self.chart_artists_widget = self.parent.chart_artists_widget if hasattr(self.parent, 'chart_artists_widget') else None
        self.charts_feeds_albums = self.parent.charts_feeds_albums if hasattr(self.parent, 'charts_feeds_albums') else None
        self.chart_feeds_genres = self.parent.chart_feeds_genres if hasattr(self.parent, 'chart_feeds_genres') else None
        self.chart_feeds_labels = self.parent.chart_feeds_labels if hasattr(self.parent, 'chart_feeds_labels') else None
    
    def setup_connections(self):
        """Connect UI elements to their respective handlers."""
        if not self.parent:
            return
        
        # Connect buttons directly to their handler methods
        button_handlers = [
            (self.btn_artists, self.on_artists_clicked),
            (self.btn_albums, self.on_albums_clicked),
            (self.btn_labels, self.on_labels_clicked),
            (self.btn_genres, self.on_genres_clicked),
            (self.btn_time, self.on_time_clicked),
            (self.btn_listens, self.on_listens_clicked),
            (self.btn_info, self.on_info_clicked)
        ]
        
        for button, handler in button_handlers:
            if button:
                try:
                    # Disconnect existing connections to avoid duplicates
                    button.clicked.disconnect()
                except:
                    pass
                button.clicked.connect(handler)
                logging.info(f"Connected button {button.objectName()} to handler")
            
    def ensure_db_connection(self):
        """Ensure we have a valid database connection."""
        if self.conn and hasattr(self.conn, 'cursor'):
            try:
                # Test the connection
                cursor = self.conn.cursor()
                cursor.execute("SELECT 1")
                return True
            except sqlite3.Error:
                logging.error("Database connection test failed")
        
        # If we reach here, the connection is invalid
        if hasattr(self.parent, 'ensure_db_connection'):
            # Try to get a connection from the parent
            if self.parent.ensure_db_connection():
                self.conn = self.parent.conn
                return True
        
        logging.error("No valid database connection available")
        return False
    
    def on_artists_clicked(self):
        """Handle clicks on the artists button."""
        if not self.ensure_db_connection():
            return
            
        logging.info("Loading feed statistics for artists")
        
        # Set the stacked widget to the artists page (index 1 according to UI)
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(1)
        
        # Load data into the existing table and chart
        self.load_feed_artists_stats()
    
    def on_albums_clicked(self):
        """Handle clicks on the albums button."""
        if not self.ensure_db_connection():
            return
            
        logging.info("Loading feed statistics for albums")
        
        # Set the stacked widget to the albums page (index 2 according to UI)
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(2)
        
        # Load data into the existing table and chart
        self.load_feed_albums_stats()
    
    def on_labels_clicked(self):
        """Handle clicks on the labels button."""
        if not self.ensure_db_connection():
            return
            
        logging.info("Loading feed statistics for labels")
        
        # Set the stacked widget to the labels page (index 4 according to UI)
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(4)
        
        # Load data into the existing table and chart
        self.load_feed_labels_stats()
        
    def on_genres_clicked(self):
        """Handle clicks on the genres button."""
        if not self.ensure_db_connection():
            return
            
        logging.info("Loading feed statistics for genres")
        
        # Set the stacked widget to the genres page (index 3 according to UI)
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(3)
        
        # Load data into the existing table and chart
        self.load_feed_genres_stats()
        
    def on_time_clicked(self):
        """Handle clicks on the time button."""
        if not self.ensure_db_connection():
            return
            
        # Set the stacked widget to the time page (index 5)
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(5)
        
        # Load time-related feed data
        self.load_feed_time_stats()
        
    def on_listens_clicked(self):
        """Handle clicks on the listens button."""
        if not self.ensure_db_connection():
            return
            
        logging.info("Loading feed statistics related to listens")
        
        # Set the stacked widget to the listens page (index 6)
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(6)
        
        # Load listen-related feed data
        self.load_feed_listens_stats()


    def on_info_clicked(self):
        """Handle clicks on the info button."""
        if not self.ensure_db_connection():
            return
            
        logging.info("Loading detailed feed information")
        
        # Set the stacked widget to the info page (index 6)
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(6)
        
        # Load detailed feed info
        self.load_feed_info_stats()
        
    def load_feed_artists_stats(self):
        """Load statistics about feeds related to artists into UI elements."""
        if not self.ensure_db_connection():
            logging.error("No database connection available")
            return
        
        # Get the table and chart container directly from parent
        table_feeds_artists = self.parent.table_feeds_artists if hasattr(self.parent, 'table_feeds_artists') else None
        chart_artists_widget = self.parent.chart_artists_widget if hasattr(self.parent, 'chart_artists_widget') else None
        
        if not table_feeds_artists or not chart_artists_widget:
            logging.error(f"Missing UI elements for artists feed stats: table={table_feeds_artists is not None}, chart={chart_artists_widget is not None}")
            return
        
        try:
            # Clear the existing table
            table_feeds_artists.setRowCount(0)
            
            # Configure table headers if needed
            if table_feeds_artists.columnCount() < 2:
                table_feeds_artists.setColumnCount(2)
                table_feeds_artists.setHorizontalHeaderLabels(["Artista", "Feeds"])
            
            # Query data
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    ar.name as artist_name, 
                    COUNT(f.id) as feed_count
                FROM 
                    artists ar
                JOIN 
                    feeds f ON f.entity_id = ar.id AND f.entity_type = 'artist'
                GROUP BY 
                    ar.name
                ORDER BY 
                    feed_count DESC
                LIMIT 50;
            """)
            
            results = cursor.fetchall()
            
            # Debug information
            logging.info(f"Found {len(results)} artists with feeds")
            if results:
                logging.info(f"First few results: {results[:3]}")
            
            # Check if we have data
            if not results:
                # Add a message to the table
                table_feeds_artists.setRowCount(1)
                table_feeds_artists.setItem(0, 0, QTableWidgetItem("No hay datos de feeds para artistas"))
                table_feeds_artists.setSpan(0, 0, 1, 2)
                return
            
            # Fill the table
            table_feeds_artists.setRowCount(len(results))
            for i, row in enumerate(results):
                # Handle different data formats (tuple or sqlite Row)
                if isinstance(row, tuple) and len(row) >= 2:
                    artist, count = row
                elif isinstance(row, sqlite3.Row):
                    artist = row['artist_name']
                    count = row['feed_count']
                else:
                    logging.error(f"Unexpected data format: {type(row)}, {row}")
                    continue
                    
                table_feeds_artists.setItem(i, 0, QTableWidgetItem(str(artist)))
                table_feeds_artists.setItem(i, 1, QTableWidgetItem(str(count)))
            
            # Resize columns to fit content
            table_feeds_artists.resizeColumnsToContents()
            
            # Create chart - make sure the container has a layout
            chart_layout = self.helper_functions.get('ensure_widget_has_layout', self.ensure_widget_has_layout)(chart_artists_widget)
            self.helper_functions.get('clear_layout', self.clear_layout)(chart_layout)
            
            # Create pie chart for artists
            chart_view = ChartFactory.create_pie_chart(
                results[:15] if len(results) > 15 else results,
                "Top Artistas con Feeds"
            )
            
            # Add chart to layout
            if chart_view:
                chart_layout.addWidget(chart_view)
                logging.info("Artist chart created successfully")
            else:
                logging.error("Failed to create artist chart")
                
        except Exception as e:
            logging.error(f"Error loading feed artists stats: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def load_feed_albums_stats(self):
        """Load statistics about feeds related to albums into UI elements."""
        if not self.ensure_db_connection() or not self.table_feeds_albums or not self.charts_feeds_albums:
            logging.error("Missing required UI elements for albums feed stats")
            return
            
        try:
            # Clear the existing table
            self.table_feeds_albums.setRowCount(0)
            
            # Configure table if needed
            if self.table_feeds_albums.columnCount() < 3:
                self.table_feeds_albums.setColumnCount(3)
                self.table_feeds_albums.setHorizontalHeaderLabels(["Álbum", "Artista", "Feeds"])
            
            # Query data
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    a.name as album_name,
                    ar.name as artist_name,
                    COUNT(f.id) as feed_count
                FROM 
                    albums a
                JOIN 
                    artists ar ON a.artist_id = ar.id
                JOIN 
                    feeds f ON f.entity_id = a.id AND f.entity_type = 'album'
                GROUP BY 
                    a.name, ar.name
                ORDER BY 
                    feed_count DESC
                LIMIT 50;
            """)
            
            results = cursor.fetchall()
            
            # Fill the table
            self.table_feeds_albums.setRowCount(len(results))
            for i, (album, artist, count) in enumerate(results):
                self.table_feeds_albums.setItem(i, 0, QTableWidgetItem(album))
                self.table_feeds_albums.setItem(i, 1, QTableWidgetItem(artist))
                self.table_feeds_albums.setItem(i, 2, QTableWidgetItem(str(count)))
            
            self.table_feeds_albums.resizeColumnsToContents()
            
            # Create chart - make sure the container has a layout
            chart_layout = self.ensure_widget_has_layout(self.charts_feeds_albums)
            self.clear_layout(chart_layout)
            
            # Create chart data
            chart_data = [(f"{album} - {artist}", count) for album, artist, count in results]
            
            # Create pie chart for albums
            chart_view = ChartFactory.create_pie_chart(
                chart_data[:15] if len(chart_data) > 15 else chart_data,
                "Top Álbumes con Feeds"
            )
            
            # Add chart to layout
            if chart_view:
                chart_layout.addWidget(chart_view)
                
        except Exception as e:
            logging.error(f"Error loading feed albums stats: {e}")
            import traceback
            logging.error(traceback.format_exc())
    

        
    def load_entity_type_stats(self):
        """Load statistics about entity types with feeds (for main page)."""
        if not self.ensure_db_connection() or not self.table_entity or not self.chart_container_entity:
            return
            
        try:
            # Clear existing chart
            if hasattr(self.parent, 'clear_layout'):
                layout = self.ensure_widget_has_layout(self.chart_container_entity)
                self.parent.clear_layout(layout)
            
            # Query data
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    entity_type, 
                    COUNT(*) as feed_count
                FROM 
                    feeds
                GROUP BY 
                    entity_type
                ORDER BY 
                    feed_count DESC;
            """)
            
            results = cursor.fetchall()
            
            # Fill the table
            self.table_entity.setRowCount(len(results))
            for i, (entity_type, count) in enumerate(results):
                self.table_entity.setItem(i, 0, QTableWidgetItem(entity_type))
                self.table_entity.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_entity.resizeColumnsToContents()
            
            # Create chart
            chart_view = ChartFactory.create_pie_chart(
                results,
                "Feeds por Tipo de Entidad"
            )
            
            # Add to layout
            self.chart_container_entity.layout().addWidget(chart_view)
            
        except Exception as e:
            logging.error(f"Error loading entity type stats: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def load_feed_names_stats(self):
        """Load statistics about feed names (for main page)."""
        if not self.ensure_db_connection() or not self.table_feeds or not self.chart_container_feeds:
            return
            
        try:
            # Clear existing chart
            if hasattr(self.parent, 'clear_layout'):
                layout = self.ensure_widget_has_layout(self.chart_container_feeds)
                self.parent.clear_layout(layout)
            
            # Query data
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    feed_name, 
                    COUNT(*) as post_count
                FROM 
                    feeds
                GROUP BY 
                    feed_name
                ORDER BY 
                    post_count DESC;
            """)
            
            results = cursor.fetchall()
            
            # Fill the table
            self.table_feeds.setRowCount(len(results))
            for i, (feed_name, count) in enumerate(results):
                self.table_feeds.setItem(i, 0, QTableWidgetItem(feed_name))
                self.table_feeds.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_feeds.resizeColumnsToContents()
            
            # Create chart - only show top 10 for better readability
            chart_data = results[:10] if len(results) > 10 else results
            chart_view = ChartFactory.create_bar_chart(
                chart_data,
                "Top Feeds por Publicaciones",
                x_label="Feed",
                y_label="Publicaciones"
            )
            
            # Add to layout
            self.chart_container_feeds.layout().addWidget(chart_view)
            
        except Exception as e:
            logging.error(f"Error loading feed names stats: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
    def load_feed_labels_stats(self):
        """Load statistics about feeds related to labels into UI elements."""
        if not self.ensure_db_connection() or not self.table_feeds_labels or not self.chart_feeds_labels:
            logging.error("Missing required UI elements for labels feed stats")
            return
            
        try:
            # Clear the existing table
            self.table_feeds_labels.setRowCount(0)
            
            # Configure table if needed
            if self.table_feeds_labels.columnCount() < 2:
                self.table_feeds_labels.setColumnCount(2)
                self.table_feeds_labels.setHorizontalHeaderLabels(["Sello", "Feeds"])
            
            # Query data - this is a bit complex as labels don't directly have feeds
            # We'll join through albums that have the label
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    a.label as label_name,
                    COUNT(DISTINCT f.id) as feed_count
                FROM 
                    albums a
                JOIN 
                    feeds f ON f.entity_id = a.id AND f.entity_type = 'album'
                WHERE 
                    a.label IS NOT NULL AND a.label != ''
                GROUP BY 
                    a.label
                ORDER BY 
                    feed_count DESC
                LIMIT 50;
            """)
            
            results = cursor.fetchall()
            
            # Fill the table
            self.table_feeds_labels.setRowCount(len(results))
            for i, (label, count) in enumerate(results):
                self.table_feeds_labels.setItem(i, 0, QTableWidgetItem(label))
                self.table_feeds_labels.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_feeds_labels.resizeColumnsToContents()
            
            # Create chart - make sure the container has a layout
            chart_layout = self.ensure_widget_has_layout(self.chart_feeds_labels)
            self.clear_layout(chart_layout)
            
            # Create pie chart for labels
            chart_view = ChartFactory.create_pie_chart(
                results[:15] if len(results) > 15 else results,
                "Top Sellos con Feeds"
            )
            
            # Add chart to layout
            if chart_view:
                chart_layout.addWidget(chart_view)
                
        except Exception as e:
            logging.error(f"Error loading feed labels stats: {e}")
            import traceback
            logging.error(traceback.format_exc())
    
    def create_or_get_widget(self, object_name):
        """
        Create a new widget or get an existing one with the given object name.
        
        Args:
            object_name: The name to assign to the widget
            
        Returns:
            QWidget: The created or found widget
        """
        # First, check if the widget already exists
        existing_widget = None
        if self.parent:
            existing_widget = self.parent.findChild(QWidget, object_name)
        
        if existing_widget:
            return existing_widget
        
        # Create a new widget
        new_widget = QWidget()
        new_widget.setObjectName(object_name)
        
        # Create a layout for the widget
        layout = QVBoxLayout(new_widget)
        
        # If there's a stacked widget, add the new widget to it
        if self.stacked_widget and self.stacked_widget.count() > 1:
            # Add the widget to the second page
            page_widget = self.stacked_widget.widget(1)
            if page_widget and page_widget.layout():
                page_widget.layout().addWidget(new_widget)
            else:
                logging.error(f"Cannot add widget to stacked widget page: {page_widget}")
        else:
            logging.warning("No appropriate stacked widget to add the new widget to")
        
        return new_widget
    
    def ensure_widget_has_layout(self, widget, layout_type=QVBoxLayout):
        """Ensures a widget has a layout without creating duplicates."""
        if widget is None:
            logging.error("Widget is None in ensure_widget_has_layout")
            return None
        
        # Use helper function from parent if available
        if 'ensure_widget_has_layout' in self.helper_functions:
            return self.helper_functions['ensure_widget_has_layout'](widget, layout_type)
        
        # Fallback implementation
        layout = widget.layout()
        if layout is None:
            layout = layout_type()
            widget.setLayout(layout)
        
        return layout


    def clear_layout(self, layout):
        """Clears all widgets from a layout."""
        if layout is None:
            return
        
        # Use helper function from parent if available
        if 'clear_layout' in self.helper_functions:
            return self.helper_functions['clear_layout'](layout)
        
        # Fallback implementation
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
                item.layout().setParent(None)


    def load_feed_stats(self):
        """Main method to load all feed statistics and update UI."""
        if not self.ensure_db_connection():
            return
        
        # Set the stacked widget to the main feeds page
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(0)
        
        # Load entity type stats
        self.load_entity_type_stats()
        
        # Load feed names stats
        self.load_feed_names_stats()
        
        logging.info("Feed statistics loaded successfully")



    def load_feed_genres_stats(self):
        """Load statistics about feeds related to genres (via albums and songs)."""
        if not self.ensure_db_connection() or not self.table_feeds_genres or not self.chart_feeds_genres:
            logging.error("Missing required UI elements for genres feed stats")
            return
            
        try:
            # Clear the existing table
            self.table_feeds_genres.setRowCount(0)
            
            # Configure table if needed
            if self.table_feeds_genres.columnCount() < 2:
                self.table_feeds_genres.setColumnCount(2)
                self.table_feeds_genres.setHorizontalHeaderLabels(["Género", "Feeds"])
            
            # Query data - join albums with genres to their feeds
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    a.genre as genre,
                    COUNT(DISTINCT f.id) as feed_count
                FROM 
                    albums a
                JOIN 
                    feeds f ON f.entity_id = a.id AND f.entity_type = 'album'
                WHERE 
                    a.genre IS NOT NULL AND a.genre != ''
                GROUP BY 
                    a.genre
                ORDER BY 
                    feed_count DESC
                LIMIT 50;
            """)
            
            results = cursor.fetchall()
            
            # Fill the table
            self.table_feeds_genres.setRowCount(len(results))
            for i, (genre, count) in enumerate(results):
                self.table_feeds_genres.setItem(i, 0, QTableWidgetItem(genre))
                self.table_feeds_genres.setItem(i, 1, QTableWidgetItem(str(count)))
            
            self.table_feeds_genres.resizeColumnsToContents()
            
            # Create chart - make sure the container has a layout
            chart_layout = self.ensure_widget_has_layout(self.chart_feeds_genres)
            self.clear_layout(chart_layout)
            
            # Create pie chart for genres
            chart_view = ChartFactory.create_pie_chart(
                results[:15] if len(results) > 15 else results,
                "Géneros con Más Feeds"
            )
            
            # Add chart to layout
            if chart_view:
                chart_layout.addWidget(chart_view)
                
        except Exception as e:
            logging.error(f"Error loading feed genres stats: {e}")
            import traceback
            logging.error(traceback.format_exc())



    def load_feed_time_stats(self):
        """Load time-related feed statistics."""
        if not self.ensure_db_connection():
            return
            
        # Get table and chart references
        table = self.parent.table_feeds_time if hasattr(self.parent, 'table_feeds_time') else None
        chart_container = self.parent.charts_feeds_time if hasattr(self.parent, 'charts_feeds_time') else None
        
        if not table or not chart_container:
            logging.error("Missing UI elements for feed time stats")
            return
        
        try:
            # Configure table
            if table.columnCount() < 3:
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Fecha", "Feed", "Publicaciones"])
            
            # Clear existing data
            table.setRowCount(0)
            
            # Clear chart
            chart_layout = self.ensure_widget_has_layout(chart_container)
            self.clear_layout(chart_layout)
            
            # Query data - posts by month/year
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', post_date) as month_year,
                    COUNT(*) as post_count
                FROM 
                    feeds
                WHERE 
                    post_date IS NOT NULL
                GROUP BY 
                    month_year
                ORDER BY 
                    month_year;
            """)
            
            time_results = cursor.fetchall()
            
            # Create line chart
            chart_view = ChartFactory.create_line_chart(
                time_results,
                "Publicaciones por Mes",
                x_label="Fecha",
                y_label="Publicaciones",
                date_axis=True
            )
            
            if chart_view:
                chart_layout.addWidget(chart_view)
            
            # Fill table with data by month and feed
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', post_date) as month_year,
                    feed_name,
                    COUNT(*) as post_count
                FROM 
                    feeds
                WHERE 
                    post_date IS NOT NULL
                GROUP BY 
                    month_year, feed_name
                ORDER BY 
                    month_year DESC, post_count DESC;
            """)
            
            detailed_results = cursor.fetchall()
            
            table.setRowCount(len(detailed_results))
            for i, (date, feed, count) in enumerate(detailed_results):
                table.setItem(i, 0, QTableWidgetItem(date))
                table.setItem(i, 1, QTableWidgetItem(feed))
                table.setItem(i, 2, QTableWidgetItem(str(count)))
            
            table.resizeColumnsToContents()
            
        except Exception as e:
            logging.error(f"Error loading feed time stats: {e}")
            import traceback
            logging.error(traceback.format_exc())


    def navigate_to_page(self, page_index):
        """Navigate to a specific page in the stacked widget."""
        if not self.stacked_widget:
            logging.error("No stacked widget available for navigation")
            return False
        
        if page_index < 0 or page_index >= self.stacked_widget.count():
            logging.error(f"Invalid page index: {page_index}, max: {self.stacked_widget.count()-1}")
            return False
        
        current_index = self.stacked_widget.currentIndex()
        if current_index != page_index:
            logging.info(f"Changing feed page from {current_index} to {page_index}")
            self.stacked_widget.setCurrentIndex(page_index)
            return True
        
        return False




    def load_feed_listens_stats(self):
        """Load statistics about artists in feeds ordered by listen count."""
        if not self.ensure_db_connection():
            return
            
        # Get table and chart references directly from parent
        table = self.parent.table_feeds_listens if hasattr(self.parent, 'table_feeds_listens') else None
        chart_container = self.parent.chart_feeds_listens if hasattr(self.parent, 'chart_feeds_listens') else None
        
        if not table or not chart_container:
            logging.error("Missing UI elements for feed listens stats")
            return
        
        try:
            # Configure table
            if table.columnCount() < 3:
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Artista", "Feeds", "Escuchas"])
            
            # Clear existing data
            table.setRowCount(0)
            
            # Clear chart
            chart_layout = self.helper_functions.get('ensure_widget_has_layout', self.ensure_widget_has_layout)(chart_container)
            self.helper_functions.get('clear_layout', self.clear_layout)(chart_layout)
            
            # First check if we have any listen data
            cursor = self.conn.cursor()
            
            # Fixed SQL query for checking if listen data exists
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM scrobbles LIMIT 1) + 
                    (SELECT COUNT(*) FROM listens LIMIT 1) as has_listens;
            """)
            
            has_listens = cursor.fetchone()[0] > 0
            
            if not has_listens:
                # No listen data available
                label = QLabel("No hay datos de escuchas disponibles")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chart_layout.addWidget(label)
                
                table.setRowCount(1)
                table.setItem(0, 0, QTableWidgetItem("No hay datos de escuchas"))
                table.setSpan(0, 0, 1, 3)
                return
            
            # Query data - get artists mentioned in feeds and their listen counts
            # Try with scrobbles first
            cursor.execute("""
                SELECT 
                    ar.name as artist_name,
                    COUNT(DISTINCT f.id) as feed_count,
                    COUNT(s.id) as listen_count
                FROM 
                    artists ar
                JOIN 
                    feeds f ON f.entity_id = ar.id AND f.entity_type = 'artist'
                LEFT JOIN 
                    scrobbles s ON s.artist_name = ar.name
                GROUP BY 
                    ar.name
                ORDER BY 
                    listen_count DESC, feed_count DESC
                LIMIT 30;
            """)
            
            results = cursor.fetchall()
            
            # If no results with scrobbles, try with listens
            if not results:
                cursor.execute("""
                    SELECT 
                        ar.name as artist_name,
                        COUNT(DISTINCT f.id) as feed_count,
                        COUNT(l.id) as listen_count
                    FROM 
                        artists ar
                    JOIN 
                        feeds f ON f.entity_id = ar.id AND f.entity_type = 'artist'
                    LEFT JOIN 
                        listens l ON l.artist_name = ar.name
                    GROUP BY 
                        ar.name
                    ORDER BY 
                        listen_count DESC, feed_count DESC
                    LIMIT 30;
                """)
                
                results = cursor.fetchall()
            
            # Fill table with data
            table.setRowCount(len(results))
            
            # Prepare data for pie chart
            chart_data = []
            
            for i, row in enumerate(results):
                if isinstance(row, tuple) and len(row) >= 3:
                    artist, feed_count, listen_count = row
                elif isinstance(row, sqlite3.Row):
                    artist = row['artist_name']
                    feed_count = row['feed_count']
                    listen_count = row['listen_count']
                else:
                    continue
                    
                table.setItem(i, 0, QTableWidgetItem(str(artist)))
                table.setItem(i, 1, QTableWidgetItem(str(feed_count)))
                table.setItem(i, 2, QTableWidgetItem(str(listen_count)))
                
                # Add to chart data if it has listens
                if listen_count > 0:
                    chart_data.append((artist, listen_count))
            
            # Resize columns
            table.resizeColumnsToContents()
            
            # Create pie chart of top listened artists with feeds
            if chart_data:
                chart_view = ChartFactory.create_pie_chart(
                    chart_data[:10] if len(chart_data) > 10 else chart_data,
                    "Artistas con Feeds - Por Escuchas"
                )
                
                if chart_view:
                    chart_layout.addWidget(chart_view)
                
        except Exception as e:
            logging.error(f"Error loading feed listens stats: {e}")
            import traceback
            logging.error(traceback.format_exc())


    def load_feed_info_stats(self):
        """Load detailed information about feeds including content length."""
        if not self.ensure_db_connection():
            return
            
        # Get table and chart references directly from parent
        table = self.parent.table_feeds_info if hasattr(self.parent, 'table_feeds_info') else None
        chart_container = self.parent.chart_feeds_info if hasattr(self.parent, 'chart_feeds_info') else None
        
        if not table or not chart_container:
            logging.error("Missing UI elements for feed info stats")
            return
        
        try:
            # Configure table
            if table.columnCount() < 4:
                table.setColumnCount(4)
                table.setHorizontalHeaderLabels(["Feed", "Artista/Álbum", "URL", "Tamaño Contenido"])
            
            # Clear existing data
            table.setRowCount(0)
            
            # Clear chart
            chart_layout = self.helper_functions.get('ensure_widget_has_layout', self.ensure_widget_has_layout)(chart_container)
            self.helper_functions.get('clear_layout', self.clear_layout)(chart_layout)
            
            # Query data - get feeds with content length
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    f.feed_name,
                    CASE 
                        WHEN f.entity_type = 'artist' THEN (SELECT name FROM artists WHERE id = f.entity_id)
                        WHEN f.entity_type = 'album' THEN (SELECT name FROM albums WHERE id = f.entity_id)
                        ELSE f.entity_type || '-' || f.entity_id
                    END as entity_name,
                    f.post_url,
                    LENGTH(f.content) as content_length
                FROM 
                    feeds f
                WHERE 
                    f.content IS NOT NULL
                ORDER BY 
                    content_length DESC
                LIMIT 100;
            """)
            
            results = cursor.fetchall()
            
            # Fill table with data
            table.setRowCount(len(results))
            
            # Prepare data for bar chart - aggregate by entity
            entity_content = {}
            
            for i, row in enumerate(results):
                if isinstance(row, tuple) and len(row) >= 4:
                    feed_name, entity_name, url, content_length = row
                elif isinstance(row, sqlite3.Row):
                    feed_name = row['feed_name']
                    entity_name = row['entity_name']
                    url = row['post_url']
                    content_length = row['content_length']
                else:
                    continue
                    
                table.setItem(i, 0, QTableWidgetItem(str(feed_name)))
                table.setItem(i, 1, QTableWidgetItem(str(entity_name)))
                table.setItem(i, 2, QTableWidgetItem(str(url) if url else ""))
                table.setItem(i, 3, QTableWidgetItem(str(content_length)))
                
                # Aggregate content length by entity
                if entity_name in entity_content:
                    entity_content[entity_name] += content_length
                else:
                    entity_content[entity_name] = content_length
            
            # Resize columns
            table.resizeColumnsToContents()
            
            # Create bar chart of entities by content length
            chart_data = sorted(entity_content.items(), key=lambda x: x[1], reverse=True)[:15]
            
            if chart_data:
                chart_view = ChartFactory.create_bar_chart(
                    chart_data,
                    "Artistas/Álbumes por Tamaño de Contenido",
                    x_label="Entidad",
                    y_label="Caracteres"
                )
                
                if chart_view:
                    chart_layout.addWidget(chart_view)
                
        except Exception as e:
            logging.error(f"Error loading feed info stats: {e}")
            import traceback
            logging.error(traceback.format_exc())