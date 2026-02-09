"""Tag widget for displaying and editing tags."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QSize, pyqtSignal
import hashlib


class TagWidget(QWidget):
    """Editable tag widget with squircle shape and vibrant color."""
    
    tag_edited = pyqtSignal(str, str)  # old_name, new_name
    tag_deleted = pyqtSignal(str)  # tag_name
    
    # Vibrant colors palette
    VIBRANT_COLORS = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
        "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B739", "#82E0AA",
        "#F1948A", "#52BE80", "#5DADE2", "#F39C12", "#D35400",
        "#E74C3C", "#3498DB", "#9B59B6", "#1ABC9C", "#F1C40F"
    ]
    
    def __init__(self, tag_name: str, tag_color: str = None, parent=None):
        super().__init__(parent)
        self.tag_name = tag_name
        self.tag_color = tag_color or self._generate_color(tag_name)
        self.editing = False
        self.init_ui()
    
    def _generate_color(self, name: str) -> str:
        """Generate a vibrant color for a tag based on its name."""
        # Use hash to consistently assign colors
        hash_val = int(hashlib.md5(name.encode()).hexdigest(), 16)
        color_index = hash_val % len(self.VIBRANT_COLORS)
        return self.VIBRANT_COLORS[color_index]
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Tag label (display mode) - capsule shape using QPushButton for better border-radius support
        self.tag_label = QPushButton(self.tag_name)
        self.tag_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tag_label.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.tag_color};
                color: white;
                padding: 6px 16px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 500;
                border: none;
                outline: none;
                min-width: 0px;
            }}
            QPushButton:hover {{
                background-color: {self.tag_color};
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                background-color: {self.tag_color};
                opacity: 0.8;
            }}
        """)
        self.tag_label.setContentsMargins(0, 0, 0, 0)
        self.tag_label.clicked.connect(self.start_edit)
        
        # Tag edit field (editing mode) - capsule shape
        self.tag_edit = QLineEdit(self.tag_name)
        self.tag_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.tag_color};
                color: white;
                padding: 6px 16px;
                border-radius: 12px;
                font-size: 11px;
                border: 2px solid white;
                min-width: 0px;
            }}
        """)
        self.tag_edit.setContentsMargins(0, 0, 0, 0)
        self.tag_edit.setVisible(False)
        self.tag_edit.editingFinished.connect(self.finish_edit)
        self.tag_edit.returnPressed.connect(self.finish_edit)
        
        # Delete button (X) - circular
        self.delete_btn = QPushButton("×")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.3);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
        """)
        self.delete_btn.clicked.connect(self.delete_tag)
        
        layout.addWidget(self.tag_label)
        layout.addWidget(self.tag_edit)
        layout.addWidget(self.delete_btn)
        
        # Set proper height to accommodate text with padding
        self.setMinimumHeight(28)
    
    def start_edit(self, event=None):
        """Start editing the tag name."""
        if self.editing:
            return
        self.editing = True
        self.tag_label.setVisible(False)
        self.tag_edit.setVisible(True)
        self.tag_edit.setFocus()
        self.tag_edit.selectAll()
    
    def start_edit_event(self, event):
        """Handle mouse event for starting edit."""
        self.start_edit()
    
    def finish_edit(self):
        """Finish editing the tag name."""
        if not self.editing:
            return
        
        new_name = self.tag_edit.text().strip()
        self.editing = False
        self.tag_label.setVisible(True)
        self.tag_edit.setVisible(False)
        
        if new_name and new_name != self.tag_name:
            old_name = self.tag_name
            self.tag_name = new_name
            # Update button text or label text depending on widget type
            if isinstance(self.tag_label, QPushButton):
                self.tag_label.setText(new_name)
            else:
                self.tag_label.setText(new_name)
            # Regenerate color if name changed significantly
            self.tag_color = self._generate_color(new_name)
            self.update_styles()
            self.tag_edited.emit(old_name, new_name)
        elif not new_name:
            # Empty name - delete the tag
            self.delete_tag()
    
    def delete_tag(self):
        """Delete this tag."""
        self.tag_deleted.emit(self.tag_name)
        self.setParent(None)
        self.deleteLater()
    
    def update_styles(self):
        """Update the stylesheet with new color."""
        capsule_radius = 12  # Rounded capsule shape
        if isinstance(self.tag_label, QPushButton):
            self.tag_label.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.tag_color};
                    color: white;
                    padding: 6px 16px;
                    border-radius: {capsule_radius}px;
                    font-size: 11px;
                    font-weight: 500;
                    border: none;
                    outline: none;
                    min-width: 0px;
                }}
                QPushButton:hover {{
                    background-color: {self.tag_color};
                    opacity: 0.9;
                }}
                QPushButton:pressed {{
                    background-color: {self.tag_color};
                    opacity: 0.8;
                }}
            """)
        else:
            self.tag_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {self.tag_color};
                    color: white;
                    padding: 6px 16px;
                    border-radius: {capsule_radius}px;
                    font-size: 11px;
                    font-weight: 500;
                    border: none;
                }}
            """)
        self.tag_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.tag_color};
                color: white;
                padding: 6px 16px;
                border-radius: {capsule_radius}px;
                font-size: 11px;
                border: 2px solid white;
            }}
        """)
    
    def get_tag_name(self) -> str:
        """Get the current tag name."""
        return self.tag_name
    
    def get_tag_color(self) -> str:
        """Get the current tag color."""
        return self.tag_color


class EmptyTagWidget(QWidget):
    """Empty tag widget for adding new tags."""
    
    tag_added = pyqtSignal(str)  # tag_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editing = False
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Empty tag input - capsule shape
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tag name...")
        self.tag_input.setStyleSheet("""
            QLineEdit {
                background-color: #3A3A3A;
                color: #CCCCCC;
                padding: 4px 12px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 500;
                border: 2px solid #555555;
            }
            QLineEdit:focus {
                border: 2px solid #5DADE2;
                background-color: #404040;
            }
        """)
        self.tag_input.setVisible(False)
        self.tag_input.editingFinished.connect(self.finish_add)
        self.tag_input.returnPressed.connect(self.finish_add)
        
        # Clickable button to add tag - capsule shape using QPushButton for better border-radius
        self.add_label = QPushButton("+ Add tag")
        self.add_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_label.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: #AAAAAA;
                padding: 4px 12px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 500;
                border: 2px dashed #666666;
                outline: none;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
                color: #CCCCCC;
                border: 2px dashed #777777;
            }
            QPushButton:pressed {
                background-color: #353535;
                color: #DDDDDD;
            }
        """)
        self.add_label.clicked.connect(self.start_add)
        
        layout.addWidget(self.add_label)
        layout.addWidget(self.tag_input)
        
        self.setMinimumHeight(24)
    
    def start_add(self, event=None):
        """Start adding a new tag."""
        if self.editing:
            return
        self.editing = True
        self.add_label.setVisible(False)
        self.tag_input.setVisible(True)
        self.tag_input.setFocus()
    
    def finish_add(self):
        """Finish adding a new tag."""
        if not self.editing:
            return
        
        tag_name = self.tag_input.text().strip()
        self.editing = False
        self.add_label.setVisible(True)
        self.tag_input.setVisible(False)
        self.tag_input.clear()
        
        if tag_name:
            self.tag_added.emit(tag_name)

