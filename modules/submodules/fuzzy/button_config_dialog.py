from PyQt6.QtWidgets import (QDialog, QGridLayout, QComboBox, QPushButton, 
                            QDialogButtonBox, QLabel, QVBoxLayout, QScrollArea, QWidget)
from PyQt6.QtCore import Qt

class ButtonConfigDialog(QDialog):
    """Dialog for configuring which buttons are visible in the buttons_container."""
    
    def __init__(self, parent=None, button_data=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Botones")
        self.resize(600, 500)  # Increased size to accommodate more buttons
        
        self.button_data = button_data or []
        self.all_buttons = []  # Will be filled with all available buttons
        self.combo_grid = []   # Will hold references to all comboboxes
        self.rows = 4
        self.cols = 4
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        main_layout = QVBoxLayout(self)
        
        # Add instructions
        instructions = QLabel("Selecciona qué botones mostrar en cada posición:")
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)
        
        # Create a scroll area to hold the grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Create grid layout for comboboxes (4x4 or larger)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)  # Add spacing between comboboxes
        
        # Create grid of comboboxes
        for row in range(self.rows):
            combo_row = []
            for col in range(self.cols):
                combo = QComboBox()
                # First option is always "None" (no button)
                combo.addItem("Ninguno", "none")
                
                # We'll add available buttons later in set_available_buttons
                
                # Add row/column label to help with positioning
                label = QLabel(f"Fila {row+1}, Columna {col+1}")
                
                # Add the label and combo to the grid
                grid_layout.addWidget(label, row*2, col)
                grid_layout.addWidget(combo, row*2+1, col)
                
                combo_row.append(combo)
            self.combo_grid.append(combo_row)
        
        # Add the grid to the scroll area
        scroll_layout.addLayout(grid_layout)
        
        # Spacer to push everything to the top
        scroll_layout.addStretch()
        
        # Set the content widget
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # Add OK/Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def set_available_buttons(self, buttons):
        """Set available buttons and update comboboxes."""
        self.all_buttons = buttons
        
        print(f"Setting available buttons in dialog: {[b['name'] for b in buttons]}")
        print(f"Current configuration: {self.button_data}")
        
        # Update all comboboxes
        for row_idx, row in enumerate(self.combo_grid):
            for col_idx, combo in enumerate(row):
                # Clear and add the default "None" option
                combo.clear()
                combo.addItem("Ninguno", "none")
                
                # Add all available buttons
                for button in self.all_buttons:
                    combo.addItem(button['display_name'], button['name'])
                
                # Set current value if exists in button_data
                idx = row_idx * self.cols + col_idx
                if idx < len(self.button_data):
                    current_value = self.button_data[idx]
                    if current_value != "none":
                        # Find the index of the button in the combobox
                        button_idx = combo.findData(current_value)
                        if button_idx >= 0:
                            combo.setCurrentIndex(button_idx)
                            print(f"Setting combobox ({row_idx},{col_idx}) to {current_value} at index {button_idx}")
    
    def get_button_configuration(self):
        """Get the button configuration from the dialog."""
        config = []
        for row in self.combo_grid:
            for combo in row:
                config.append(combo.currentData())
        return config