from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QWidget
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, Qt

class CollapsibleGroupBox(QGroupBox):
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(True)
        
        # Store original height for animation
        self.original_height = 0
        self.collapsed_height = 35  # Height when collapsed (just the title)
        self.is_collapsed = False
        
        # Capture content and wrap in a widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 5, 0, 0)
        
        # Add to parent layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 25, 5, 5)
        self.main_layout.addWidget(self.content_widget)
        
        # Connect signals
        self.toggled.connect(self.toggle_collapsed)
        
        # Initialize animation
        self.animation = QPropertyAnimation(self, b"minimumHeight")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def add_widget(self, widget):
        """Add a widget to the content layout"""
        self.content_layout.addWidget(widget)
        
    def add_layout(self, layout):
        """Add a layout to the content layout"""
        self.content_layout.addLayout(layout)
        
    def showEvent(self, event):
        """Capture initial height when shown"""
        super().showEvent(event)
        if self.original_height == 0:
            self.original_height = self.height()
        
    def toggle_collapsed(self, checked):
        """Animate collapse/expand when toggled"""
        self.is_collapsed = not checked
        
        if not checked:  # Collapse
            self.animation.setStartValue(self.height())
            self.animation.setEndValue(self.collapsed_height)
            self.content_widget.setVisible(False)
        else:  # Expand
            self.animation.setStartValue(self.height())
            self.animation.setEndValue(self.original_height)
            self.content_widget.setVisible(True)
            
        self.animation.start()