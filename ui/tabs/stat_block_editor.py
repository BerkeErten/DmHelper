"""Stat Block Editor using EntityProperty and EntitySection models."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QScrollArea, QSizePolicy, QFrame,
    QComboBox, QMessageBox, QApplication, QCheckBox, QListWidget, QListWidgetItem,
    QInputDialog, QTabWidget, QToolButton, QGraphicsDropShadowEffect, QMenu, QWidgetAction,
)
from PyQt6.QtGui import QFont, QDrag, QPainter, QPixmap, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QPoint
from datetime import datetime
from core.database import DatabaseManager
from core.dnd_utils import calculate_initiative_from_ability_score, proficiency_bonus_from_cr
from core.events import signal_hub
from models.entity import Entity
from models.entity_property import EntityProperty
from models.entity_section import EntitySection
import json
import re


class PropertiesDropWidget(QWidget):
    """Widget that accepts property drops with visual feedback."""
    
    def __init__(self, parent_editor):
        super().__init__()
        self.parent_editor = parent_editor
        self.setAcceptDrops(True)
        self.placeholder_widget = None
        self.drag_over = False
        self.original_style = STATBLOCK_PANEL_STYLE
        self.setStyleSheet(self.original_style)
    
    def dragEnterEvent(self, event):
        """Handle drag enter."""
        if event.mimeData().hasFormat("application/x-statblock-item"):
            data = event.mimeData().data("application/x-statblock-item").data().decode()
            if data.startswith("property:"):
                self.drag_over = True
                # Change background to lighter color
                if not self.original_style:
                    self.original_style = self.styleSheet()
                self.setStyleSheet("""
                    QWidget {
                        background-color: #5A6578;
                        border: 2px dashed #5DADE2;
                        border-radius: 4px;
                        padding: 4px;
                    }
                """)
                event.acceptProposedAction()
                self._show_placeholder(event.position().toPoint(), data)
                return
        event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move - update placeholder position."""
        if event.mimeData().hasFormat("application/x-statblock-item"):
            data = event.mimeData().data("application/x-statblock-item").data().decode()
            if data.startswith("property:"):
                event.acceptProposedAction()
                self._update_placeholder(event.position().toPoint(), data)
                return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave - remove visual feedback."""
        self.drag_over = False
        if self.original_style:
            self.setStyleSheet(self.original_style)
        self._hide_placeholder()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        """Handle drop."""
        self.drag_over = False
        if self.original_style:
            self.setStyleSheet(self.original_style)
        self._hide_placeholder()
        
        if not event.mimeData().hasFormat("application/x-statblock-item"):
            event.ignore()
            return
        
        data = event.mimeData().data("application/x-statblock-item").data().decode()
        if not data.startswith("property:"):
            event.ignore()
            return
        
        prop_key = data.split(":")[1]
        if prop_key not in self.parent_editor.property_widgets:
            event.ignore()
            return
        
        # Find drop position
        pos = event.position().toPoint()
        drop_row = self.parent_editor._find_drop_row(self.parent_editor.properties_grid, pos)
        
        # Reorder
        if prop_key in self.parent_editor.property_order:
            self.parent_editor.property_order.remove(prop_key)
        self.parent_editor.property_order.insert(drop_row, prop_key)
        self.parent_editor._refresh_properties_grid()
        
        event.acceptProposedAction()
    
    def _show_placeholder(self, pos, data):
        """Show placeholder at drop position."""
        prop_key = data.split(":")[1]
        if prop_key not in self.parent_editor.property_widgets:
            return
        
        # Get the dragged widget to match its size
        dragged_widget = self.parent_editor.property_widgets[prop_key]
        
        # Find drop row
        drop_row = self.parent_editor._find_drop_row(self.parent_editor.properties_grid, pos)
        
        # Create placeholder widget
        self._hide_placeholder()  # Remove existing if any
        
        self.placeholder_widget = QFrame()
        self.placeholder_widget.setStyleSheet("""
            QFrame {
                background-color: rgba(93, 173, 226, 0.2);
                border: 2px dashed #5DADE2;
                border-radius: 6px;
            }
        """)
        # Match the dragged widget's size dynamically
        dragged_height = dragged_widget.sizeHint().height()
        if dragged_height < 32:
            dragged_height = 32
        self.placeholder_widget.setFixedHeight(dragged_height)
        self.placeholder_widget.setMinimumHeight(32)
        # Set width to match container width
        self.placeholder_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Add placeholder at drop position
        self.parent_editor.properties_grid.addWidget(self.placeholder_widget, drop_row, 0)
    
    def _update_placeholder(self, pos, data):
        """Update placeholder position during drag."""
        prop_key = data.split(":")[1]
        if prop_key not in self.parent_editor.property_widgets:
            return
        
        dragged_widget = self.parent_editor.property_widgets[prop_key]
        drop_row = self.parent_editor._find_drop_row(self.parent_editor.properties_grid, pos)
        
        if self.placeholder_widget:
            # Update height to match dragged widget dynamically
            dragged_height = dragged_widget.sizeHint().height()
            if dragged_height < 32:
                dragged_height = 32
            self.placeholder_widget.setFixedHeight(dragged_height)
            # Remove and re-add at new position
            self.parent_editor.properties_grid.removeWidget(self.placeholder_widget)
            self.parent_editor.properties_grid.addWidget(self.placeholder_widget, drop_row, 0)
        else:
            self._show_placeholder(pos, data)
    
    def _hide_placeholder(self):
        """Hide placeholder widget."""
        if self.placeholder_widget:
            self.parent_editor.properties_grid.removeWidget(self.placeholder_widget)
            self.placeholder_widget.setParent(None)
            self.placeholder_widget.deleteLater()
            self.placeholder_widget = None


class SectionsDropWidget(QWidget):
    """Widget that accepts section drops with visual feedback."""
    
    def __init__(self, parent_editor):
        super().__init__()
        self.parent_editor = parent_editor
        self.setAcceptDrops(True)
        self.placeholder_widget = None
        self.drag_over = False
        self.original_style = STATBLOCK_PANEL_STYLE
        self.setStyleSheet(self.original_style)
    
    def dragEnterEvent(self, event):
        """Handle drag enter."""
        if event.mimeData().hasFormat("application/x-statblock-item"):
            data = event.mimeData().data("application/x-statblock-item").data().decode()
            if data.startswith("section:"):
                self.drag_over = True
                # Change background to lighter color
                if not self.original_style:
                    self.original_style = self.styleSheet()
                self.setStyleSheet("""
                    QWidget {
                        background-color: #5A6578;
                        border: 2px dashed #5DADE2;
                        border-radius: 4px;
                        padding: 4px;
                    }
                """)
                event.acceptProposedAction()
                self._show_placeholder(event.position().toPoint(), data)
                return
        event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move - update placeholder position."""
        if event.mimeData().hasFormat("application/x-statblock-item"):
            data = event.mimeData().data("application/x-statblock-item").data().decode()
            if data.startswith("section:"):
                event.acceptProposedAction()
                self._update_placeholder(event.position().toPoint(), data)
                return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave - remove visual feedback."""
        self.drag_over = False
        if self.original_style:
            self.setStyleSheet(self.original_style)
        self._hide_placeholder()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        """Handle drop."""
        self.drag_over = False
        if self.original_style:
            self.setStyleSheet(self.original_style)
        self._hide_placeholder()
        
        if not event.mimeData().hasFormat("application/x-statblock-item"):
            event.ignore()
            return
        
        data = event.mimeData().data("application/x-statblock-item").data().decode()
        if not data.startswith("section:"):
            event.ignore()
            return
        
        section_type = data.split(":")[1]
        if section_type not in self.parent_editor.section_widgets:
            event.ignore()
            return
        
        # Find drop position
        pos = event.position().toPoint()
        drop_row = self.parent_editor._find_drop_row(self.parent_editor.sections_grid, pos)
        
        # Reorder
        if section_type in self.parent_editor.section_order:
            self.parent_editor.section_order.remove(section_type)
        self.parent_editor.section_order.insert(drop_row, section_type)
        self.parent_editor._refresh_sections_grid()
        
        event.acceptProposedAction()
    
    def _show_placeholder(self, pos, data):
        """Show placeholder at drop position."""
        section_type = data.split(":")[1]
        if section_type not in self.parent_editor.section_widgets:
            return
        
        # Get the dragged widget to match its size
        dragged_widget = self.parent_editor.section_widgets[section_type]
        
        # Find drop row
        drop_row = self.parent_editor._find_drop_row(self.parent_editor.sections_grid, pos)
        
        # Create placeholder widget
        self._hide_placeholder()  # Remove existing if any
        
        self.placeholder_widget = QFrame()
        self.placeholder_widget.setStyleSheet("""
            QFrame {
                background-color: rgba(93, 173, 226, 0.2);
                border: 2px dashed #5DADE2;
                border-radius: 6px;
            }
        """)
        # Match the dragged widget's height dynamically
        dragged_height = dragged_widget.sizeHint().height()
        if dragged_height < 50:
            dragged_height = 50
        self.placeholder_widget.setFixedHeight(dragged_height)
        self.placeholder_widget.setMinimumHeight(50)
        # Set width to match container width
        self.placeholder_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Add placeholder at drop position
        self.parent_editor.sections_grid.addWidget(self.placeholder_widget, drop_row, 0)
    
    def _update_placeholder(self, pos, data):
        """Update placeholder position during drag."""
        section_type = data.split(":")[1]
        if section_type not in self.parent_editor.section_widgets:
            return
        
        dragged_widget = self.parent_editor.section_widgets[section_type]
        drop_row = self.parent_editor._find_drop_row(self.parent_editor.sections_grid, pos)
        
        if self.placeholder_widget:
            # Update height to match dragged widget dynamically
            dragged_height = dragged_widget.sizeHint().height()
            if dragged_height < 50:
                dragged_height = 50
            self.placeholder_widget.setFixedHeight(dragged_height)
            # Remove and re-add at new position
            self.parent_editor.sections_grid.removeWidget(self.placeholder_widget)
            self.parent_editor.sections_grid.addWidget(self.placeholder_widget, drop_row, 0)
        else:
            self._show_placeholder(pos, data)
    
    def _hide_placeholder(self):
        """Hide placeholder widget."""
        if self.placeholder_widget:
            self.parent_editor.sections_grid.removeWidget(self.placeholder_widget)
            self.placeholder_widget.setParent(None)
            self.placeholder_widget.deleteLater()
            self.placeholder_widget = None


class PropertyEntryWidget(QWidget):
    """Editable property entry (key-value pair) with drag support."""
    
    property_edited = pyqtSignal(str, str, str, str)  # old_key, new_key, old_value, new_value
    property_deleted = pyqtSignal(str)  # property_key
    drag_started = pyqtSignal(object)  # widget
    
    def __init__(self, prop_key: str, prop_value: str, parent=None):
        super().__init__(parent)
        self.prop_key = prop_key
        self.prop_value = prop_value
        self.editing_key = False
        self.editing_value = False
        self.drag_start_position = None
        self.is_dragging = False
        self.original_style = None
        self.setAcceptDrops(True)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)  # Minimal spacing for very tight layout
        
        # View mode: Display key: value format with bold key (inset for depth)
        self.view_label = QLabel()
        self.view_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_label.setStyleSheet("""
            QLabel {
                background-color: #3c3c3c;
                color: #CBD5E0;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                border: 1px solid #4c4c4c;
                border-top-color: #383838;
                border-left-color: #383838;
                border-right-color: #505050;
                border-bottom-color: #505050;
            }
            QLabel:hover { background-color: #454545; }
        """)
        self.view_label.mouseDoubleClickEvent = self.on_double_click
        self.view_label.setWordWrap(False)  # Disable word wrap to allow full width usage
        self.view_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        # Set text with bold key using HTML
        self.update_view_text()
        
        # Edit mode container (hidden by default)
        self.edit_container = QWidget()
        edit_layout = QHBoxLayout(self.edit_container)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(6)
        
        # Key label (display mode in edit)
        self.key_label = QPushButton(self.prop_key)
        self.key_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.key_label.setStyleSheet("""
            QPushButton {
                background-color: #4A5568;
                color: #E2E8F0;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                min-width: 80px;
                text-align: left;
                border: 1px solid #5a6478;
                border-top-color: #606c7a;
                border-left-color: #606c7a;
                border-right-color: #3d4758;
                border-bottom-color: #3d4758;
            }
            QPushButton:hover { background-color: #5A6478; }
        """)
        self.key_label.clicked.connect(self.start_edit_key)
        
        # Key edit field (editing mode)
        self.key_edit = QLineEdit(self.prop_key)
        self.key_edit.setStyleSheet("""
            QLineEdit {
                background-color: #4A5568;
                color: #E2E8F0;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 2px solid #5DADE2;
                min-width: 80px;
            }
        """)
        self.key_edit.setVisible(False)
        self.key_edit.editingFinished.connect(self.finish_edit_key)
        self.key_edit.returnPressed.connect(self.finish_edit_key)
        
        # Separator
        separator = QLabel(":")
        separator.setStyleSheet("color: #888888; font-size: 12px; font-weight: bold;")
        separator.setFixedWidth(10)
        
        # Value label (display mode in edit)
        self.value_label = QPushButton(self.prop_value)
        self.value_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.value_label.setStyleSheet("""
            QPushButton {
                background-color: #2D3748;
                color: #CBD5E0;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                min-width: 60px;
                text-align: left;
                border: 1px solid #3d4758;
                border-top-color: #454f60;
                border-left-color: #454f60;
                border-right-color: #252d3a;
                border-bottom-color: #252d3a;
            }
            QPushButton:hover { background-color: #3D4758; }
        """)
        self.value_label.clicked.connect(self.start_edit_value)
        
        # Value edit field (editing mode)
        self.value_edit = QLineEdit(self.prop_value)
        self.value_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2D3748;
                color: #CBD5E0;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                border: 2px solid #5DADE2;
                min-width: 60px;
            }
        """)
        self.value_edit.setVisible(False)
        self.value_edit.editingFinished.connect(self.finish_edit_value)
        self.value_edit.returnPressed.connect(self.finish_edit_value)
        
        # Delete button
        self.delete_btn = QPushButton("×")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.3);
                color: #FCA5A5;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.5);
                color: white;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_property)
        
        # Add drag handle
        drag_handle = QLabel("::")
        drag_handle.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 16px;
                padding: 4px;
                min-width: 20px;
                max-width: 20px;
            }
        """)
        drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)
        drag_handle.mousePressEvent = self.on_drag_handle_press
        drag_handle.mouseMoveEvent = self.on_drag_handle_move
        
        # Edit container layout
        edit_layout.addWidget(drag_handle)
        edit_layout.addWidget(self.key_label)
        edit_layout.addWidget(self.key_edit)
        edit_layout.addWidget(separator)
        edit_layout.addWidget(self.value_label)
        edit_layout.addWidget(self.value_edit)
        edit_layout.addWidget(self.delete_btn)
        edit_layout.addStretch()
        
        # Main layout - show view by default
        layout.addWidget(self.view_label)
        layout.addWidget(self.edit_container)
        self.edit_container.setVisible(False)
        # Removed addStretch() to allow view_label to expand fully
        
        self.setMinimumHeight(24)  # Minimal height for very tight spacing
        # Store original style
        self.original_style = self.styleSheet()
        self.is_edit_mode = False
    
    def update_view_text(self):
        """Update view label text with bold key."""
        self.view_label.setText(f'<b>{self.prop_key}</b>: {self.prop_value}')
    
    def on_double_click(self, event):
        """Handle double-click to enter edit mode."""
        self.enter_edit_mode()
    
    def enter_edit_mode(self):
        """Enter edit mode - show editable widgets."""
        self.is_edit_mode = True
        self.view_label.setVisible(False)
        self.edit_container.setVisible(True)
    
    def exit_edit_mode(self):
        """Exit edit mode - show view label."""
        self.is_edit_mode = False
        self.editing_key = False
        self.editing_value = False
        self.key_label.setVisible(True)
        self.key_edit.setVisible(False)
        self.value_label.setVisible(True)
        self.value_edit.setVisible(False)
        self.update_view_text()
        self.view_label.setVisible(True)
        self.edit_container.setVisible(False)
    
    def on_drag_handle_press(self, event):
        """Handle drag handle press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
    
    def on_drag_handle_move(self, event):
        """Handle drag handle move."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self.drag_start_position is None:
            return
        
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 
            QApplication.startDragDistance()):
            return
        
        # Start drag
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"property:{self.prop_key}")
        mime_data.setData("application/x-statblock-item", 
                         f"property:{self.prop_key}".encode())
        drag.setMimeData(mime_data)
        
        # Create drag pixmap
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint() - self.drag_start_position)
        
        # Change background color when dragging starts
        self.is_dragging = True
        if not self.original_style:
            self.original_style = self.styleSheet()
        self.setStyleSheet("""
            QWidget {
                background-color: #5A6578;
                border: 2px solid #5DADE2;
                border-radius: 6px;
                padding: 2px;
            }
        """)
        
        # Emit signal
        self.drag_started.emit(self)
        
        # Execute drag
        result = drag.exec(Qt.DropAction.MoveAction)
        
        # Restore original style when drag ends
        self.is_dragging = False
        if self.original_style:
            self.setStyleSheet(self.original_style)
        self.drag_start_position = None
    
    
    def start_edit_key(self):
        """Start editing the property key."""
        if self.editing_key:
            return
        self.editing_key = True
        self.key_label.setVisible(False)
        self.key_edit.setVisible(True)
        self.key_edit.setFocus()
        self.key_edit.selectAll()
    
    def finish_edit_key(self):
        """Finish editing the property key."""
        if not self.editing_key:
            return
        
        new_key = self.key_edit.text().strip()
        self.editing_key = False
        self.key_label.setVisible(True)
        self.key_edit.setVisible(False)
        
        if new_key and new_key != self.prop_key:
            old_key = self.prop_key
            self.prop_key = new_key
            self.key_label.setText(new_key)
            self.update_view_text()  # Update view label with bold key
            self.property_edited.emit(old_key, new_key, self.prop_value, self.prop_value)
        elif not new_key:
            self.delete_property()
            return
        
        # Exit edit mode after editing
        self.exit_edit_mode()
    
    def start_edit_value(self):
        """Start editing the property value."""
        if self.editing_value:
            return
        self.editing_value = True
        self.value_label.setVisible(False)
        self.value_edit.setVisible(True)
        self.value_edit.setFocus()
        self.value_edit.selectAll()
    
    def finish_edit_value(self):
        """Finish editing the property value."""
        if not self.editing_value:
            return
        
        new_value = self.value_edit.text().strip()
        self.editing_value = False
        self.value_label.setVisible(True)
        self.value_edit.setVisible(False)
        
        if new_value != self.prop_value:
            old_value = self.prop_value
            self.prop_value = new_value
            self.value_label.setText(new_value)
            self.update_view_text()  # Update view label with bold key
            self.property_edited.emit(self.prop_key, self.prop_key, old_value, new_value)
        
        # Exit edit mode after editing
        self.exit_edit_mode()
    
    def delete_property(self):
        """Delete this property entry."""
        self.property_deleted.emit(self.prop_key)
        self.setParent(None)
        self.deleteLater()


class SectionWidget(QWidget):
    """Collapsible section widget for traits, actions, etc. with drag support."""
    
    content_changed = pyqtSignal(str, str)  # section_type, new_content
    drag_started = pyqtSignal(object)  # widget
    
    def __init__(self, section_type: str, content: str = "", sort_order: int = 0, is_first: bool = False, compact: bool = False, parent=None):
        super().__init__(parent)
        self.section_type = section_type
        self.content = content
        self.sort_order = sort_order
        self.is_collapsed = False
        self.drag_start_position = None
        self.is_first = is_first
        self.compact = compact
        self.setAcceptDrops(True)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1 if self.compact else 2)
        
        # Edit mode container (hidden by default)
        self.edit_container = QWidget()
        edit_layout = QVBoxLayout(self.edit_container)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(1 if self.compact else 2)
        
        header_pad = 2 if self.compact else 4
        header_style = f"""
            QFrame {{
                background-color: #3c3c3c;
                border: 1px solid #4c4c4c;
                border-top-color: #505050;
                border-left-color: #505050;
                border-right-color: #383838;
                border-bottom-color: #383838;
                border-radius: 3px;
                padding: {header_pad}px;
            }}
        """ if self.compact else """
            QFrame {
                background-color: #3c3c3c;
                border: 1px solid #4c4c4c;
                border-top-color: #505050;
                border-left-color: #505050;
                border-right-color: #383838;
                border-bottom-color: #383838;
                border-radius: 4px;
                padding: 4px;
            }
        """
        header = QFrame()
        header.setStyleSheet(header_style)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(header_pad, header_pad, header_pad, header_pad)
        header_layout.setSpacing(2 if self.compact else 4)
        
        btn_sz = "10px" if self.compact else "12px"
        self.collapse_btn = QPushButton("▼" if not self.is_collapsed else "▶")
        self.collapse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #E2E8F0;
                border: none;
                font-size: {btn_sz};
                min-width: 16px;
                max-width: 16px;
            }}
        """)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        
        type_font = "10px" if self.compact else "14px"
        type_label = QLabel(self.section_type.replace("_", " ").title())
        type_label.setStyleSheet(f"font-size: {type_font}; font-weight: bold; color: #E2E8F0;")
        
        del_sz = "12px" if self.compact else "14px"
        del_wh = "18px" if self.compact else "24px"
        self.delete_btn = QPushButton("×")
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(239, 68, 68, 0.3);
                color: #FCA5A5;
                border: none;
                border-radius: 6px;
                font-size: {del_sz};
                font-weight: bold;
                min-width: {del_wh};
                max-width: {del_wh};
                min-height: {del_wh};
                max-height: {del_wh};
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.5);
                color: white;
            }}
        """)
        self.delete_btn.clicked.connect(self.delete_section)
        
        drag_sz = "12px" if self.compact else "16px"
        drag_handle = QLabel("::")
        drag_handle.setStyleSheet(f"""
            QLabel {{
                color: #888888;
                font-size: {drag_sz};
                padding: 2px;
                min-width: 14px;
                max-width: 14px;
            }}
        """)
        drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)
        drag_handle.mousePressEvent = self.on_drag_handle_press
        drag_handle.mouseMoveEvent = self.on_drag_handle_move
        
        header_layout.addWidget(drag_handle)
        header_layout.addWidget(self.collapse_btn)
        header_layout.addWidget(type_label)
        header_layout.addStretch()
        header_layout.addWidget(self.delete_btn)
        
        content_font = "10px" if self.compact else "11px"
        content_pad = "2px" if self.compact else "4px"
        self.content_edit = QTextEdit()
        self.content_edit.setPlainText(self.content)
        self.content_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: #2b2b2b;
                color: #E2E8F0;
                border: 1px solid #4c4c4c;
                border-top: none;
                border-left-color: #505050;
                border-right-color: #383838;
                border-bottom-color: #383838;
                border-radius: 0 0 3px 3px;
                padding: {content_pad};
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: {content_font};
            }}
        """)
        if self.compact:
            self.content_edit.setMaximumHeight(120)
        self.content_edit.textChanged.connect(self.on_content_changed)
        
        edit_layout.addWidget(header)
        edit_layout.addWidget(self.content_edit)
        
        if self.is_collapsed:
            self.content_edit.setVisible(False)
        
        view_font = "10px" if self.compact else "11px"
        view_pad = "1px 4px" if self.compact else "2px 6px"
        self.view_label = QLabel()
        self.view_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_label.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                color: #CBD5E0;
                padding: {view_pad};
                border-radius: 3px;
                font-size: {view_font};
                border: none;
            }}
        """)
        self.view_label.mouseDoubleClickEvent = self.on_double_click
        self.view_label.setWordWrap(True)
        self.view_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # Set text with bold section type using HTML
        self.update_view_text()
        
        # Main layout - show view by default
        layout.addWidget(self.view_label)
        layout.addWidget(self.edit_container)
        self.edit_container.setVisible(False)
        
        self.is_edit_mode = False
    
    def update_view_text(self):
        """Update view label text with bold section type."""
        section_type_display = self.section_type.replace('_', ' ').title()
        if self.content:
            # First section gets extra bold, others just bold section type
            if self.is_first:
                display_text = f'<b style="font-weight: bold;">{section_type_display}</b>: {self.content}'
            else:
                display_text = f'<b>{section_type_display}</b>: {self.content}'
        else:
            if self.is_first:
                display_text = f'<b style="font-weight: bold;">{section_type_display}</b>'
            else:
                display_text = f'<b>{section_type_display}</b>'
        self.view_label.setText(display_text)
    
    def on_double_click(self, event):
        """Handle double-click to enter edit mode."""
        self.enter_edit_mode()
    
    def enter_edit_mode(self):
        """Enter edit mode - show editable widgets."""
        self.is_edit_mode = True
        self.view_label.setVisible(False)
        self.edit_container.setVisible(True)
    
    def exit_edit_mode(self):
        """Exit edit mode - show view label."""
        self.is_edit_mode = False
        self.update_view_text()
        self.view_label.setVisible(True)
        self.edit_container.setVisible(False)
    
    def on_drag_handle_press(self, event):
        """Handle drag handle press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
    
    def on_drag_handle_move(self, event):
        """Handle drag handle move."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self.drag_start_position is None:
            return
        
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 
            QApplication.startDragDistance()):
            return
        
        # Start drag
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"section:{self.section_type}")
        mime_data.setData("application/x-statblock-item", 
                         f"section:{self.section_type}".encode())
        drag.setMimeData(mime_data)
        
        # Create drag pixmap
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint() - self.drag_start_position)
        
        # Emit signal
        self.drag_started.emit(self)
        
        # Execute drag
        drag.exec(Qt.DropAction.MoveAction)
        self.drag_start_position = None
    
    
    def toggle_collapse(self):
        """Toggle collapsed state."""
        self.is_collapsed = not self.is_collapsed
        self.content_edit.setVisible(not self.is_collapsed)
        self.collapse_btn.setText("▼" if not self.is_collapsed else "▶")
    
    def on_content_changed(self):
        """Handle content change."""
        self.content = self.content_edit.toPlainText()
        self.update_view_text()
        self.content_changed.emit(self.section_type, self.content)
    
    def delete_section(self):
        """Delete this section."""
        reply = QMessageBox.question(
            self, 
            "Delete Section",
            f"Are you sure you want to delete the '{self.section_type}' section?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Emit signal to parent to handle deletion
            if hasattr(self.parent(), 'on_section_deleted'):
                self.parent().on_section_deleted(self.section_type)
            self.setParent(None)
            self.deleteLater()


class AbilityScoresWidget(QWidget):
    """Widget for editing ability scores (STR, DEX, CON, INT, WIS, CHA)."""
    
    ability_score_changed = pyqtSignal(str, str)  # ability_key, new_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ability_inputs = {}  # key -> QLineEdit
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with title and remove button
        header_layout = QHBoxLayout()
        header_label = QLabel("Ability Scores")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        remove_btn = QPushButton("×")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.3);
                color: #FCA5A5;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.5);
                color: white;
            }
        """)
        remove_btn.clicked.connect(self.on_remove)
        header_layout.addWidget(remove_btn)
        layout.addLayout(header_layout)
        
        # Grid layout for ability scores (2 rows x 3 columns)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        ability_names = ["str", "dex", "con", "int", "wis", "cha"]
        ability_labels = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        
        for i, (ability_key, ability_label) in enumerate(zip(ability_names, ability_labels)):
            row = i // 3
            col = i % 3
            
            # Container for this ability
            ability_container = QWidget()
            ability_container.setStyleSheet("""
                QWidget {
                    background-color: #3c3c3c;
                    border-radius: 4px;
                    padding: 6px;
                }
            """)
            ability_layout = QVBoxLayout(ability_container)
            ability_layout.setContentsMargins(8, 6, 8, 6)
            ability_layout.setSpacing(4)
            
            # Label
            label = QLabel(ability_label)
            label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    color: #E2E8F0;
                    font-size: 11px;
                }
            """)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ability_layout.addWidget(label)
            
            # Input field
            input_field = QLineEdit()
            input_field.setPlaceholderText("e.g., 27 (+8)")
            input_field.setStyleSheet("""
                QLineEdit {
                    background-color: #2b2b2b;
                    color: #CBD5E0;
                    padding: 6px 8px;
                    border-radius: 4px;
                    border: 1px solid #4c4c4c;
                    font-size: 11px;
                }
                QLineEdit:focus {
                    border: 2px solid #5DADE2;
                }
            """)
            input_field.textChanged.connect(lambda value, key=ability_key: self.on_ability_changed(key, value))
            ability_layout.addWidget(input_field)
            self.ability_inputs[ability_key] = input_field
            
            grid_layout.addWidget(ability_container, row, col)
        
        layout.addLayout(grid_layout)
        
        # Frame styling
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #4c4c4c;
                border-radius: 6px;
                padding: 10px;
            }
        """)
    
    def on_ability_changed(self, key: str, value: str):
        """Handle ability score change."""
        self.ability_score_changed.emit(key, value)
    
    def set_ability_scores(self, scores: dict):
        """Set ability scores from dictionary."""
        for key, value in scores.items():
            if key in self.ability_inputs:
                # Block signals to avoid triggering save
                self.ability_inputs[key].blockSignals(True)
                self.ability_inputs[key].setText(str(value))
                self.ability_inputs[key].blockSignals(False)
    
    def get_ability_scores(self) -> dict:
        """Get ability scores as dictionary."""
        scores = {}
        for key, input_field in self.ability_inputs.items():
            value = input_field.text().strip()
            if value:
                scores[key] = value
        return scores
    
    def on_remove(self):
        """Handle remove button click - hide widget."""
        if hasattr(self.parent(), 'on_ability_scores_removed'):
            self.parent().on_ability_scores_removed()
        self.setParent(None)
        self.deleteLater()


class SavingThrowProficiencyWidget(QWidget):
    """Widget for editing saving throw proficiencies."""
    
    proficiency_changed = pyqtSignal(str, bool)  # ability_key, is_proficient
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.proficiency_checks = {}  # key -> QCheckBox
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with title and remove button
        header_layout = QHBoxLayout()
        header_label = QLabel("Saving Throw Proficiencies")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        remove_btn = QPushButton("×")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.3);
                color: #FCA5A5;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.5);
                color: white;
            }
        """)
        remove_btn.clicked.connect(self.on_remove)
        header_layout.addWidget(remove_btn)
        layout.addLayout(header_layout)
        
        # Grid layout for saving throw proficiencies (2 rows x 3 columns)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        ability_names = ["str", "dex", "con", "int", "wis", "cha"]
        ability_labels = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        
        for i, (ability_key, ability_label) in enumerate(zip(ability_names, ability_labels)):
            row = i // 3
            col = i % 3
            
            # Container for this ability
            ability_container = QWidget()
            ability_container.setStyleSheet("""
                QWidget {
                    background-color: #3c3c3c;
                    border-radius: 4px;
                    padding: 6px;
                }
            """)
            ability_layout = QHBoxLayout(ability_container)
            ability_layout.setContentsMargins(8, 6, 8, 6)
            ability_layout.setSpacing(6)
            
            # Checkbox
            checkbox = QCheckBox(ability_label)
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #E2E8F0;
                    font-size: 11px;
                    font-weight: bold;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #4c4c4c;
                    border-radius: 3px;
                    background-color: #2b2b2b;
                }
                QCheckBox::indicator:checked {
                    background-color: #5DADE2;
                    border-color: #5DADE2;
                }
                QCheckBox::indicator:hover {
                    border-color: #6DBDF2;
                }
            """)
            checkbox.stateChanged.connect(lambda state, key=ability_key: self.on_proficiency_changed(key, state == 2))
            ability_layout.addWidget(checkbox)
            self.proficiency_checks[ability_key] = checkbox
            
            grid_layout.addWidget(ability_container, row, col)
        
        layout.addLayout(grid_layout)
        
        # Frame styling
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #4c4c4c;
                border-radius: 6px;
                padding: 10px;
            }
        """)
    
    def on_proficiency_changed(self, key: str, is_proficient: bool):
        """Handle proficiency change."""
        self.proficiency_changed.emit(key, is_proficient)
    
    def set_proficiencies(self, proficiencies: dict):
        """Set proficiencies from dictionary."""
        for key, is_proficient in proficiencies.items():
            if key in self.proficiency_checks:
                # Block signals to avoid triggering save
                self.proficiency_checks[key].blockSignals(True)
                self.proficiency_checks[key].setChecked(bool(is_proficient))
                self.proficiency_checks[key].blockSignals(False)
    
    def get_proficiencies(self) -> dict:
        """Get proficiencies as dictionary."""
        proficiencies = {}
        for key, checkbox in self.proficiency_checks.items():
            proficiencies[key] = checkbox.isChecked()
        return proficiencies
    
    def on_remove(self):
        """Handle remove button click - parent handles removal and deletion."""
        if hasattr(self.parent(), 'on_saving_throw_proficiency_removed'):
            self.parent().on_saving_throw_proficiency_removed()


class SkillRowWidget(QWidget):
    """Row widget that emits on double-click for custom bonus."""
    double_clicked = pyqtSignal(str, str)  # skill_key, skill_label
    
    def __init__(self, skill_key: str, skill_label: str, parent=None):
        super().__init__(parent)
        self.skill_key = skill_key
        self.skill_label = skill_label
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.skill_key, self.skill_label)
        super().mouseDoubleClickEvent(event)


class SkillProficiencyWidget(QWidget):
    """Widget for editing skill proficiencies and expertise."""
    
    skill_changed = pyqtSignal(str, str)  # skill_name, proficiency_type (none/proficiency/expertise)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.skill_combos = {}  # skill_name -> QComboBox
        self.skill_custom_bonus = {}  # skill_name -> int (optional bonus)
        self.skill_bonus_labels = {}  # skill_name -> QLabel
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with title and remove button
        header_layout = QHBoxLayout()
        header_label = QLabel("Skill Proficiencies & Expertise")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        remove_btn = QPushButton("×")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.3);
                color: #FCA5A5;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.5);
                color: white;
            }
        """)
        remove_btn.clicked.connect(self.on_remove)
        header_layout.addWidget(remove_btn)
        layout.addLayout(header_layout)
        
        # Skills list
        skills = [
            ("acrobatics", "Acrobatics", "dex"),
            ("animal_handling", "Animal Handling", "wis"),
            ("arcana", "Arcana", "int"),
            ("athletics", "Athletics", "str"),
            ("deception", "Deception", "cha"),
            ("history", "History", "int"),
            ("insight", "Insight", "wis"),
            ("intimidation", "Intimidation", "cha"),
            ("investigation", "Investigation", "int"),
            ("medicine", "Medicine", "wis"),
            ("nature", "Nature", "int"),
            ("perception", "Perception", "wis"),
            ("performance", "Performance", "cha"),
            ("persuasion", "Persuasion", "cha"),
            ("religion", "Religion", "int"),
            ("sleight_of_hand", "Sleight of Hand", "dex"),
            ("stealth", "Stealth", "dex"),
            ("survival", "Survival", "wis"),
        ]
        # Iterate in alphabetical order (by display name); grid fills left-to-right, top-to-bottom
        skills_ordered = sorted(skills, key=lambda x: x[1].lower())
        
        # Grid layout for skills (3 columns)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        for i, (skill_key, skill_label, ability) in enumerate(skills_ordered):
            row = i // 3
            col = i % 3
            
            # Container for this skill (double-click opens custom bonus dialog)
            skill_container = SkillRowWidget(skill_key, skill_label)
            skill_container.setStyleSheet("""
                QWidget {
                    background-color: #3c3c3c;
                    border-radius: 4px;
                    padding: 6px;
                }
            """)
            skill_container.setToolTip("Çift tıkla: Custom bonus ekle/düzenle")
            skill_container.double_clicked.connect(self._on_skill_double_clicked)
            skill_layout = QHBoxLayout(skill_container)
            skill_layout.setContentsMargins(6, 4, 6, 4)
            skill_layout.setSpacing(6)
            
            # Skill label
            label = QLabel(skill_label)
            label.setStyleSheet("""
                QLabel {
                    color: #E2E8F0;
                    font-size: 10px;
                    min-width: 80px;
                }
            """)
            skill_layout.addWidget(label)
            
            # ComboBox for proficiency type
            combo = QComboBox()
            combo.addItems(["None", "Proficiency", "Expertise"])
            combo.setStyleSheet("""
                QComboBox {
                    background-color: #2b2b2b;
                    color: #CBD5E0;
                    padding: 4px 8px;
                    border-radius: 4px;
                    border: 1px solid #4c4c4c;
                    font-size: 10px;
                    min-width: 80px;
                }
                QComboBox:focus {
                    border: 2px solid #5DADE2;
                }
                QComboBox::drop-down {
                    border: none;
                }
            """)
            combo.currentTextChanged.connect(lambda text, key=skill_key: self.on_skill_changed(key, text.lower()))
            skill_layout.addWidget(combo)
            self.skill_combos[skill_key] = combo
            
            # Bonus label (e.g. "(+2)" when custom bonus is set)
            bonus_label = QLabel("")
            bonus_label.setStyleSheet("color: #9F7AEA; font-size: 9px; min-width: 28px;")
            skill_layout.addWidget(bonus_label)
            self.skill_bonus_labels[skill_key] = bonus_label
            
            grid_layout.addWidget(skill_container, row, col)
        
        layout.addLayout(grid_layout)
        
        # Frame styling
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #4c4c4c;
                border-radius: 6px;
                padding: 10px;
            }
        """)
    
    def _on_skill_double_clicked(self, skill_key: str, skill_label: str):
        """Open dialog to set custom bonus for this skill."""
        current = self.skill_custom_bonus.get(skill_key, 0)
        value, ok = QInputDialog.getInt(
            self,
            "Custom Bonus",
            f"{skill_label} için bonus (örn. +2 için 2, yoksa 0):",
            value=current,
            min=-5,
            max=20,
            step=1
        )
        if ok:
            if value == 0:
                self.skill_custom_bonus.pop(skill_key, None)
                if skill_key in self.skill_bonus_labels:
                    self.skill_bonus_labels[skill_key].setText("")
            else:
                self.skill_custom_bonus[skill_key] = value
                sign = "+" if value > 0 else ""
                self.skill_bonus_labels[skill_key].setText(f"({sign}{value})")
    
    def on_skill_changed(self, skill_key: str, proficiency_type: str):
        """Handle skill proficiency change."""
        self.skill_changed.emit(skill_key, proficiency_type)
    
    def set_skills(self, skills: dict):
        """Set skills from dictionary. Values can be str or dict with 'type' and optional 'bonus'."""
        for skill_key, val in skills.items():
            if skill_key not in self.skill_combos:
                continue
            # Block signals to avoid triggering save
            self.skill_combos[skill_key].blockSignals(True)
            proficiency_type = None
            bonus = 0
            if isinstance(val, dict):
                proficiency_type = val.get("type", "none").lower()
                bonus = int(val.get("bonus", 0))
            else:
                proficiency_type = str(val).lower() if val else "none"
            if proficiency_type == "none":
                self.skill_combos[skill_key].setCurrentIndex(0)
                if bonus != 0:
                    self.skill_custom_bonus[skill_key] = bonus
                    sign = "+" if bonus > 0 else ""
                    self.skill_bonus_labels[skill_key].setText(f"({sign}{bonus})")
                else:
                    self.skill_custom_bonus.pop(skill_key, None)
                    self.skill_bonus_labels[skill_key].setText("")
            elif proficiency_type == "proficiency":
                self.skill_combos[skill_key].setCurrentIndex(1)
            elif proficiency_type == "expertise":
                self.skill_combos[skill_key].setCurrentIndex(2)
            else:
                self.skill_combos[skill_key].setCurrentIndex(0)
            if bonus != 0:
                self.skill_custom_bonus[skill_key] = bonus
                sign = "+" if bonus > 0 else ""
                self.skill_bonus_labels[skill_key].setText(f"({sign}{bonus})")
            else:
                self.skill_custom_bonus.pop(skill_key, None)
                self.skill_bonus_labels[skill_key].setText("")
            self.skill_combos[skill_key].blockSignals(False)
    
    def get_skills(self) -> dict:
        """Get skills as dictionary. Includes custom bonus when set (even when type is None)."""
        skills = {}
        for skill_key, combo in self.skill_combos.items():
            proficiency_type = combo.currentText().lower()
            bonus = self.skill_custom_bonus.get(skill_key, 0)
            if proficiency_type != "none":
                if bonus != 0:
                    skills[skill_key] = {"type": proficiency_type, "bonus": bonus}
                else:
                    skills[skill_key] = proficiency_type
            elif bonus != 0:
                # Custom bonus only (no proficiency/expertise) - still save so viewer can show it
                skills[skill_key] = {"type": "none", "bonus": bonus}
        return skills
    
    def on_remove(self):
        """Handle remove button click - parent handles removal and deletion."""
        if hasattr(self.parent(), 'on_skill_proficiency_removed'):
            self.parent().on_skill_proficiency_removed()


class SavingThrowProficiencyWidget(QWidget):
    """Widget for editing saving throw proficiencies."""
    
    proficiency_changed = pyqtSignal(str, bool)  # ability_key, is_proficient
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.proficiency_checks = {}  # key -> QCheckBox
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with title and remove button
        header_layout = QHBoxLayout()
        header_label = QLabel("Saving Throw Proficiencies")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        remove_btn = QPushButton("×")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.3);
                color: #FCA5A5;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.5);
                color: white;
            }
        """)
        remove_btn.clicked.connect(self.on_remove)
        header_layout.addWidget(remove_btn)
        layout.addLayout(header_layout)
        
        # Grid layout for saving throw proficiencies (2 rows x 3 columns)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        ability_names = ["str", "dex", "con", "int", "wis", "cha"]
        ability_labels = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        
        for i, (ability_key, ability_label) in enumerate(zip(ability_names, ability_labels)):
            row = i // 3
            col = i % 3
            
            # Container for this ability
            ability_container = QWidget()
            ability_container.setStyleSheet("""
                QWidget {
                    background-color: #3c3c3c;
                    border-radius: 4px;
                    padding: 6px;
                }
            """)
            ability_layout = QHBoxLayout(ability_container)
            ability_layout.setContentsMargins(8, 6, 8, 6)
            ability_layout.setSpacing(6)
            
            # Checkbox
            checkbox = QCheckBox(ability_label)
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #E2E8F0;
                    font-size: 11px;
                    font-weight: bold;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #4c4c4c;
                    border-radius: 3px;
                    background-color: #2b2b2b;
                }
                QCheckBox::indicator:checked {
                    background-color: #5DADE2;
                    border-color: #5DADE2;
                }
                QCheckBox::indicator:hover {
                    border-color: #6DBDF2;
                }
            """)
            checkbox.stateChanged.connect(lambda state, key=ability_key: self.on_proficiency_changed(key, state == 2))
            ability_layout.addWidget(checkbox)
            self.proficiency_checks[ability_key] = checkbox
            
            grid_layout.addWidget(ability_container, row, col)
        
        layout.addLayout(grid_layout)
        
        # Frame styling
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 1px solid #4c4c4c;
                border-radius: 6px;
                padding: 10px;
            }
        """)
    
    def on_proficiency_changed(self, key: str, is_proficient: bool):
        """Handle proficiency change."""
        self.proficiency_changed.emit(key, is_proficient)
    
    def set_proficiencies(self, proficiencies: dict):
        """Set proficiencies from dictionary."""
        for key, is_proficient in proficiencies.items():
            if key in self.proficiency_checks:
                # Block signals to avoid triggering save
                self.proficiency_checks[key].blockSignals(True)
                self.proficiency_checks[key].setChecked(bool(is_proficient))
                self.proficiency_checks[key].blockSignals(False)
    
    def get_proficiencies(self) -> dict:
        """Get proficiencies as dictionary."""
        proficiencies = {}
        for key, checkbox in self.proficiency_checks.items():
            proficiencies[key] = checkbox.isChecked()
        return proficiencies
    
    def on_remove(self):
        """Handle remove button click - parent handles removal and deletion."""
        if hasattr(self.parent(), 'on_saving_throw_proficiency_removed'):
            self.parent().on_saving_throw_proficiency_removed()


# Section types shown in Lore subtab (same as Knowledge Base Info tab)
LORE_SECTION_TYPES = {"description", "background", "history", "personality", "appearance", "notes", "lore"}

# Depth-only styles: inset/raised borders on inner components, no overall color change
STATBLOCK_PANEL_STYLE = """
    QWidget {
        background-color: #3c3c3c;
        border: 1px solid #4c4c4c;
        border-top-color: #505050;
        border-left-color: #505050;
        border-right-color: #383838;
        border-bottom-color: #383838;
        border-radius: 6px;
        padding: 8px;
    }
"""
STATBLOCK_SCROLL_STYLE = """
    QScrollArea { border: none; }
    QScrollBar:vertical {
        background: #3c3c3c;
        width: 10px;
        border-radius: 5px;
        margin: 0;
        border: 1px solid #4c4c4c;
        border-top-color: #505050;
        border-left-color: #505050;
    }
    QScrollBar::handle:vertical {
        background: #4c4c4c;
        border-radius: 4px;
        min-height: 24px;
        border: 1px solid #555;
        border-bottom-color: #3a3a3a;
        border-right-color: #3a3a3a;
    }
    QScrollBar::handle:vertical:hover { background: #5a5a5a; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
STATBLOCK_SECTION_HEADER_STYLE = """
    font-size: 14px;
    font-weight: bold;
    color: #E2E8F0;
    padding: 6px 0;
    border-bottom: 1px solid #4c4c4c;
    margin-bottom: 4px;
"""
# Wrapper for each lore section so description, background, etc. are visually separate
STATBLOCK_LORE_SECTION_CARD_STYLE = """
    QFrame {
        background-color: #3c3c3c;
        border: 1px solid #4c4c4c;
        border-top-color: #505050;
        border-left-color: #505050;
        border-right-color: #383838;
        border-bottom-color: #383838;
        border-radius: 6px;
        padding: 6px;
        margin-bottom: 4px;
    }
"""
STATBLOCK_INNER_TABS_STYLE = """
    QTabWidget::pane {
        border: 1px solid #4c4c4c;
        border-top-color: #383838;
        border-left-color: #383838;
        border-right-color: #505050;
        border-bottom-color: #505050;
        border-radius: 6px;
        top: -1px;
        padding: 0;
    }
    QTabBar::tab {
        background: #3c3c3c;
        color: #AAAAAA;
        padding: 8px 16px;
        margin-right: 2px;
        border: 1px solid #4c4c4c;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-size: 12px;
    }
    QTabBar::tab:selected {
        background: transparent;
        color: #E2E8F0;
        font-weight: bold;
        border-bottom: 1px solid transparent;
    }
    QTabBar::tab:hover:!selected { background: #454545; }
"""


class StatBlockEditor(QWidget):
    """Complete stat block editor using EntityProperty and EntitySection."""

    attach_clicked = pyqtSignal(str, object)  # (source_kind, source_id)

    def __init__(self, parent=None, entity_id=None):
        super().__init__(parent)
        self.entity_id = entity_id
        self.entity = None
        self.property_widgets = {}  # key -> PropertyEntryWidget
        self.section_widgets = {}  # section_type -> SectionWidget
        self.property_order = []  # Order of properties
        self.section_order = []  # Order of sections
        self.dragged_property = None
        self.dragged_section = None
        self.setAcceptDrops(True)
        self.setup_ui()
        
        if self.entity_id:
            self.load_entity()
    
    def setup_ui(self):
        """Setup the UI components."""
        inner_tabs = QTabWidget()
        inner_tabs.setDocumentMode(True)
        inner_tabs.setStyleSheet(STATBLOCK_INNER_TABS_STYLE)
        stats_page = QWidget()
        stats_layout = QVBoxLayout(stats_page)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(12)
        
        # Title and name
        title_layout = QHBoxLayout()
        title_label = QLabel("Stat Block Editor")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #E2E8F0;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Entity name input
        name_label = QLabel("Name:")
        name_label.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Entity name...")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #E2E8F0;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #4c4c4c;
                border-top-color: #505050;
                border-left-color: #505050;
                border-right-color: #383838;
                border-bottom-color: #383838;
                font-size: 12px;
                min-width: 200px;
            }
            QLineEdit:focus { border-color: #5DADE2; }
        """)
        self.name_input.textChanged.connect(self.on_name_changed)
        title_layout.addWidget(name_label)
        title_layout.addWidget(self.name_input)
        
        # Save button (right side, before ability score button)
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #48BB78;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #38A169;
                border-top-color: #52c78a;
                border-left-color: #52c78a;
                border-right-color: #2d8558;
                border-bottom-color: #2d8558;
            }
            QPushButton:hover { background-color: #38A169; }
            QPushButton:pressed { background-color: #2F855A; }
        """)
        self.save_btn.clicked.connect(self.save_entity)
        title_layout.addWidget(self.save_btn)
        
        # Add Ability Score button (right side)
        self.add_ability_score_btn = QPushButton("+ Add Ability Score")
        self.add_ability_score_btn.setStyleSheet("""
            QPushButton {
                background-color: #5DADE2;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #6DBDF2;
                border-top-color: #7dc8f5;
                border-left-color: #7dc8f5;
                border-right-color: #4a9dd4;
                border-bottom-color: #4a9dd4;
            }
            QPushButton:hover { background-color: #6DBDF2; }
        """)
        self.add_ability_score_btn.clicked.connect(self.toggle_ability_scores)
        title_layout.addWidget(self.add_ability_score_btn)
        
        # Add Saving Throw Proficiency button
        self.add_saving_throw_btn = QPushButton("+ Add Save Prof.")
        self.add_saving_throw_btn.setStyleSheet("""
            QPushButton {
                background-color: #9F7AEA;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #B794F4;
                border-top-color: #c4a8f7;
                border-left-color: #c4a8f7;
                border-right-color: #8060c0;
                border-bottom-color: #8060c0;
            }
            QPushButton:hover { background-color: #B794F4; }
        """)
        self.add_saving_throw_btn.clicked.connect(self.toggle_saving_throw_proficiency)
        title_layout.addWidget(self.add_saving_throw_btn)
        
        # Add Skill Proficiency button
        self.add_skill_proficiency_btn = QPushButton("+ Add Skill Prof.")
        self.add_skill_proficiency_btn.setStyleSheet("""
            QPushButton {
                background-color: #ED8936;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #F6AD55;
                border-top-color: #f7b962;
                border-left-color: #f7b962;
                border-right-color: #c96f20;
                border-bottom-color: #c96f20;
            }
            QPushButton:hover { background-color: #F6AD55; }
        """)
        self.add_skill_proficiency_btn.clicked.connect(self.toggle_skill_proficiency)
        title_layout.addWidget(self.add_skill_proficiency_btn)
        # Attach button (right-aligned, next to add bonus buttons) with button shadow
        title_layout.addStretch()
        self.attach_btn = QToolButton()
        self.attach_btn.setText("\U0001f4ce")
        self.attach_btn.setToolTip("Attach")
        self.attach_btn.setFixedSize(28, 28)
        self.attach_btn.setStyleSheet("""
            QToolButton {
                background-color: #3c3c3c;
                border: 1px solid #4c4c4c;
                border-radius: 4px;
                font-size: 16px;
            }
            QToolButton:hover { background-color: #4a4a4a; border-color: #5c5c5c; }
            QToolButton:pressed { background-color: #2e2e2e; border-color: #383838; }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(6)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.attach_btn.setGraphicsEffect(shadow)
        self.attach_btn.clicked.connect(self._on_attach_btn_clicked)
        title_layout.addWidget(self.attach_btn)
        stats_layout.addLayout(title_layout)
        
        # CR and Initiative row
        cr_row = QHBoxLayout()
        cr_label = QLabel("CR:")
        cr_label.setStyleSheet("color: #E2E8F0; font-size: 12px; min-width: 24px;")
        self.cr_input = QLineEdit()
        self.cr_input.setPlaceholderText("e.g. 1/2, 1, 5")
        self.cr_input.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #E2E8F0;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #4c4c4c;
                border-top-color: #505050;
                border-left-color: #505050;
                border-right-color: #383838;
                border-bottom-color: #383838;
                font-size: 12px;
                max-width: 80px;
            }
            QLineEdit:focus { border-color: #5DADE2; }
        """)
        cr_row.addWidget(cr_label)
        cr_row.addWidget(self.cr_input)
        # Initiative (next to CR)
        init_label = QLabel("Initiative:")
        init_label.setStyleSheet("color: #E2E8F0; font-size: 12px; min-width: 52px; margin-left: 12px;")
        self.initiative_input = QLineEdit()
        self.initiative_input.setPlaceholderText("e.g. +2")
        self.initiative_input.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #E2E8F0;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #4c4c4c;
                border-top-color: #505050;
                border-left-color: #505050;
                border-right-color: #383838;
                border-bottom-color: #383838;
                font-size: 12px;
                max-width: 60px;
            }
            QLineEdit:focus { border-color: #5DADE2; }
        """)
        cr_row.addWidget(init_label)
        cr_row.addWidget(self.initiative_input)
        # Proficiency Bonus (next to Initiative)
        pb_label = QLabel("PB:")
        pb_label.setStyleSheet("color: #E2E8F0; font-size: 12px; min-width: 24px; margin-left: 12px;")
        self.proficiency_bonus_input = QLineEdit()
        self.proficiency_bonus_input.setPlaceholderText("e.g. +2")
        self.proficiency_bonus_input.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #E2E8F0;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #4c4c4c;
                border-top-color: #505050;
                border-left-color: #505050;
                border-right-color: #383838;
                border-bottom-color: #383838;
                font-size: 12px;
                max-width: 50px;
            }
            QLineEdit:focus { border-color: #5DADE2; }
        """)
        cr_row.addWidget(pb_label)
        cr_row.addWidget(self.proficiency_bonus_input)
        cr_row.addStretch()
        stats_layout.addLayout(cr_row)
        
        # Scroll area for content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(STATBLOCK_SCROLL_STYLE)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)
        
        # Ability Scores section (optional, initially hidden)
        self.ability_scores_widget = None
        self.ability_scores_index = -1  # Track position in scroll layout
        
        # Saving Throw Proficiency section (optional, initially hidden)
        self.saving_throw_proficiency_widget = None
        self.saving_throw_proficiency_index = -1
        
        # Skill Proficiency section (optional, initially hidden)
        self.skill_proficiency_widget = None
        self.skill_proficiency_index = -1
        
        # Properties section
        props_label = QLabel("Properties")
        props_label.setStyleSheet(STATBLOCK_SECTION_HEADER_STYLE)
        self.props_label = props_label  # Store reference
        self.scroll_layout.addWidget(props_label)
        
        self.properties_container = PropertiesDropWidget(self)
        self.properties_container.setMinimumHeight(48)
        self.properties_grid = QGridLayout(self.properties_container)
        self.properties_grid.setContentsMargins(4, 4, 4, 4)
        self.properties_grid.setSpacing(3)
        self.properties_grid.setColumnStretch(0, 1)
        self.scroll_layout.addWidget(self.properties_container)
        
        # Track property order
        self.property_order = []  # List of keys in display order
        
        # Add property button
        self.add_prop_btn = QPushButton("+ Add Property")
        self.add_prop_btn.setStyleSheet("""
            QPushButton {
                background-color: #5DADE2;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #6DBDF2;
                border-top-color: #7dc8f5;
                border-left-color: #7dc8f5;
                border-right-color: #4a9dd4;
                border-bottom-color: #4a9dd4;
            }
            QPushButton:hover { background-color: #6DBDF2; }
        """)
        self.add_prop_btn.clicked.connect(self.add_property_dialog)
        self.scroll_layout.addWidget(self.add_prop_btn)
        
        # Sections
        sections_label = QLabel("Sections")
        sections_label.setStyleSheet(STATBLOCK_SECTION_HEADER_STYLE)
        self.scroll_layout.addWidget(sections_label)
        
        self.sections_container = SectionsDropWidget(self)
        self.sections_container.setMinimumHeight(60)
        self.sections_grid = QGridLayout(self.sections_container)
        self.sections_grid.setContentsMargins(4, 4, 4, 4)
        self.sections_grid.setSpacing(6)
        self.sections_grid.setColumnStretch(0, 1)
        self.scroll_layout.addWidget(self.sections_container)
        
        # Track section order
        self.section_order = []  # List of section_types in display order
        
        # Add section button
        self.add_section_btn = QPushButton("+ Add Section")
        self.add_section_btn.setStyleSheet("""
            QPushButton {
                background-color: #5DADE2;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #6DBDF2;
                border-top-color: #7dc8f5;
                border-left-color: #7dc8f5;
                border-right-color: #4a9dd4;
                border-bottom-color: #4a9dd4;
            }
            QPushButton:hover { background-color: #6DBDF2; }
        """)
        self.add_section_btn.clicked.connect(self.add_section_dialog)
        self.scroll_layout.addWidget(self.add_section_btn)
        
        self.scroll_layout.addStretch()
        
        self.scroll.setWidget(self.scroll_content)
        stats_layout.addWidget(self.scroll)
        
        inner_tabs.addTab(stats_page, "Stat Block")
        
        # Lore tab: lore sections only (for Knowledge Base Info)
        lore_page = QWidget()
        lore_layout = QVBoxLayout(lore_page)
        lore_layout.setContentsMargins(12, 12, 12, 12)
        lore_layout.setSpacing(8)
        lore_header = QHBoxLayout()
        lore_heading = QLabel("Lore & flavor text (Knowledge Base → Info)")
        lore_heading.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        lore_header.addWidget(lore_heading)
        lore_header.addStretch()
        self.lore_save_btn = QPushButton("💾 Save")
        self.lore_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #48BB78;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #38A169;
                border-top-color: #52c78a;
                border-left-color: #52c78a;
                border-right-color: #2d8558;
                border-bottom-color: #2d8558;
            }
            QPushButton:hover { background-color: #38A169; }
        """)
        self.lore_save_btn.clicked.connect(self.save_entity)
        lore_header.addWidget(self.lore_save_btn)
        self.add_lore_section_btn = QPushButton("+ Add Lore Section")
        self.add_lore_section_btn.setStyleSheet("""
            QPushButton {
                background-color: #9F7AEA;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #B794F4;
                border-top-color: #c4a8f7;
                border-left-color: #c4a8f7;
                border-right-color: #8060c0;
                border-bottom-color: #8060c0;
            }
            QPushButton:hover { background-color: #B794F4; }
        """)
        self.add_lore_section_btn.clicked.connect(self.add_lore_section_dialog)
        lore_header.addWidget(self.add_lore_section_btn)
        lore_layout.addLayout(lore_header)
        lore_scroll = QScrollArea()
        lore_scroll.setWidgetResizable(True)
        lore_scroll.setStyleSheet(STATBLOCK_SCROLL_STYLE)
        lore_scroll_content = QWidget()
        lore_scroll_content.setMinimumHeight(80)
        self.lore_sections_layout = QVBoxLayout(lore_scroll_content)
        self.lore_sections_layout.setContentsMargins(4, 4, 4, 4)
        self.lore_sections_layout.setSpacing(4)
        self.lore_sections_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        lore_scroll.setWidget(lore_scroll_content)
        lore_layout.addWidget(lore_scroll)
        inner_tabs.addTab(lore_page, "Lore")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(inner_tabs)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    
    def _find_drop_row(self, grid_layout, pos):
        """Find which row to drop at based on position."""
        container = grid_layout.parent()
        if container is None:
            return 0
        
        # Convert position to container coordinates
        container_pos = container.mapFrom(self, pos)
        
        row = 0
        for i in range(grid_layout.rowCount()):
            item = grid_layout.itemAtPosition(i, 0)
            if item and item.widget():
                widget = item.widget()
                # Skip placeholder widget in calculations
                placeholder = getattr(container, 'placeholder_widget', None)
                if widget == placeholder:
                    continue
                widget_rect = widget.geometry()
                # Check if position is above the middle of this widget
                if container_pos.y() < widget_rect.top() + widget_rect.height() / 2:
                    return i
                row = i + 1
        return row
    
    def load_entity(self):
        """Load entity and its properties/sections."""
        if not self.entity_id:
            return
        
        try:
            with DatabaseManager() as db:
                self.entity = db.query(Entity).filter(Entity.id == self.entity_id).first()
                if not self.entity:
                    return
                
                # Load name
                self.name_input.setText(self.entity.name)
                
                # Clear existing widgets
                self._clear_widgets()
                
                # Load ability scores if they exist
                ability_score_keys = ["str", "dex", "con", "int", "wis", "cha"]
                ability_scores = {}
                for prop in self.entity.properties:
                    if prop.key in ability_score_keys:
                        ability_scores[prop.key] = prop.value
                
                if ability_scores:
                    # Show ability scores widget and populate it
                    if not self.ability_scores_widget:
                        self.show_ability_scores()
                    if self.ability_scores_widget:
                        self.ability_scores_widget.set_ability_scores(ability_scores)
                        self._update_initiative_from_dex()
                
                # Load saving throw proficiencies if they exist
                saving_throw_prop = None
                for prop in self.entity.properties:
                    if prop.key == "saving_throw_proficiencies":
                        saving_throw_prop = prop
                        break
                
                if saving_throw_prop:
                    try:
                        proficiencies = json.loads(saving_throw_prop.value)
                        if isinstance(proficiencies, dict):
                            if not self.saving_throw_proficiency_widget:
                                self.show_saving_throw_proficiency(from_load=True)
                            if self.saving_throw_proficiency_widget:
                                self.saving_throw_proficiency_widget.set_proficiencies(proficiencies)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Load skill proficiencies if they exist
                skill_prop = None
                for prop in self.entity.properties:
                    if prop.key == "skill_proficiencies":
                        skill_prop = prop
                        break
                
                if skill_prop:
                    try:
                        skills = json.loads(skill_prop.value)
                        if isinstance(skills, dict):
                            if not self.skill_proficiency_widget:
                                self.show_skill_proficiency(from_load=True)
                            if self.skill_proficiency_widget:
                                self.skill_proficiency_widget.set_skills(skills)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Load CR from challenge_rating or cr property
                for prop in self.entity.properties:
                    if prop.key in ("challenge_rating", "cr") and prop.value:
                        self.cr_input.setText(prop.value)
                        break
                
                # Load initiative from initiative property
                for prop in self.entity.properties:
                    if prop.key == "initiative" and prop.value:
                        self.initiative_input.setText(prop.value)
                        break
                
                # Load proficiency bonus from proficiency_bonus property
                for prop in self.entity.properties:
                    if prop.key == "proficiency_bonus" and prop.value:
                        self.proficiency_bonus_input.setText(prop.value)
                        break
                
                # Load properties (maintain order from database, excluding ability scores, CR, initiative, proficiency_bonus)
                for prop in self.entity.properties:
                    if prop.key not in ability_score_keys and prop.key not in ("challenge_rating", "cr", "initiative", "proficiency_bonus"):
                        self._add_property_widget(prop.key, prop.value)
                
                # Load sections (sorted by sort_order)
                sorted_sections = sorted(self.entity.sections, key=lambda s: s.sort_order)
                for i, section in enumerate(sorted_sections):
                    # First section should be bold
                    is_first = (i == 0)
                    self._add_section_widget(section.section_type, section.content, section.sort_order)
                    # Update is_first flag after widget is created
                    if section.section_type in self.section_widgets:
                        widget = self.section_widgets[section.section_type]
                        widget.is_first = is_first
                        # Update view text to reflect is_first status
                        if hasattr(widget, 'update_view_text'):
                            widget.update_view_text()
        except Exception as e:
            print(f"Error loading entity: {e}")
            import traceback
            traceback.print_exc()
    
    def _clear_widgets(self):
        """Clear all property and section widgets."""
        self.cr_input.clear()
        self.initiative_input.clear()
        self.proficiency_bonus_input.clear()
        # Clear ability scores widget
        if self.ability_scores_widget:
            self.ability_scores_widget.setParent(None)
            self.ability_scores_widget.deleteLater()
            self.ability_scores_widget = None
            self.ability_scores_index = -1
        
        # Clear saving throw proficiency widget
        if self.saving_throw_proficiency_widget:
            self.saving_throw_proficiency_widget.setParent(None)
            self.saving_throw_proficiency_widget.deleteLater()
            self.saving_throw_proficiency_widget = None
            self.saving_throw_proficiency_index = -1
        
        # Clear skill proficiency widget
        if self.skill_proficiency_widget:
            self.skill_proficiency_widget.setParent(None)
            self.skill_proficiency_widget.deleteLater()
            self.skill_proficiency_widget = None
            self.skill_proficiency_index = -1
        
        # Clear properties
        for widget in list(self.property_widgets.values()):
            widget.setParent(None)
            widget.deleteLater()
        self.property_widgets.clear()
        
        # Clear sections
        for widget in list(self.section_widgets.values()):
            widget.setParent(None)
            widget.deleteLater()
        self.section_widgets.clear()
    
    def _add_property_widget(self, key: str, value: str, position: int = None):
        """Add a property widget to the grid."""
        if key in self.property_widgets:
            return
        
        prop_widget = PropertyEntryWidget(key, value)
        prop_widget.property_edited.connect(self.on_property_edited)
        prop_widget.property_deleted.connect(self.on_property_deleted)
        prop_widget.drag_started.connect(lambda w: self._on_property_drag_start(w))
        
        # Add to grid
        if position is None:
            position = len(self.property_order)
        
        row = position
        # Add to grid (single column)
        self.properties_grid.addWidget(prop_widget, row, 0)
        
        # Update order
        if key not in self.property_order:
            self.property_order.insert(position, key)
        else:
            # Move to new position
            self.property_order.remove(key)
            self.property_order.insert(position, key)
        
        self.property_widgets[key] = prop_widget
        self._refresh_properties_grid()
    
    def _refresh_properties_grid(self):
        """Refresh properties grid layout."""
        # Remove all widgets (except placeholder if it exists)
        for i in reversed(range(self.properties_grid.count())):
            item = self.properties_grid.itemAt(i)
            if item:
                widget = item.widget()
                if widget and widget != getattr(self.properties_container, 'placeholder_widget', None):
                    self.properties_grid.removeWidget(widget)
        
        # Re-add in order
        for i, key in enumerate(self.property_order):
            if key in self.property_widgets:
                widget = self.property_widgets[key]
                # Check if placeholder exists at this position
                placeholder = getattr(self.properties_container, 'placeholder_widget', None)
                if placeholder and self.properties_grid.indexOf(placeholder) == i:
                    # Skip placeholder position, insert after
                    self.properties_grid.addWidget(widget, i + 1, 0)
                else:
                    self.properties_grid.addWidget(widget, i, 0)
    
    def _on_property_drag_start(self, widget):
        """Handle property drag start."""
        self.dragged_property = widget
    
    def _add_section_widget(self, section_type: str, content: str = "", sort_order: int = 0, position: int = None):
        """Add a section widget to the grid."""
        if section_type in self.section_widgets:
            return
        
        # Check if this is the first section
        is_first = len(self.section_order) == 0
        compact = section_type in LORE_SECTION_TYPES
        section_widget = SectionWidget(section_type, content, sort_order, is_first=is_first, compact=compact)
        section_widget.content_changed.connect(self.on_section_changed)
        section_widget.drag_started.connect(lambda w: self._on_section_drag_start(w))
        
        # Determine position
        if position is None:
            position = 0
            for i, st in enumerate(self.section_order):
                if st in self.section_widgets:
                    widget = self.section_widgets[st]
                    if hasattr(widget, 'sort_order') and widget.sort_order > sort_order:
                        position = i
                        break
                    position = i + 1
        
        if section_type not in self.section_order:
            self.section_order.insert(position, section_type)
        else:
            self.section_order.remove(section_type)
            self.section_order.insert(position, section_type)
        
        self.section_widgets[section_type] = section_widget
        self._refresh_sections_grid()
    
    def _refresh_sections_grid(self):
        """Refresh sections grid (mechanics) and lore layout (lore sections)."""
        # Remove all widgets from sections grid (except placeholder)
        for i in reversed(range(self.sections_grid.count())):
            item = self.sections_grid.itemAt(i)
            if item:
                widget = item.widget()
                if widget and widget != getattr(self.sections_container, 'placeholder_widget', None):
                    self.sections_grid.removeWidget(widget)
        # Clear lore layout (unwrap section widgets from card frames)
        while self.lore_sections_layout.count():
            item = self.lore_sections_layout.takeAt(0)
            w = item.widget() if item else None
            if w:
                # Card frame has one child: the section widget
                lay = w.layout()
                if lay and lay.count() > 0:
                    child_item = lay.takeAt(0)
                    if child_item and child_item.widget():
                        child_item.widget().setParent(None)
                w.deleteLater()
        
        mechanics_row = 0
        for i, section_type in enumerate(self.section_order):
            if section_type not in self.section_widgets:
                continue
            widget = self.section_widgets[section_type]
            widget.sort_order = i
            widget.is_first = (i == 0)
            if hasattr(widget, 'update_view_text'):
                widget.update_view_text()
            if section_type in LORE_SECTION_TYPES:
                card = QFrame()
                card.setStyleSheet(STATBLOCK_LORE_SECTION_CARD_STYLE)
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(0, 0, 0, 0)
                card_layout.setSpacing(0)
                card_layout.addWidget(widget)
                self.lore_sections_layout.addWidget(card)
            else:
                placeholder = getattr(self.sections_container, 'placeholder_widget', None)
                if placeholder and self.sections_grid.indexOf(placeholder) == mechanics_row:
                    self.sections_grid.addWidget(widget, mechanics_row + 1, 0)
                else:
                    self.sections_grid.addWidget(widget, mechanics_row, 0)
                mechanics_row += 1
    
    def _on_section_drag_start(self, widget):
        """Handle section drag start."""
        self.dragged_section = widget
    
    def add_property_dialog(self):
        """Show dialog to add a new property."""
        from PyQt6.QtWidgets import QInputDialog
        key, ok = QInputDialog.getText(self, "Add Property", "Property name:")
        if ok and key.strip():
            value, ok2 = QInputDialog.getText(self, "Add Property", f"Value for '{key}':")
            if ok2:
                self._add_property_widget(key.strip(), value.strip())
    
    def add_section_dialog(self):
        """Show dialog to add a new section (preset or custom)."""
        from PyQt6.QtWidgets import QInputDialog
        section_types = [
            "traits", "actions", "legendary_actions", "lair_actions",
            "description", "regional_effects", "reactions", "bonus_actions",
            "...Custom Section..."
        ]
        section_type, ok = QInputDialog.getItem(
            self, "Add Section", "Section type:", section_types, 0, False
        )
        if not ok or not section_type:
            return
        if section_type == "---":
            return
        if section_type == "Custom...":
            custom_name, ok_custom = QInputDialog.getText(
                self, "Add Custom Section", "Section name (e.g. Custom Notes, House Rules):"
            )
            if not ok_custom or not (custom_name and custom_name.strip()):
                return
            # Normalize: lowercase, spaces -> underscores
            section_type = custom_name.strip().lower().replace(" ", "_")
            if not section_type.replace("_", "").isalnum():
                section_type = "custom_" + "".join(c if c.isalnum() or c == "_" else "_" for c in section_type)
        if section_type in self.section_widgets:
            QMessageBox.information(
                self, "Add Section",
                f"A section named '{section_type}' already exists."
            )
            return
        max_order = max([w.sort_order for w in self.section_widgets.values()] + [-1])
        self._add_section_widget(section_type, "", max_order + 1)
    
    def add_lore_section_dialog(self):
        """Show dialog to add a lore section (for Knowledge Base Info tab)."""
        section_types = sorted(LORE_SECTION_TYPES)
        section_type, ok = QInputDialog.getItem(
            self, "Add Lore Section", "Section type:",
            section_types, 0, False
        )
        if not ok or not section_type:
            return
        if section_type in self.section_widgets:
            QMessageBox.information(
                self, "Add Lore Section",
                f"A section named '{section_type}' already exists."
            )
            return
        # Insert at top of list so new lore section appears at top of Lore tab
        self._add_section_widget(section_type, "", 0, position=0)
    
    def on_property_edited(self, old_key: str, new_key: str, old_value: str, new_value: str):
        """Handle property edit."""
        # Update widget mapping if key changed
        if old_key != new_key and old_key in self.property_widgets:
            widget = self.property_widgets.pop(old_key)
            self.property_widgets[new_key] = widget
    
    def on_property_deleted(self, key: str):
        """Handle property deletion."""
        if key in self.property_widgets:
            self.property_widgets.pop(key)
    
    def on_section_changed(self, section_type: str, content: str):
        """Handle section content change."""
        pass
    
    def on_section_deleted(self, section_type: str):
        """Handle section deletion."""
        if section_type in self.section_widgets:
            self.section_widgets.pop(section_type)
        if section_type in self.section_order:
            self.section_order.remove(section_type)
        self._refresh_sections_grid()
    
    def _on_add_relation_triggered(self):
        """Emit attach_clicked with context if entity is saved; else prompt to save first."""
        if self.entity_id is None:
            QMessageBox.information(
                self,
                "Save first",
                "Save the statblock first to add relations.",
            )
            return
        self.attach_clicked.emit("entity", self.entity_id)

    def _on_attach_btn_clicked(self):
        """Show popup menu with search bar and relation options list."""
        if self.entity_id is None:
            QMessageBox.information(
                self,
                "Save first",
                "Save the statblock first to add relations.",
            )
            return
        from ui.dialogs.add_relation_dialog import AddRelationPopupWidget
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #e0e0e0;
                padding: 0;
                border: 1px solid #4c4c4c;
                border-radius: 4px;
            }
        """)
        content = AddRelationPopupWidget("entity", self.entity_id, menu)
        action = QWidgetAction(menu)
        action.setDefaultWidget(content)
        menu.addAction(action)
        content.closed_requested.connect(menu.close)
        menu.exec(self.attach_btn.mapToGlobal(self.attach_btn.rect().bottomLeft()))
    
    def on_name_changed(self, name: str):
        """Handle name change."""
        # Emit signal to update tab title
        if hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'setTabText'):
            # Try to find our tab index and update title
            tab_widget = self.parent().parent()
            for i in range(tab_widget.count()):
                if tab_widget.widget(i) == self:
                    tab_widget.setTabText(i, name.strip() or "Stat Block")
                    break
    
    def toggle_ability_scores(self):
        """Toggle ability scores widget visibility."""
        if self.ability_scores_widget:
            self.on_ability_scores_removed()
        else:
            self.show_ability_scores()
    
    def show_ability_scores(self):
        """Show ability scores widget."""
        if self.ability_scores_widget:
            return
        
        # Create ability scores widget
        self.ability_scores_widget = AbilityScoresWidget(self)
        self.ability_scores_widget.ability_score_changed.connect(self.on_ability_score_changed)
        
        # Insert before Properties label
        # Find properties label index
        props_label_index = -1
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget == self.props_label:
                    props_label_index = i
                    break
        
        if props_label_index >= 0:
            self.scroll_layout.insertWidget(props_label_index, self.ability_scores_widget)
            self.ability_scores_index = props_label_index
        else:
            self.scroll_layout.insertWidget(0, self.ability_scores_widget)
            self.ability_scores_index = 0
        
        # Update button text
        self.add_ability_score_btn.setText("Remove Ability Score")
        # Sync initiative from DEX when ability scores are opened
        self._update_initiative_from_dex()

    def _parse_ability_score_to_int(self, value: str) -> int | None:
        """Parse ability score string (e.g. '14 (+2)' or '14') to integer score. Returns None if unparseable."""
        if not value or not value.strip():
            return None
        match = re.match(r"(\d+)", value.strip())
        if match:
            try:
                return int(match.group(1))
            except (ValueError, TypeError):
                pass
        return None

    def _update_initiative_from_dex(self):
        """Update initiative property from DEX ability score using dnd_utils.calculate_initiative_from_ability_score."""
        if not self.ability_scores_widget:
            return
        scores = self.ability_scores_widget.get_ability_scores()
        dex_raw = scores.get("dex") or scores.get("DEX")
        if dex_raw is None:
            return
        dex_int = self._parse_ability_score_to_int(dex_raw)
        if dex_int is None:
            return
        cr_text = self.cr_input.text().strip()
        proficiency_bonus = proficiency_bonus_from_cr(cr_text) if cr_text else 0
        initiative = calculate_initiative_from_ability_score(dex_int, proficiency_bonus, 0)
        value_str = str(initiative) if initiative < 0 else f"+{initiative}"
        self.initiative_input.setText(value_str)

    def on_ability_scores_removed(self):
        """Handle ability scores widget removal."""
        if self.ability_scores_widget:
            # Remove from layout
            self.scroll_layout.removeWidget(self.ability_scores_widget)
            
            # Delete widget
            self.ability_scores_widget.setParent(None)
            self.ability_scores_widget.deleteLater()
            self.ability_scores_widget = None
            self.ability_scores_index = -1
            
            # Update button text
            self.add_ability_score_btn.setText("+ Add Ability Score")
    
    def on_ability_score_changed(self, key: str, value: str):
        """Handle ability score change."""
        if key == "dex":
            self._update_initiative_from_dex()
    
    def _has_ability_scores_or_cr(self) -> bool:
        """Return True if entity has ability scores or proficiency_bonus/challenge_rating (CR)."""
        if self.ability_scores_widget:
            scores = self.ability_scores_widget.get_ability_scores()
            if scores:
                return True
        if self.cr_input.text().strip():
            return True
        cr_keys = ("proficiency_bonus", "challenge_rating", "cr")
        for key in cr_keys:
            if key in self.property_widgets:
                val = self.property_widgets[key].prop_value.strip()
                if val:
                    return True
        return False
    
    def toggle_saving_throw_proficiency(self):
        """Toggle saving throw proficiency widget visibility."""
        if self.saving_throw_proficiency_widget:
            self.on_saving_throw_proficiency_removed()
        else:
            self.show_saving_throw_proficiency()
    
    def show_saving_throw_proficiency(self, from_load: bool = False):
        """Show saving throw proficiency widget. If from_load, skip ability/CR check."""
        if self.saving_throw_proficiency_widget:
            return
        
        if not from_load and not self._has_ability_scores_or_cr():
            QMessageBox.warning(
                self,
                "Ability Score or CR Required",
                "Enter ability score first or enter challenge rating (CR) to use Save Throw proficiency."
            )
            return

        # Create saving throw proficiency widget
        self.saving_throw_proficiency_widget = SavingThrowProficiencyWidget(self)
        self.saving_throw_proficiency_widget.proficiency_changed.connect(self.on_saving_throw_proficiency_changed)
        
        # Insert after ability scores widget or before Properties label
        insert_index = -1
        if self.ability_scores_widget and self.ability_scores_index >= 0:
            insert_index = self.ability_scores_index + 1
        else:
            # Find properties label index
            for i in range(self.scroll_layout.count()):
                item = self.scroll_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if widget == self.props_label:
                        insert_index = i
                        break
        
        if insert_index >= 0:
            self.scroll_layout.insertWidget(insert_index, self.saving_throw_proficiency_widget)
            self.saving_throw_proficiency_index = insert_index
        else:
            self.scroll_layout.insertWidget(0, self.saving_throw_proficiency_widget)
            self.saving_throw_proficiency_index = 0
        
        # Update button text
        self.add_saving_throw_btn.setText("Remove Save Prof.")
    
    def on_saving_throw_proficiency_removed(self):
        """Handle saving throw proficiency widget removal."""
        widget = self.saving_throw_proficiency_widget
        self.saving_throw_proficiency_widget = None
        self.saving_throw_proficiency_index = -1
        self.add_saving_throw_btn.setText("+ Add Save Prof.")
        if widget is None:
            return
        try:
            from PyQt6.sip import isdeleted
            if isdeleted(widget):
                return
        except Exception:
            pass
        try:
            self.scroll_layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        except RuntimeError:
            pass  # widget already deleted
    
    def on_saving_throw_proficiency_changed(self, key: str, is_proficient: bool):
        """Handle saving throw proficiency change."""
        pass
    
    def toggle_skill_proficiency(self):
        """Toggle skill proficiency widget visibility."""
        if self.skill_proficiency_widget:
            self.on_skill_proficiency_removed()
        else:
            self.show_skill_proficiency()
    
    def show_skill_proficiency(self, from_load: bool = False):
        """Show skill proficiency widget. If from_load, skip ability/CR check."""
        if self.skill_proficiency_widget:
            return
        
        if not from_load and not self._has_ability_scores_or_cr():
            QMessageBox.warning(
                self,
                "Ability Score or CR Required",
                "Enter ability score first or enter challenge rating (CR) to use Skill proficiency."
            )
            return

        # Create skill proficiency widget
        self.skill_proficiency_widget = SkillProficiencyWidget(self)
        self.skill_proficiency_widget.skill_changed.connect(self.on_skill_proficiency_changed)
        
        # Insert after saving throw proficiency widget or before Properties label
        insert_index = -1
        if self.saving_throw_proficiency_widget and self.saving_throw_proficiency_index >= 0:
            insert_index = self.saving_throw_proficiency_index + 1
        elif self.ability_scores_widget and self.ability_scores_index >= 0:
            insert_index = self.ability_scores_index + 1
        else:
            # Find properties label index
            for i in range(self.scroll_layout.count()):
                item = self.scroll_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if widget == self.props_label:
                        insert_index = i
                        break
        
        if insert_index >= 0:
            self.scroll_layout.insertWidget(insert_index, self.skill_proficiency_widget)
            self.skill_proficiency_index = insert_index
        else:
            self.scroll_layout.insertWidget(0, self.skill_proficiency_widget)
            self.skill_proficiency_index = 0
        
        # Update button text
        self.add_skill_proficiency_btn.setText("Remove Skill Prof.")
    
    def on_skill_proficiency_removed(self):
        """Handle skill proficiency widget removal."""
        widget = self.skill_proficiency_widget
        self.skill_proficiency_widget = None
        self.skill_proficiency_index = -1
        self.add_skill_proficiency_btn.setText("+ Add Skill Prof.")
        if widget is None:
            return
        try:
            from PyQt6.sip import isdeleted
            if isdeleted(widget):
                return
        except Exception:
            pass
        try:
            self.scroll_layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        except RuntimeError:
            pass  # widget already deleted
    
    def on_skill_proficiency_changed(self, skill_key: str, proficiency_type: str):
        """Handle skill proficiency change."""
        pass
    
    def save_entity(self):
        """Save entity, properties, and sections to database."""
        # Get entity name (use placeholder if empty)
        entity_name = self.name_input.text().strip() or "New Stat Block"
        
        try:
            with DatabaseManager() as db:
                # Eager load relationships to ensure all data is available
                from sqlalchemy.orm import joinedload
                
                # Create new entity if entity_id is None
                if not self.entity_id:
                    entity = Entity(type="statblock", name=entity_name)
                    db.add(entity)
                    db.flush()  # Flush to get the entity ID
                    self.entity_id = entity.id
                    # Update tab title after entity is created
                    self.on_name_changed(entity_name)
                else:
                    entity = db.query(Entity).options(
                        joinedload(Entity.properties),
                        joinedload(Entity.sections)
                    ).filter(Entity.id == self.entity_id).first()
                
                if not entity:
                    return
                
                # Update name (or set it if this is a new entity)
                entity.name = entity_name
                entity.updated_at = datetime.utcnow()
                
                # Get existing properties and sections (will be empty for new entities)
                existing_props_list = list(entity.properties) if entity.properties else []
                existing_props = {p.key: p for p in existing_props_list}
                existing_sections_list = list(entity.sections) if entity.sections else []
                existing_sections = {s.section_type: s for s in existing_sections_list}
                
                # Save CR (Challenge Rating) from dedicated field
                cr_value = self.cr_input.text().strip()
                if "challenge_rating" in existing_props:
                    existing_props["challenge_rating"].value = cr_value
                else:
                    if cr_value:
                        new_prop = EntityProperty(entity_id=entity.id, key="challenge_rating", value=cr_value)
                        db.add(new_prop)
                
                # Save Initiative from dedicated field
                initiative_value = self.initiative_input.text().strip()
                if "initiative" in existing_props:
                    existing_props["initiative"].value = initiative_value
                else:
                    if initiative_value:
                        new_prop = EntityProperty(entity_id=entity.id, key="initiative", value=initiative_value)
                        db.add(new_prop)
                
                # Save Proficiency Bonus from dedicated field
                pb_value = self.proficiency_bonus_input.text().strip()
                if "proficiency_bonus" in existing_props:
                    existing_props["proficiency_bonus"].value = pb_value
                else:
                    if pb_value:
                        new_prop = EntityProperty(entity_id=entity.id, key="proficiency_bonus", value=pb_value)
                        db.add(new_prop)
                
                # Save ability scores if widget exists
                ability_score_keys = ["str", "dex", "con", "int", "wis", "cha"]
                if self.ability_scores_widget:
                    ability_scores = self.ability_scores_widget.get_ability_scores()
                    for key, value in ability_scores.items():
                        if key in existing_props:
                            existing_props[key].value = value
                        else:
                            new_prop = EntityProperty(entity_id=entity.id, key=key, value=value)
                            db.add(new_prop)
                
                # Save saving throw proficiencies if widget exists
                if self.saving_throw_proficiency_widget:
                    proficiencies = self.saving_throw_proficiency_widget.get_proficiencies()
                    proficiencies_json = json.dumps(proficiencies)
                    if "saving_throw_proficiencies" in existing_props:
                        existing_props["saving_throw_proficiencies"].value = proficiencies_json
                    else:
                        new_prop = EntityProperty(entity_id=entity.id, key="saving_throw_proficiencies", value=proficiencies_json)
                        db.add(new_prop)
                
                # Save skill proficiencies if widget exists
                if self.skill_proficiency_widget:
                    skills = self.skill_proficiency_widget.get_skills()
                    skills_json = json.dumps(skills)
                    if "skill_proficiencies" in existing_props:
                        existing_props["skill_proficiencies"].value = skills_json
                    else:
                        new_prop = EntityProperty(entity_id=entity.id, key="skill_proficiencies", value=skills_json)
                        db.add(new_prop)
                
                # Save properties (excluding ability scores)
                for key, widget in self.property_widgets.items():
                    if key not in ability_score_keys:  # Skip ability scores
                        value = widget.prop_value
                        if key in existing_props:
                            existing_props[key].value = value
                        else:
                            new_prop = EntityProperty(entity_id=entity.id, key=key, value=value)
                            db.add(new_prop)
                
                # Remove deleted properties (including ability scores if widget was removed)
                current_keys = set(self.property_widgets.keys())
                current_keys.add("challenge_rating")  # CR is saved from cr_input
                current_keys.add("initiative")  # Initiative is saved from initiative_input
                current_keys.add("proficiency_bonus")  # PB is saved from proficiency_bonus_input
                if self.ability_scores_widget:
                    # Add ability scores from widget
                    current_keys.update(self.ability_scores_widget.get_ability_scores().keys())
                
                # Add saving throw proficiencies and skill proficiencies to current_keys if widgets exist
                if self.saving_throw_proficiency_widget:
                    current_keys.add("saving_throw_proficiencies")
                if self.skill_proficiency_widget:
                    current_keys.add("skill_proficiencies")
                
                for prop in existing_props_list:
                    if prop.key not in current_keys:
                        db.delete(prop)
                
                # Save sections
                for section_type, widget in self.section_widgets.items():
                    content = widget.content
                    sort_order = widget.sort_order
                    if section_type in existing_sections:
                        existing_sections[section_type].content = content
                        existing_sections[section_type].sort_order = sort_order
                    else:
                        new_section = EntitySection(
                            entity_id=entity.id,
                            section_type=section_type,
                            content=content,
                            sort_order=sort_order
                        )
                        db.add(new_section)
                
                # Remove deleted sections
                current_section_types = set(self.section_widgets.keys())
                for section in existing_sections_list:
                    if section.section_type not in current_section_types:
                        db.delete(section)
                
                db.commit()
                
                # Force refresh of entity to get latest data
                db.refresh(entity)
                
                # Emit signal that entity was saved - this will update statblock viewer
                signal_hub.data_saved.emit(entity.type, {"id": entity.id, "name": entity.name})
                
                # Visual feedback for save button
                original_text = self.save_btn.text()
                self.save_btn.setText("✓ Saved")
                self.save_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2F855A;
                        color: white;
                        padding: 6px 12px;
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: 600;
                        border: none;
                    }
                """)
                QTimer.singleShot(1500, lambda: self.save_btn.setText(original_text) or 
                                 self.save_btn.setStyleSheet("""
                                     QPushButton {
                                         background-color: #48BB78;
                                         color: white;
                                         padding: 6px 12px;
                                         border-radius: 6px;
                                         font-size: 11px;
                                         font-weight: 600;
                                         border: none;
                                     }
                                     QPushButton:hover {
                                         background-color: #38A169;
                                     }
                                     QPushButton:pressed {
                                         background-color: #2F855A;
                                     }
                                 """))
        except Exception as e:
            print(f"Error saving entity: {e}")
            import traceback
            traceback.print_exc()
            # Show error feedback on button
            original_text = self.save_btn.text()
            self.save_btn.setText("✗ Error")
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F56565;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    border: none;
                }
            """)
            QTimer.singleShot(2000, lambda: self.save_btn.setText(original_text) or 
                             self.save_btn.setStyleSheet("""
                                 QPushButton {
                                     background-color: #48BB78;
                                     color: white;
                                     padding: 6px 12px;
                                     border-radius: 6px;
                                     font-size: 11px;
                                     font-weight: 600;
                                     border: none;
                                 }
                                 QPushButton:hover {
                                     background-color: #38A169;
                                 }
                                 QPushButton:pressed {
                                     background-color: #2F855A;
                                 }
                             """))
    
    def set_entity_id(self, entity_id: str):
        """Set entity ID and load."""
        self.entity_id = entity_id
        if entity_id:
            self.load_entity()
    
    def create_new_entity(self, entity_type: str = "creature", name: str = "New Entity"):
        """Create a new entity and load it."""
        try:
            with DatabaseManager() as db:
                new_entity = Entity(type=entity_type, name=name)
                db.add(new_entity)
                db.commit()
                self.entity_id = new_entity.id
                self.load_entity()
                return new_entity.id
        except Exception as e:
            print(f"Error creating entity: {e}")
            import traceback
            traceback.print_exc()
            return None

