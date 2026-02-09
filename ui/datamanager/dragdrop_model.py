"""Drag and drop model for Data Manager."""
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtWidgets import QTreeWidget


class DraggableTreeWidget(QTreeWidget):
    """Tree widget with custom drag behavior."""
    
    def startDrag(self, supportedActions):
        """Start drag operation with custom mime data."""
        item = self.currentItem()
        
        if item and item.parent():  # Only drag child items (entities)
            mime_data = QMimeData()
            entity_text = item.text(0)
            entity_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Set plain text
            mime_data.setText(entity_text)
            
            # Optionally set custom data
            if entity_data:
                mime_data.setData("application/x-dmhelper-entity", 
                                str(entity_data).encode())
            
            drag = self.startDrag(supportedActions)
            
        super().startDrag(supportedActions)

