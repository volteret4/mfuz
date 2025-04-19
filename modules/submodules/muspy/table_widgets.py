# submodules/muspy/table_widgets.py
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt

class NumericTableWidgetItem(QTableWidgetItem):
    """A QTableWidgetItem that sorts numerically"""
    
    def __lt__(self, other):
        try:
            # Convert both items to numbers for comparison
            return float(self.text().replace(',', '')) < float(other.text().replace(',', ''))
        except (ValueError, TypeError):
            # Fall back to default string comparison if numeric conversion fails
            return super().__lt__(other)


class DateTableWidgetItem(QTableWidgetItem):
    """A QTableWidgetItem that sorts dates chronologically"""
    
    def __init__(self, date_text, date_format="%Y-%m-%d"):
        super().__init__(date_text)
        self.date_text = date_text
        self.date_format = date_format
        
        # Try to convert to datetime for sorting
        try:
            from datetime import datetime
            self.date_obj = datetime.strptime(date_text, date_format)
            self.valid_date = True
        except (ValueError, TypeError):
            # If conversion fails, store None and fall back to string comparison
            self.date_obj = None
            self.valid_date = False
    
    def __lt__(self, other):
        # If both items have valid dates, compare them directly
        if self.valid_date and hasattr(other, 'valid_date') and other.valid_date:
            return self.date_obj < other.date_obj
        
        # If this item has a valid date but other doesn't, this should come first
        if self.valid_date and hasattr(other, 'valid_date') and not other.valid_date:
            return True
            
        # If other item has a valid date but this doesn't, other should come first
        if not self.valid_date and hasattr(other, 'valid_date') and other.valid_date:
            return False
            
        # Fall back to default string comparison if neither are valid dates
        return super().__lt__(other)