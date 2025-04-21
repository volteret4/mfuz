# chart_utils.py
from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
import logging
from PyQt6.QtCharts import QChart

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
            from PyQt6.QtGui import QPainter
            
            # Limitar a los primeros N elementos
            limited_data = data[:limit]
            
            # Crear el conjunto de barras
            bar_set = QBarSet("Valores")
            
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
        
        # Charts are available, try to create one
        try:
            from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QPieSlice
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QPainter
            
            # Create pie series
            series = QPieSeries()
            
            # Limit items if needed
            if len(data) > limit:
                top_items = sorted(data, key=lambda x: x[1], reverse=True)[:limit-1]
                other_sum = sum(count for _, count in sorted(data, key=lambda x: x[1], reverse=True)[limit-1:])
                
                # Add top items
                for label, value in top_items:
                    series.append(str(label), value)
                
                # Add "Others" category
                if other_sum > 0:
                    series.append("Otros", other_sum)
            else:
                # Add all items
                for label, value in data:
                    series.append(str(label), value)
            
            # Calculate total for percentages
            total = sum(count for _, count in data)
            
            # Style the slices
            for slice_index in range(series.count()):
                slice = series.slices()[slice_index]
                percent = (slice.value() / total) * 100 if total > 0 else 0
                slice.setLabel(f"{slice.label()}: {percent:.1f}%")
                slice.setLabelVisible(True)
                
                # Explode slightly on hover
                slice.setExploded(True)
                slice.setExplodeDistanceFactor(0.05)
                
            # Create chart
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle(title)
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            chart.legend().setVisible(True)
            chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
            
            # Create chart view
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            logging.info(f"Pie chart '{title}' created successfully")
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
        
        return widget
    
    @staticmethod
    def create_error_widget(error_message):
        """Create a widget to display error messages"""
        label = QLabel(f"Error al crear el gráfico: {error_message}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background-color: #f0f0f0; padding: 20px; color: red;")
        return label