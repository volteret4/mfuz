from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                           QCheckBox, QPushButton, QFrame, QSpinBox, QComboBox,
                           QLabel)
from PyQt6.QtCore import Qt, pyqtSignal

class SearchPanel(QWidget):
    """
    Search panel component for music browser.
    Handles basic and advanced search functionality.
    """
    
    # Signals
    searchRequested = pyqtSignal(str)  # Emitted when search should be performed
    filterRequested = pyqtSignal(str)  # Emitted when a filter should be applied
    
    def __init__(self, parent=None):
        """
        Initialize search panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set up UI
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # Search box container
        self.search_frame = QFrame()
        self.search_frame.setObjectName("search_frame")
        self.search_layout = QHBoxLayout(self.search_frame)
        self.search_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setObjectName("search_box")
        self.search_box.setPlaceholderText(
            "a:artista - b:álbum - g:género - l:sello - t:título - aa:album-artist - br:bitrate - d:fecha - w:semanas - m:meses - y:años - am:mes/año - ay:año"
        )
        self.search_layout.addWidget(self.search_box)
        
        # Advanced options checkbox
        self.advanced_settings_check = QCheckBox("Más")
        self.advanced_settings_check.setObjectName("advanced_settings_check")
        self.search_layout.addWidget(self.advanced_settings_check)
        
        # Custom buttons (initially hidden)
        self.custom_button1 = QPushButton("Reproduciendo")
        self.custom_button1.setObjectName("custom_button1")
        self.custom_button1.setVisible(False)
        self.search_layout.addWidget(self.custom_button1)
        
        self.custom_button2 = QPushButton("Script 2")
        self.custom_button2.setObjectName("custom_button2")
        self.custom_button2.setVisible(False)
        self.search_layout.addWidget(self.custom_button2)
        
        self.custom_button3 = QPushButton("Script 3")
        self.custom_button3.setObjectName("custom_button3")
        self.custom_button3.setVisible(False)
        self.search_layout.addWidget(self.custom_button3)
        
        # Add search frame to main layout
        self.layout.addWidget(self.search_frame)
        
        # Advanced settings container (initially hidden)
        self.advanced_settings_container = QFrame()
        self.advanced_settings_container.setObjectName("advanced_settings_container")
        self.advanced_settings_container.setVisible(False)
        self.advanced_layout = QHBoxLayout(self.advanced_settings_container)
        self.advanced_layout.setSpacing(10)
        self.advanced_layout.setContentsMargins(0, 0, 0, 0)
        
        # Time filter frame
        self.time_filter_frame = QFrame()
        self.time_filter_frame.setObjectName("time_filter_frame")
        self.time_filter_layout = QHBoxLayout(self.time_filter_frame)
        self.time_filter_layout.setSpacing(5)
        self.time_filter_layout.setContentsMargins(0, 0, 0, 0)
        
        # Time value
        self.time_value = QSpinBox()
        self.time_value.setObjectName("time_value")
        self.time_value.setMinimum(1)
        self.time_value.setMaximum(999)
        self.time_value.setValue(1)
        self.time_filter_layout.addWidget(self.time_value)
        
        # Time unit
        self.time_unit = QComboBox()
        self.time_unit.setObjectName("time_unit")
        self.time_unit.addItems(["Semanas", "Meses", "Años"])
        self.time_filter_layout.addWidget(self.time_unit)
        
        # Apply time filter button
        self.apply_time_filter = QPushButton("Aplicar")
        self.apply_time_filter.setObjectName("apply_time_filter")
        self.time_filter_layout.addWidget(self.apply_time_filter)
        
        # Add time filter frame to advanced layout
        self.advanced_layout.addWidget(self.time_filter_frame)
        
        # Add separator
        self.separator1 = QLabel("|")
        self.separator1.setObjectName("separator1")
        self.separator1.setStyleSheet("color: rgba(169, 177, 214, 0.5);")
        self.advanced_layout.addWidget(self.separator1)
        
        # Month/Year filter frame
        self.month_year_frame = QFrame()
        self.month_year_frame.setObjectName("month_year_frame")
        self.month_year_layout = QHBoxLayout(self.month_year_frame)
        self.month_year_layout.setSpacing(5)
        self.month_year_layout.setContentsMargins(0, 0, 0, 0)
        
        # Month combo
        self.month_combo = QComboBox()
        self.month_combo.setObjectName("month_combo")
        self.month_combo.addItems([f"{i:02d}" for i in range(1, 13)])
        self.month_year_layout.addWidget(self.month_combo)
        
        # Year spin box
        self.year_spin = QSpinBox()
        self.year_spin.setObjectName("year_spin")
        self.year_spin.setMinimum(1900)
        self.year_spin.setMaximum(2100)
        from PyQt6.QtCore import QDate
        self.year_spin.setValue(QDate.currentDate().year())
        self.month_year_layout.addWidget(self.year_spin)
        
        # Apply month/year button
        self.apply_month_year = QPushButton("Filtrar por Mes/Año")
        self.apply_month_year.setObjectName("apply_month_year")
        self.month_year_layout.addWidget(self.apply_month_year)
        
        # Add month/year frame to advanced layout
        self.advanced_layout.addWidget(self.month_year_frame)
        
        # Add separator
        self.separator2 = QLabel("|")
        self.separator2.setObjectName("separator2")
        self.separator2.setStyleSheet("color: rgba(169, 177, 214, 0.5);")
        self.advanced_layout.addWidget(self.separator2)
        
        # Year filter frame
        self.year_frame = QFrame()
        self.year_frame.setObjectName("year_frame")
        self.year_layout = QHBoxLayout(self.year_frame)
        self.year_layout.setSpacing(5)
        self.year_layout.setContentsMargins(0, 0, 0, 0)
        
        # Year only spin box
        self.year_only_spin = QSpinBox()
        self.year_only_spin.setObjectName("year_only_spin")
        self.year_only_spin.setMinimum(1900)
        self.year_only_spin.setMaximum(2100)
        self.year_only_spin.setValue(QDate.currentDate().year())
        self.year_layout.addWidget(self.year_only_spin)
        
        # Apply year button
        self.apply_year = QPushButton("Filtrar por Año")
        self.apply_year.setObjectName("apply_year")
        self.year_layout.addWidget(self.apply_year)
        
        # Add year frame to advanced layout
        self.advanced_layout.addWidget(self.year_frame)
        
        # Add advanced settings container to main layout
        self.layout.addWidget(self.advanced_settings_container)
        
        # Connect signals
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect internal signals."""
        # Search box signals
        self.search_box.textChanged.connect(self._on_search_text_changed)
        self.search_box.returnPressed.connect(self._on_search_requested)
        
        # Advanced settings checkbox
        self.advanced_settings_check.stateChanged.connect(self._toggle_advanced_settings)
        
        # Filter buttons
        self.apply_time_filter.clicked.connect(self._on_time_filter_clicked)
        self.apply_month_year.clicked.connect(self._on_month_year_filter_clicked)
        self.apply_year.clicked.connect(self._on_year_filter_clicked)
        
        # Custom buttons
        self.custom_button1.clicked.connect(self._on_custom_button1_clicked)
        
    def _on_search_text_changed(self, text):
        """Handle search box text changes."""
        # Optionally implement debounced search here
        pass
        
    def _on_search_requested(self):
        """Handle search requests."""
        query = self.search_box.text()
        self.searchRequested.emit(query)
        
    def _toggle_advanced_settings(self, state):
        """
        Show or hide advanced settings.
        
        Args:
            state: Checkbox state
        """
        is_checked = (state == Qt.CheckState.Checked.value)
        
        # Show/hide advanced settings container
        self.advanced_settings_container.setVisible(is_checked)
        
        # Show/hide custom buttons
        for button in [self.custom_button1, self.custom_button2, self.custom_button3]:
            button.setVisible(is_checked)
            
    def _on_time_filter_clicked(self):
        """Handle time filter button click."""
        value = self.time_value.value()
        unit_idx = self.time_unit.currentIndex()
        
        # Map unit index to filter code
        unit_code = ['w', 'm', 'y'][unit_idx]
        
        # Create filter string
        filter_str = f"{unit_code}:{value}"
        
        # Update search box text
        self.search_box.setText(filter_str)
        
        # Emit filter signal
        self.filterRequested.emit(filter_str)
        
    def _on_month_year_filter_clicked(self):
        """Handle month/year filter button click."""
        month = self.month_combo.currentText()
        year = self.year_spin.value()
        
        # Create filter string
        filter_str = f"am:{month}/{year}"
        
        # Update search box text
        self.search_box.setText(filter_str)
        
        # Emit filter signal
        self.filterRequested.emit(filter_str)
        
    def _on_year_filter_clicked(self):
        """Handle year filter button click."""
        year = self.year_only_spin.value()
        
        # Create filter string
        filter_str = f"ay:{year}"
        
        # Update search box text
        self.search_box.setText(filter_str)
        
        # Emit filter signal
        self.filterRequested.emit(filter_str)
        
    def _on_custom_button1_clicked(self):
        """Handle custom button 1 click (Playing Now)."""
        # This method would be implemented in MusicBrowser and connected
        # to this signal
        pass
        
    def set_search_text(self, text):
        """
        Set the search box text.
        
        Args:
            text (str): Text to set
        """
        self.search_box.setText(text)
        self.searchRequested.emit(text)
        
    def get_advanced_buttons(self):
        """
        Get list of advanced buttons.
        
        Returns:
            list: List of QPushButton objects
        """
        return [self.custom_button1, self.custom_button2, self.custom_button3]
        
    def set_custom_button_handlers(self, button1_handler=None, button2_handler=None, button3_handler=None):
        """
        Set handlers for custom buttons.
        
        Args:
            button1_handler: Function to handle button 1 click
            button2_handler: Function to handle button 2 click
            button3_handler: Function to handle button 3 click
        """
        if button1_handler:
            self.custom_button1.clicked.disconnect()
            self.custom_button1.clicked.connect(button1_handler)
            
        if button2_handler:
            self.custom_button2.clicked.disconnect()
            self.custom_button2.clicked.connect(button2_handler)
            
        if button3_handler:
            self.custom_button3.clicked.disconnect()
            self.custom_button3.clicked.connect(button3_handler)