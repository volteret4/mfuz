# chart_utils.py
from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QWidget, QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QPen
import logging
from PyQt6.QtCharts import QChart


CHART_COLORS = [
    "#cba6f7",  # Purple
    "#f5c2e7",  # Pink
    "#89dceb",  # Cyan
    "#a6e3a1",  # Green
    "#f9e2af",  # Yellow
    "#fab387",  # Peach
    "#eba0ac",  # Red
    "#89b4fa",  # Blue
]

# # Then use these colors in charts
# for i, color in enumerate(ChartFactory.CHART_COLORS):
#     if i < bar_set.count():
#         bar_set.setColor(QColor(color))

class ChartFactory:
    """Factory class for creating charts with proper fallbacks"""
    
    @staticmethod
    def is_charts_available():
        """Check if the Qt Charts module is available"""
        try:
            from PyQt6.QtCharts import QChart
            return True
        except ImportError:
            return False
    
    @staticmethod
    def create_bar_chart(data, title, x_label="Category", y_label="Value", limit=10):
        """Create a bar chart or fallback to text representation"""
        if not ChartFactory.is_charts_available():
            return ChartFactory.create_text_chart(data, title)
            
        try:
            from PyQt6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QPainter, QPen, QColor
            
            # Limitar a los primeros N elementos
            limited_data = data[:limit]
            
            # Crear el conjunto de barras
            bar_set = QBarSet("Valores")
            
            # Eliminar el borde de las barras estableciendo un pen transparente
            transparent_pen = QPen(QColor(0, 0, 0, 0))  # Color totalmente transparente
            bar_set.setPen(transparent_pen)
            
            # Nombres de categorías para el eje X
            categories = []
            
            # Añadir valores al conjunto
            for label, value in limited_data:
                bar_set.append(value)
                # Acortar nombres muy largos
                display_name = str(label) if len(str(label)) < 20 else str(label)[:17] + "..."
                categories.append(display_name)
            
            # Crear la serie
            series = QBarSeries()
            series.append(bar_set)
            
            # Crear el gráfico
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle(title)
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            
            # Crear ejes
            axis_x = QBarCategoryAxis()
            axis_x.append(categories)
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            max_value = max(value for _, value in limited_data) if limited_data else 0
            axis_y.setRange(0, max_value * 1.1)  # Añadir un 10% extra
            axis_y.setLabelFormat("%i")
            axis_y.setTitleText(y_label)
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_y)
            
            # Configurar leyenda
            chart.legend().setVisible(False)
                        
            # Crear la vista del gráfico
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            ChartFactory.apply_dark_theme(chart)
            
            return chart_view
            
        except Exception as e:
            logging.error(f"Error creating bar chart: {e}")
            return ChartFactory.create_error_widget(str(e))
    

    @staticmethod
    def create_pie_chart(data, title, limit=15):
        """Creates a pie chart with the given data."""
        logging.info(f"Creating pie chart '{title}' with {len(data)} items")
        
        # Check if charts are available
        if not ChartFactory.is_charts_available():
            logging.warning("Charts not available, returning text representation")
            return ChartFactory.create_text_chart(data, title)
        
        try:
            from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QPieSlice
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QPainter, QFont, QPen, QColor, QBrush
            
            # Create pie series
            series = QPieSeries()
            
            # Prepare data for the chart
            chart_data = []
            if len(data) > limit:
                # Get top items and calculate "Others"
                top_items = sorted(data, key=lambda x: x[1], reverse=True)[:limit-1]
                other_sum = sum(count for _, count in sorted(data, key=lambda x: x[1], reverse=True)[limit-1:])
                
                chart_data = top_items.copy()
                if other_sum > 0:
                    chart_data.append(("Otros", other_sum))
            else:
                chart_data = data.copy()
            
            # Calculate total for percentages
            total = sum(count for _, count in chart_data)
            
            # Add items to the series
            for label, value in chart_data:
                # Preserve the full name in the series for legend display
                slice = series.append(str(label), value)
            
            # Get the background color to match slice borders
            background_color = "#1a1b26"  # Default dark theme background
            
            # Define text color for labels and legend
            text_color = "#a2a6ba"  # As requested
            
            # Style the slices - focus on correct legend display
            for i in range(series.count()):
                slice = series.slices()[i]
                percent = (slice.value() / total) * 100 if total > 0 else 0
                label = str(slice.label())
                
                # Set percentage label and name on the slice
                slice.setLabel(f"{label}: {percent:.1f}%")
                slice.setLabelVisible(True)
                
                # Set the label color to the requested color
                slice.setLabelColor(QColor(text_color))
                
                # Remove the white border by setting the pen color to match background
                slice.setPen(QPen(QColor(background_color), 0))
                
                # Explode slightly on hover
                slice.setExploded(True)
                slice.setExplodeDistanceFactor(0.05)
            
            # Create chart
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle(title)
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            
            # Configure legend to show the full names
            chart.legend().setVisible(True)
            chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
            
            # Make legend text more readable and set the color
            legend_font = QFont()
            legend_font.setPointSize(8)  # Smaller font size
            chart.legend().setFont(legend_font)
            
            # Set the legend text color
            chart.legend().setLabelBrush(QBrush(QColor(text_color)))
            
            # Create chart view
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Set minimum size to ensure chart is visible
            chart_view.setMinimumSize(400, 300)
            
            logging.info(f"Pie chart '{title}' created successfully")
            
            # Apply dark theme with improved legend text
            ChartFactory.apply_dark_theme(chart, text_color=text_color, background_color=background_color)
            
            return chart_view
            
        except Exception as e:
            logging.error(f"Error creating pie chart: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
            # Return error widget
            return ChartFactory.create_error_widget(str(e))


    
    @staticmethod
    def create_line_chart(data, title, x_label="X", y_label="Y", date_axis=False):
        """Create a line chart or fallback to text representation"""
        if not ChartFactory.is_charts_available():
            return ChartFactory.create_text_chart(data, title)
            
        try:
            from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
            from PyQt6.QtCore import Qt, QDateTime
            from PyQt6.QtGui import QPainter
            
            # Crear serie para el gráfico
            series = QLineSeries()
            
            # Determinar si estamos trabajando con fechas o valores numéricos
            if date_axis:
                # Para fechas, espera tuplas (fecha_str, valor)
                valid_points = []
                for date_str, value in data:
                    try:
                        # Convertir string a QDateTime
                        if isinstance(date_str, str):
                            if len(date_str) == 4:  # Año
                                date = QDateTime.fromString(f"{date_str}-01-01", "yyyy-MM-dd")
                            elif len(date_str) == 7:  # Año-Mes
                                date = QDateTime.fromString(f"{date_str}-01", "yyyy-MM-dd")
                            else:  # Fecha completa
                                date = QDateTime.fromString(date_str, "yyyy-MM-dd")
                            
                            if date.isValid():
                                valid_points.append((date.toMSecsSinceEpoch(), value))
                    except Exception:
                        continue
                
                # Ordenar por fecha
                valid_points.sort()
                
                # Añadir puntos ordenados
                for date_msecs, value in valid_points:
                    series.append(date_msecs, value)
                    
                # Crear el gráfico con eje de fecha
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle(title)
                
                # Eje X (tiempo)
                axis_x = QDateTimeAxis()
                # Determinar formato de fecha según los datos
                if len(data) > 0 and isinstance(data[0][0], str):
                    if len(data[0][0]) == 4:  # Año
                        axis_x.setFormat("yyyy")
                    elif len(data[0][0]) == 7:  # Año-Mes
                        axis_x.setFormat("MMM yyyy")
                    else:
                        axis_x.setFormat("dd/MM/yyyy")
                else:
                    axis_x.setFormat("yyyy")
                
                axis_x.setTitleText(x_label)
                chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
                
            else:
                # Para valores numéricos (x, y)
                valid_points = []
                for x, y in data:
                    try:
                        x_val = float(x)
                        y_val = float(y)
                        valid_points.append((x_val, y_val))
                    except (ValueError, TypeError):
                        continue
                
                # Ordenar por valor X
                valid_points.sort()
                
                # Añadir puntos ordenados
                for x, y in valid_points:
                    series.append(x, y)
                
                # Crear el gráfico con eje numérico
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle(title)
                
                # Eje X (numérico)
                axis_x = QValueAxis()
                axis_x.setLabelFormat("%i")
                axis_x.setTitleText(x_label)
                chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
            
            # Eje Y (valores)
            axis_y = QValueAxis()
            axis_y.setLabelFormat("%i")
            axis_y.setTitleText(y_label)
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_y)
            
            chart.legend().setVisible(False)
            
            # Crear la vista del gráfico
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            ChartFactory.apply_dark_theme(chart)

            return chart_view
            
        except Exception as e:
            logging.error(f"Error creating line chart: {e}")
            return ChartFactory.create_error_widget(str(e))
    
    @staticmethod
    def create_text_chart(data, title):
        """Create a text representation of the data"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        header = QLabel(title)
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        
        # Format data as text
        text = f"Datos para {title}:\n\n"
        
        # Determinar si tenemos muchos datos
        if len(data) > 20:
            shown_data = data[:20]
            text += f"Mostrando los primeros 20 de {len(data)} elementos:\n\n"
        else:
            shown_data = data
        
        # Formatear datos
        for item, value in shown_data:
            text += f"{item}: {value}\n"
        
        if len(data) > 20:
            text += f"\n... y {len(data) - 20} elementos más"
            
        text_area.setText(text)
        layout.addWidget(text_area)
        
        ChartFactory.apply_dark_theme(chart)

        return widget
    
    @staticmethod
    def create_error_widget(error_message):
        """Create a widget to display error messages"""
        label = QLabel(f"Error al crear el gráfico: {error_message}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background-color: #f0f0f0; padding: 20px; color: red;")
        return label

    @staticmethod
    def apply_dark_theme(chart, text_color="#a2a6ba", background_color="#1a1b26"):
        """Apply a dark theme to a chart"""
        if not isinstance(chart, QChart):
            return
            
        # Set background
        chart.setBackgroundBrush(QBrush(QColor(background_color)))
        
        # Remove chart border by setting a zero-width pen in background color
        chart.setBackgroundPen(QPen(QColor(background_color), 0))
        
        # Set text colors
        chart.setTitleBrush(QBrush(QColor(text_color)))
        
        # Axes text
        for axis in chart.axes():
            axis.setLabelsBrush(QBrush(QColor(text_color)))
            axis.setTitleBrush(QBrush(QColor(text_color)))
            
            # Set grid color to a slightly lighter color 
            gridline_color = QColor(text_color)
            gridline_color.setAlphaF(0.2)  # More transparent
            axis.setGridLinePen(QPen(gridline_color, 0.5))
            
        # Legend - use the specified color for better visibility
        chart.legend().setLabelBrush(QBrush(QColor(text_color)))
        chart.legend().setBrush(QBrush(QColor(background_color)))
        
        # PyQt6 may not have these properties, so wrap in try/except
        try:
            # Make legend background transparent
            chart.legend().setBackgroundVisible(False)
            # Remove legend border
            chart.legend().setColor(QColor(background_color))
        except:
            pass