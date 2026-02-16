"""StatBlock Viewer Widget - Custom list viewer for entities, notes, and more."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QScrollArea, QFrame, QSizePolicy, QGridLayout, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox,
    QMessageBox, QSplitter, QMenu, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextDocument, QPainter, QColor, QBrush
from core.database import DatabaseManager
from core.dice_roller import DiceRoller
from core.dnd_utils import proficiency_bonus_from_cr, calculate_initiative_from_ability_score
from core.events import signal_hub
from models.entity import Entity
from models.note import Note
import json
import re
import random


# Condition name -> hex color (shared for list indicators and conditions summary tooltip)
CONDITION_COLORS = {
    "blinded": "#FF6B6B",
    "charmed": "#FFD93D",
    "deafened": "#95E1D3",
    "frightened": "#6C5CE7",
    "grappled": "#A29BFE",
    "incapacitated": "#FD79A8",
    "invisible": "#74B9FF",
    "paralyzed": "#E17055",
    "petrified": "#636E72",
    "poisoned": "#00B894",
    "prone": "#FDCB6E",
    "restrained": "#E84393",
    "stunned": "#FF7675",
    "unconscious": "#2D3436",
    "exhaustion": "#6C5CE7",
}


class CombatTrackerWidget(QWidget):
    """Widget showing combatants in a side panel (like statblock viewer)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.combatants = []  # list of {"type": "entity"/"note", "id": "...", "name": "..."}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Combat Tracker")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #E2E8F0;")
        header.addWidget(title)
        header.addStretch()

        self.clear_tracker_btn = QPushButton("Clear")
        self.clear_tracker_btn.setStyleSheet("""
            QPushButton {
                background-color: #5c3c3c;
                color: #E2E8F0;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #6c4c4c; }
        """)
        self.clear_tracker_btn.clicked.connect(self._clear_combatants)
        header.addWidget(self.clear_tracker_btn)
        layout.addLayout(header)

        self.combatants_list = QListWidget()
        self.combatants_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.combatants_list.customContextMenuRequested.connect(self._show_context_menu)
        self.combatants_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #E2E8F0;
                border: 1px solid #4c4c4c;
                border-radius: 6px;
                font-size: 11px;
            }
            QListWidget::item { padding: 6px; }
            QListWidget::item:selected { background-color: #3d5a80; }
            QListWidget::item:hover { background-color: #3c3c3c; }
        """)
        layout.addWidget(self.combatants_list)

        self.setMinimumWidth(200)

    def add_combatant(self, item: dict):
        """Add a combatant; use item['result'] if provided, else roll 1d20+initiative. Allow duplicates (same entity → Name 2, Name 3, ...)."""
        mod = item.get("initiative")
        if mod is None:
            mod = 0
        if "result" not in item:
            expr = f"1d20+{mod}" if mod >= 0 else f"1d20{mod}"
            roll_result = DiceRoller.roll(expr)
            item["result"] = roll_result.total if roll_result else mod
        # Index for same entity (1st, 2nd, 3rd...) so we can show "Goblin", "Goblin 2", "Goblin 3"
        same_count = sum(1 for c in self.combatants if c.get("type") == item.get("type") and c.get("id") == item.get("id"))
        item["display_index"] = same_count + 1
        self.combatants.append(item)
        self._refresh_list()

    def _refresh_list(self):
        """Display combatants sorted by initiative result descending. Same entity added again: Name 2, Name 3. (result) right. Conditions as colored dots."""
        def sort_key(c):
            res = c.get("result")
            if res is None:
                res = -999
            return (-res, (c.get("name") or "Unknown").lower())
        self.combatants.sort(key=sort_key)
        self.combatants_list.clear()
        for i, c in enumerate(self.combatants):
            icon = "📦" if c.get("type") == "entity" else "📝"
            base_name = c.get("name", "Unknown")
            idx = c.get("display_index", 1)
            display_name = base_name if idx == 1 else f"{base_name} {idx}"
            result = c.get("result")
            conditions = c.get("conditions", [])
            list_item = QListWidgetItem()
            list_item.setSizeHint(self._combatant_item_size())
            self.combatants_list.addItem(list_item)
            row_widget = self._make_combatant_row_widget(f"{icon} {display_name}", result, conditions, i)
            self.combatants_list.setItemWidget(list_item, row_widget)

    def _combatant_item_size(self):
        """Return a fixed size for each combatant row so setItemWidget looks correct."""
        from PyQt6.QtCore import QSize
        return QSize(200, 28)

    def _make_condition_dot(self, condition_name: str, combatant_index: int) -> QWidget:
        """Small colored circle for a condition; click removes it."""
        condition_lower = condition_name.lower().strip()
        base_color = CONDITION_COLORS.get(condition_lower, "#888888")
        parent = self

        class ConditionDot(QWidget):
            def __init__(self, color_hex: str, tooltip_text: str, cond_name: str, idx: int):
                super().__init__()
                self.setFixedSize(12, 12)
                self.setToolTip(f"{tooltip_text}\n(Click to remove)")
                self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                self.setMouseTracking(True)
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                self._color = QColor(color_hex)
                self._hover = QColor(
                    min(255, int(self._color.red() * 1.3)),
                    min(255, int(self._color.green() * 1.3)),
                    min(255, int(self._color.blue() * 1.3)),
                )
                self._current = self._color
                self._cond_name = cond_name
                self._idx = idx

            def enterEvent(self, event):
                self._current = self._hover
                self.update()
                super().enterEvent(event)

            def leaveEvent(self, event):
                self._current = self._color
                self.update()
                super().leaveEvent(event)

            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    parent.remove_condition_from_combatant(self._idx, self._cond_name)
                super().mousePressEvent(event)

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QBrush(self._current))
                painter.setPen(Qt.PenStyle.NoPen)
                r = self.rect()
                s = min(r.width(), r.height()) - 2
                x, y = (r.width() - s) // 2, (r.height() - s) // 2
                painter.drawEllipse(x, y, s, s)
                painter.end()

        return ConditionDot(base_color, condition_name, condition_name, combatant_index)

    def _make_combatant_row_widget(self, name_text: str, result: int | None, conditions: list, combatant_index: int) -> QWidget:
        """Row: name on left, condition dots, stretch, (result) on right."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)
        left = QLabel(name_text)
        left.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        left.setWordWrap(False)
        layout.addWidget(left)
        for cond in conditions:
            layout.addWidget(self._make_condition_dot(cond, combatant_index))
        layout.addStretch()
        if result is not None:
            right = QLabel(f"({result})")
            right.setStyleSheet("color: #CBD5E0; font-size: 11px; font-weight: bold;")
            layout.addWidget(right)
        return row

    def add_condition_to_combatant(self, combatant_index: int, condition_name: str):
        """Add a condition to the combatant at the given index (in current sorted list) and refresh."""
        if combatant_index < 0 or combatant_index >= len(self.combatants):
            return
        cond_list = self.combatants[combatant_index].setdefault("conditions", [])
        if condition_name.strip():
            cond_list.append(condition_name.strip())
            self._refresh_list()

    def remove_condition_from_combatant(self, combatant_index: int, condition_name: str):
        """Remove a condition from the combatant at the given index and refresh."""
        if combatant_index < 0 or combatant_index >= len(self.combatants):
            return
        cond_list = self.combatants[combatant_index].get("conditions", [])
        condition_lower = condition_name.lower()
        self.combatants[combatant_index]["conditions"] = [c for c in cond_list if c.lower() != condition_lower]
        self._refresh_list()

    def _clear_combatants(self):
        if self.combatants:
            reply = QMessageBox.question(
                self, "Clear Tracker",
                "Remove all combatants from the tracker?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.combatants.clear()
                self._refresh_list()

    def _show_context_menu(self, pos):
        item = self.combatants_list.itemAt(pos)
        if not item:
            return
        row = self.combatants_list.row(item)
        if row < 0 or row >= len(self.combatants):
            return
        menu = QMenu(self)
        add_cond_act = menu.addAction("➕ Add Condition")
        remove_act = menu.addAction("Remove from tracker")
        action = menu.exec(self.combatants_list.mapToGlobal(pos))
        if action == add_cond_act:
            self._show_add_condition_dialog(row)
        elif action == remove_act:
            self.combatants.pop(row)
            self._refresh_list()

    def _show_add_condition_dialog(self, combatant_index: int):
        """Show dialog to pick or enter a condition, then add it to the combatant."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Condition")
        dialog.setMinimumWidth(320)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Condition:"))
        known = list(CONDITION_COLORS.keys())
        combo = QComboBox()
        combo.addItems([c.title() for c in known])
        combo.addItem("Other")
        combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: #E2E8F0;
                padding: 6px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        layout.addWidget(combo)
        other_edit = QLineEdit()
        other_edit.setPlaceholderText("Custom condition name...")
        other_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #E2E8F0;
                padding: 6px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        layout.addWidget(other_edit)
        other_edit.setVisible(False)

        def on_combo(i):
            other_edit.setVisible(i == len(known))

        combo.currentIndexChanged.connect(on_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if combo.currentIndex() == len(known):
                name = other_edit.text().strip()
            else:
                name = known[combo.currentIndex()]
            if name:
                self.add_condition_to_combatant(combatant_index, name)


class StatBlockViewerWidget(QWidget):
    """Widget that displays statblocks visually - game mechanics only, no lore."""

    # Emitted when user clicks a clickable word in statblock content (e.g. condition name)
    word_clicked = pyqtSignal(str)
    
    # Words that become clickable links in section content (e.g. D&D conditions)
    CLICKABLE_WORDS = list(CONDITION_COLORS.keys())
    
    # Define which section types are mechanics (not lore)
    MECHANICS_SECTIONS = {
        "traits", "actions", "legendary_actions", "lair_actions",
        "reactions", "bonus_actions", "regional_effects", "legendary_resistance"
    }
    
    # Section types to exclude (lore)
    LORE_SECTIONS = {
        "description", "background", "history", "personality", 
        "appearance", "notes", "lore"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_entity = None
        self.custom_list = []  # List of items: [{"type": "entity"/"note", "id": "...", "name": "..."}, ...]
        self.combat_mode = False
        self.combat_tracker_widget = None
        self.combat_splitter = None
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the UI components."""
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(10, 10, 10, 10)
        self.root_layout.setSpacing(10)
        
        # Main content (list + display) - can be put in splitter with combat tracker
        self.main_content_widget = QWidget()
        layout = QVBoxLayout(self.main_content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header with title and buttons
        header_layout = QHBoxLayout()
        header_label = QLabel("StatBlock Viewer - Custom List")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #E2E8F0;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        # Add item button
        self.add_item_btn = QPushButton("+ Add Item")
        self.add_item_btn.setStyleSheet("""
            QPushButton {
                background-color: #5DADE2;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover {
                background-color: #6DBDF2;
            }
        """)
        self.add_item_btn.clicked.connect(self.show_add_item_dialog)
        header_layout.addWidget(self.add_item_btn)
        
        # Clear list button
        self.clear_list_btn = QPushButton("Clear List")
        self.clear_list_btn.setStyleSheet("""
            QPushButton {
                background-color: #F56565;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover {
                background-color: #FC8181;
            }
        """)
        self.clear_list_btn.clicked.connect(self.clear_list)
        header_layout.addWidget(self.clear_list_btn)
        
        # Start Combat button (red, sword) - toggles to "End Combat" in combat mode
        self.start_combat_btn = QPushButton("\u2694 Start Combat")
        self.start_combat_btn.setToolTip("Split view and enable combat tracker; double-click list items to add to tracker.")
        self.start_combat_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B0000;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #a52a2a;
            }
            QPushButton:hover {
                background-color: #a52a2a;
            }
        """)
        self.start_combat_btn.clicked.connect(self._toggle_combat_mode)
        header_layout.addWidget(self.start_combat_btn)
        
        layout.addLayout(header_layout)
        
        # List of items (small list widget showing what's in the custom list)
        list_title_row = QHBoxLayout()
        list_title_row.setContentsMargins(0, 0, 0, 0)
        list_label = QLabel("Items in List:")
        list_label.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        list_title_row.addWidget(list_label)
        list_title_row.addStretch()
        # Small dot next to title: hover = tooltip, click = toggle panel with all conditions
        self.conditions_summary_dot = self._create_conditions_summary_dot()
        list_title_row.addWidget(self.conditions_summary_dot)
        layout.addLayout(list_title_row)
        
        # Toggle panel: list all conditions in the list with colored dots (hidden by default)
        self.conditions_summary_panel = self._create_conditions_summary_panel()
        layout.addWidget(self.conditions_summary_panel)
        
        self.items_list = QListWidget()
        self.items_list.setMaximumHeight(100)
        self.items_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.items_list.customContextMenuRequested.connect(self.show_list_item_context_menu)
        self.items_list.setStyleSheet("""
            QListWidget {
                background-color: #3c3c3c;
                color: #E2E8F0;
                border: 1px solid #4c4c4c;
                border-radius: 6px;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 0px;
                border-bottom: 1px solid #4c4c4c;
                min-height: 20px;
            }
            QListWidget::item:selected {
                background-color: #5DADE2;
            }
            QListWidget::item:hover {
                background-color: #4c4c4c;
            }
        """)
        self.items_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.items_list.itemSelectionChanged.connect(self.on_item_selection_changed)
        layout.addWidget(self.items_list)
        
        # Scroll area for displaying all items
        self.display_scroll = QScrollArea()
        self.display_scroll.setWidgetResizable(True)
        self.display_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #4c4c4c;
                border-radius: 6px;
                background-color: #2b2b2b;
            }
        """)
        
        # Display widget for all items
        self.display_widget = QWidget()
        self.display_layout = QVBoxLayout(self.display_widget)
        self.display_layout.setContentsMargins(15, 15, 15, 15)
        self.display_layout.setSpacing(15)
        
        # Placeholder text
        self.placeholder = QLabel("Add items to your custom list to view them here")
        self.placeholder.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
                font-style: italic;
            }
        """)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_layout.addWidget(self.placeholder)
        self.display_layout.addStretch()
        
        self.display_scroll.setWidget(self.display_widget)
        layout.addWidget(self.display_scroll)
        
        # Combat tracker (shown in splitter when entering combat mode, like statblock viewer)
        self.combat_tracker_widget = CombatTrackerWidget(self)

        # Start with only main content
        self.root_layout.addWidget(self.main_content_widget)
        self.setMinimumWidth(350)
        
    def connect_signals(self):
        """Connect signals and slots."""
        signal_hub.data_saved.connect(self.on_data_saved)
        signal_hub.data_selected.connect(self.on_data_selected)
        signal_hub.add_to_stat_block_list.connect(self.add_item_to_list)

    def _toggle_combat_mode(self):
        """Switch between normal view and combat view (splitter with combat tracker)."""
        self.combat_mode = not self.combat_mode
        if self.combat_mode:
            self._enter_combat_mode()
        else:
            self._leave_combat_mode()

    def _enter_combat_mode(self):
        """Show splitter: main content | combat tracker."""
        self.root_layout.removeWidget(self.main_content_widget)
        self.combat_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.combat_splitter.addWidget(self.main_content_widget)
        self.combat_splitter.addWidget(self.combat_tracker_widget)
        self.combat_splitter.setStretchFactor(0, 1)
        self.combat_splitter.setStretchFactor(1, 0)
        self.combat_splitter.setSizes([400, 220])
        self.root_layout.addWidget(self.combat_splitter)
        self.start_combat_btn.setText("\u2694 End Combat")
        self.start_combat_btn.setStyleSheet("""
            QPushButton {
                background-color: #5c3c3c;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #6c4c4c;
            }
            QPushButton:hover { background-color: #6c4c4c; }
        """)

    def _leave_combat_mode(self):
        """Hide splitter, show only main content."""
        if self.combat_splitter:
            self.root_layout.removeWidget(self.combat_splitter)
            self.combat_splitter.removeWidget(self.main_content_widget)
            self.combat_splitter.removeWidget(self.combat_tracker_widget)
            self.combat_splitter.deleteLater()
            self.combat_splitter = None
        self.root_layout.addWidget(self.main_content_widget)
        self.start_combat_btn.setText("\u2694 Start Combat")
        self.start_combat_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B0000;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #a52a2a;
            }
            QPushButton:hover { background-color: #a52a2a; }
        """)

    def show_add_item_dialog(self):
        """Show dialog to add items to the custom list."""
        dialog = AddItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = dialog.get_selected_item()
            if item:
                self.add_item_to_list(item)
    
    def add_item_to_list(self, item: dict):
        """Add an item to the custom list."""
        # Check if already in list
        for existing_item in self.custom_list:
            if existing_item["type"] == item["type"] and existing_item["id"] == item["id"]:
                QMessageBox.information(self, "Already Added", f"{item['name']} is already in the list.")
                return
        
        self.custom_list.append(item)
        self.refresh_items_list()
        # Auto-select the newly added item
        last_index = self.items_list.count() - 1
        if last_index >= 0:
            self.items_list.setCurrentRow(last_index)
        self.refresh_display()
    
    def remove_item_from_list(self, index: int):
        """Remove an item from the custom list."""
        if 0 <= index < len(self.custom_list):
            self.custom_list.pop(index)
            self.refresh_items_list()
            self.refresh_display()
    
    def clear_list(self):
        """Clear the entire custom list."""
        reply = QMessageBox.question(
            self, 
            "Clear List",
            "Are you sure you want to clear the entire list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.custom_list.clear()
            self.refresh_items_list()
            self.refresh_display()
    
    def refresh_items_list(self):
        """Refresh the items list widget."""
        self.items_list.clear()
        for item in self.custom_list:
            item_type_icon = "📦" if item["type"] == "entity" else "📝"
            base_text = f"{item_type_icon} {item['name']} ({item['type']})"
            
            # Create custom widget for item with condition indicators
            item_widget = self.create_list_item_widget(item, base_text)
            
            list_item = QListWidgetItem()
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            # Set proper size hint
            item_widget.setMinimumHeight(20)
            size_hint = item_widget.sizeHint()
            if size_hint.height() < 20:
                size_hint.setHeight(20)
            list_item.setSizeHint(size_hint)
            self.items_list.addItem(list_item)
            self.items_list.setItemWidget(list_item, item_widget)
        # Update conditions summary dot tooltip and panel content
        self._update_conditions_summary_tooltip()
        if self.conditions_summary_panel.isVisible():
            self._refresh_conditions_summary_panel()
    
    def create_list_item_widget(self, item_data: dict, base_text: str) -> QWidget:
        """Create a custom widget for list item with condition indicators."""
        widget = QWidget()
        widget.setAutoFillBackground(False)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Base text label
        text_label = QLabel(base_text)
        text_label.setStyleSheet("""
            QLabel {
                color: #E2E8F0;
                font-size: 11px;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(text_label)
        
        # Condition indicators (only for entities)
        if item_data["type"] == "entity":
            try:
                conditions = self.get_entity_conditions(item_data["id"])
                if conditions:
                    for condition in conditions:
                        # Get description for this condition
                        desc = self.get_condition_description(item_data["id"], condition)
                        if desc:
                            tooltip = f"{condition}: {desc}"
                        else:
                            tooltip = condition
                        indicator = self.create_condition_indicator_with_tooltip(
                            condition, tooltip, item_data["id"]
                        )
                        layout.addWidget(indicator)
            except Exception as e:
                print(f"Error loading conditions for {item_data.get('name', 'unknown')}: {e}")
        
        layout.addStretch()
        
        # Set fixed height for consistent display
        widget.setFixedHeight(24)
        widget.setMinimumWidth(150)
        
        return widget
    
    def get_entity_conditions(self, entity_id: str) -> list:
        """Get conditions for an entity from database."""
        try:
            with DatabaseManager() as db:
                from sqlalchemy.orm import joinedload
                entity = db.query(Entity).options(
                    joinedload(Entity.properties)
                ).filter(Entity.id == entity_id).first()
                
                if not entity:
                    return []
                
                # Look for conditions in properties
                conditions = []
                for prop in entity.properties:
                    if prop.key.lower() in ["condition", "conditions", "status", "statuses"]:
                        # Try to parse as JSON dict (with descriptions) or array
                        try:
                            cond_data = json.loads(prop.value)
                            if isinstance(cond_data, dict):
                                # Dictionary format: {"condition_name": "description"}
                                conditions = list(cond_data.keys())
                            elif isinstance(cond_data, list):
                                conditions = cond_data
                            else:
                                conditions.append(prop.value)
                        except (json.JSONDecodeError, TypeError):
                            # If not JSON, treat as comma-separated
                            cond_list = [c.strip() for c in prop.value.split(",") if c.strip()]
                            conditions.extend(cond_list)
                
                return conditions
        except Exception as e:
            print(f"Error getting entity conditions: {e}")
            return []
    
    def get_all_conditions_in_list(self):
        """Return list of (condition_name, hex_color) for all conditions present in list entities (unique, sorted)."""
        seen = {}
        for item in self.custom_list:
            if item.get("type") != "entity":
                continue
            try:
                for cond in self.get_entity_conditions(item["id"]):
                    key = (cond or "").strip().lower()
                    if not key:
                        continue
                    if key not in seen:
                        color = CONDITION_COLORS.get(key, "#888888")
                        seen[key] = (cond.strip(), color)
            except Exception:
                pass
        return sorted(seen.values(), key=lambda x: x[0].lower())
    
    def build_conditions_tooltip_html(self) -> str:
        """Build HTML tooltip listing all conditions in the list with colored bullet."""
        pairs = self.get_all_conditions_in_list()
        if not pairs:
            return "No conditions on items in list."
        lines = []
        for name, color in pairs:
            lines.append(f"<span style='color:{color}'>●</span> {name}")
        return "<html><body>" + "<br/>".join(lines) + "</body></html>"
    
    def _update_conditions_summary_tooltip(self):
        """Update the conditions summary dot tooltip from current list."""
        if hasattr(self, "conditions_summary_dot") and self.conditions_summary_dot:
            self.conditions_summary_dot.setToolTip(self.build_conditions_tooltip_html())
    
    def _create_conditions_summary_panel(self) -> QWidget:
        """Panel below title: shows all conditions in list with colored dots. Toggle visibility via dot click."""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #4c4c4c;
                border-radius: 4px;
                padding: 6px;
                margin-bottom: 4px;
            }
        """)
        panel.setVisible(False)
        self._conditions_panel_layout = QHBoxLayout(panel)
        self._conditions_panel_layout.setContentsMargins(6, 4, 6, 4)
        self._conditions_panel_layout.setSpacing(8)
        self._conditions_panel_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return panel

    def _refresh_conditions_summary_panel(self):
        """Rebuild the conditions summary panel content from current list."""
        # Clear existing
        while self._conditions_panel_layout.count():
            child = self._conditions_panel_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        pairs = self.get_all_conditions_in_list()
        for name, color in pairs:
            dot = self._make_small_condition_dot(color)
            lbl = QLabel(name)
            lbl.setStyleSheet("color: #E2E8F0; font-size: 10px; background: transparent;")
            self._conditions_panel_layout.addWidget(dot)
            self._conditions_panel_layout.addWidget(lbl)
        self._conditions_panel_layout.addStretch()

    def _make_small_condition_dot(self, hex_color: str) -> QWidget:
        """Return a small colored circle widget (no click, just display)."""
        class SmallDot(QWidget):
            def __init__(self, color):
                super().__init__()
                self.color = QColor(color)
                self.setFixedSize(10, 10)
            def paintEvent(self, event):
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setBrush(QBrush(self.color))
                p.setPen(Qt.PenStyle.NoPen)
                r = self.rect()
                d = min(r.width(), r.height()) - 2
                x, y = (r.width() - d) // 2, (r.height() - d) // 2
                p.drawEllipse(x, y, d, d)
                p.end()
        return SmallDot(hex_color)

    def _create_conditions_summary_dot(self) -> QWidget:
        """Create small dot next to 'Items in List:' title; hover = tooltip, click = toggle panel."""
        class ConditionsSummaryDot(QWidget):
            def __init__(self, parent_widget):
                super().__init__(parent_widget)
                self.parent_viewer = parent_widget
                self.setFixedSize(10, 10)
                self.setToolTip(parent_widget.build_conditions_tooltip_html())
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QBrush(QColor("#888888")))
                painter.setPen(Qt.PenStyle.NoPen)
                r = self.rect()
                d = min(r.width(), r.height()) - 2
                x = (r.width() - d) // 2
                y = (r.height() - d) // 2
                painter.drawEllipse(x, y, d, d)
                painter.end()
            
            def enterEvent(self, event):
                self.setToolTip(self.parent_viewer.build_conditions_tooltip_html())
                super().enterEvent(event)
            
            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    self.parent_viewer._toggle_conditions_summary_panel()
                super().mousePressEvent(event)
        
        return ConditionsSummaryDot(self)

    def _toggle_conditions_summary_panel(self):
        """Show or hide the conditions summary panel and refresh its content."""
        self._refresh_conditions_summary_panel()
        self.conditions_summary_panel.setVisible(not self.conditions_summary_panel.isVisible())
    
    def create_condition_indicator_with_tooltip(self, condition: str, tooltip: str, entity_id: str) -> QWidget:
        """Create a colored circle indicator for a condition with custom tooltip, hover effect, and click to remove."""
        condition_lower = condition.lower().strip()
        base_color = CONDITION_COLORS.get(condition_lower, "#888888")
        
        # Create indicator widget with custom paint, hover, and click
        class ConditionIndicator(QWidget):
            def __init__(self, base_color, tooltip_text, condition_name, entity_id, parent_widget):
                super().__init__()
                self.base_color = QColor(base_color)
                self.hover_color = self._lighten_color(self.base_color)
                self.current_color = self.base_color
                self.condition_name = condition_name
                self.entity_id = entity_id
                self.parent_widget = parent_widget
                
                # Fixed square size to ensure perfect circle
                self.setFixedSize(14, 14)
                self.setToolTip(f"{tooltip_text}\n(Tıklayarak kaldır)")
                self.setMinimumSize(14, 14)
                self.setMaximumSize(14, 14)
                # Prevent stretching
                self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                # Enable mouse tracking for hover
                self.setMouseTracking(True)
                # Enable cursor change on hover
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            
            def _lighten_color(self, color: QColor) -> QColor:
                """Lighten the color slightly for hover effect."""
                # Brighten RGB values by ~30%
                r = min(255, int(color.red() * 1.3))
                g = min(255, int(color.green() * 1.3))
                b = min(255, int(color.blue() * 1.3))
                return QColor(r, g, b, color.alpha())
            
            def enterEvent(self, event):
                """Mouse enters the widget - show hover color."""
                self.current_color = self.hover_color
                self.update()
                super().enterEvent(event)
            
            def leaveEvent(self, event):
                """Mouse leaves the widget - show base color."""
                self.current_color = self.base_color
                self.update()
                super().leaveEvent(event)
            
            def mousePressEvent(self, event):
                """Handle mouse click - remove condition."""
                if event.button() == Qt.MouseButton.LeftButton:
                    # Remove condition from entity
                    self.parent_widget.remove_condition_from_entity(self.entity_id, self.condition_name)
                    # Refresh the list to update display
                    self.parent_widget.refresh_items_list()
                super().mousePressEvent(event)
            
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Draw filled perfect circle with current color
                painter.setBrush(QBrush(self.current_color))
                painter.setPen(Qt.PenStyle.NoPen)
                
                # Draw perfect circle - use same width and height, centered
                rect = self.rect()
                circle_size = min(rect.width(), rect.height()) - 2  # 2px margin
                x = (rect.width() - circle_size) // 2
                y = (rect.height() - circle_size) // 2
                painter.drawEllipse(x, y, circle_size, circle_size)
                
                painter.end()
        
        return ConditionIndicator(base_color, tooltip, condition, entity_id, self)
    
    def create_condition_indicator(self, condition: str) -> QWidget:
        """Create a colored circle indicator for a condition."""
        # D&D 5e condition colors and descriptions
        condition_info = {
            "blinded": ("#FF6B6B", "Blinded: Can't see and automatically fails sight-based checks"),
            "charmed": ("#FFD93D", "Charmed: Can't attack the charmer and charmer has advantage on social checks"),
            "deafened": ("#95E1D3", "Deafened: Can't hear and automatically fails hearing-based checks"),
            "frightened": ("#6C5CE7", "Frightened: Disadvantage on ability checks and attack rolls while source is in line of sight"),
            "grappled": ("#A29BFE", "Grappled: Speed becomes 0, can't benefit from speed bonus"),
            "incapacitated": ("#FD79A8", "Incapacitated: Can't take actions or reactions"),
            "invisible": ("#74B9FF", "Invisible: Heavily obscured, attacks have disadvantage against you"),
            "paralyzed": ("#E17055", "Paralyzed: Can't move or speak, automatically fails STR/DEX saves, attacks have advantage"),
            "petrified": ("#636E72", "Petrified: Turned to stone, weight increases, can't move or perceive, resistant to damage"),
            "poisoned": ("#00B894", "Poisoned: Disadvantage on attack rolls and ability checks"),
            "prone": ("#FDCB6E", "Prone: Can only crawl or stand up, melee attacks have advantage, ranged attacks have disadvantage"),
            "restrained": ("#E84393", "Restrained: Speed becomes 0, disadvantage on DEX saves and attack rolls, attacks have advantage"),
            "stunned": ("#FF7675", "Stunned: Can't take actions, can't move, can only speak falteringly, automatically fails STR/DEX saves"),
            "unconscious": ("#2D3436", "Unconscious: Can't move or speak, unaware of surroundings, drops held items, attacks have advantage"),
            "exhaustion": ("#6C5CE7", "Exhaustion: Levels 1-6 with increasing penalties"),
        }
        
        # Normalize condition name
        condition_lower = condition.lower().strip()
        color, tooltip = condition_info.get(condition_lower, ("#888888", condition.title()))
        
        # Create indicator widget with custom paint
        class ConditionIndicator(QWidget):
            def __init__(self, color, tooltip_text):
                super().__init__()
                self.color = QColor(color)
                # Fixed square size to ensure perfect circle
                self.setFixedSize(14, 14)
                self.setToolTip(tooltip_text)
                self.setMinimumSize(14, 14)
                self.setMaximumSize(14, 14)
                # Prevent stretching
                self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Draw filled perfect circle
                painter.setBrush(QBrush(self.color))
                painter.setPen(Qt.PenStyle.NoPen)
                
                # Draw perfect circle - use same width and height, centered
                rect = self.rect()
                circle_size = min(rect.width(), rect.height()) - 2  # 2px margin
                x = (rect.width() - circle_size) // 2
                y = (rect.height() - circle_size) // 2
                painter.drawEllipse(x, y, circle_size, circle_size)
                
                painter.end()
        
        return ConditionIndicator(color, tooltip)
    
    def show_list_item_context_menu(self, position):
        """Show context menu for list items."""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        item = self.items_list.itemAt(position)
        if not item:
            return
        
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if not item_data or item_data.get("type") != "entity":
            return
        
        menu = QMenu(self)
        
        add_condition_action = QAction("➕ Add Condition", self)
        add_condition_action.triggered.connect(lambda: self.add_condition_to_entity(item_data))
        menu.addAction(add_condition_action)
        
        menu.addSeparator()
        
        remove_action = QAction("🗑️ Remove from List", self)
        remove_action.triggered.connect(lambda: self.remove_item_from_list(self.items_list.row(item)))
        menu.addAction(remove_action)
        
        menu.exec(self.items_list.mapToGlobal(position))
    
    def add_condition_to_entity(self, item_data: dict):
        """Add a condition to an entity."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Condition")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Condition name
        name_label = QLabel("Condition Name:")
        name_label.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g., Poisoned, Grappled, Blinded")
        name_input.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #E2E8F0;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #4c4c4c;
                font-size: 11px;
            }
        """)
        layout.addWidget(name_label)
        layout.addWidget(name_input)
        
        # Condition description (optional)
        desc_label = QLabel("Description (Optional):")
        desc_label.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("Enter condition description...")
        desc_input.setMaximumHeight(100)
        desc_input.setStyleSheet("""
            QTextEdit {
                background-color: #3c3c3c;
                color: #E2E8F0;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #4c4c4c;
                font-size: 11px;
            }
        """)
        layout.addWidget(desc_label)
        layout.addWidget(desc_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #718096;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        add_btn = QPushButton("Add Condition")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #48BB78;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
            }
        """)
        add_btn.clicked.connect(dialog.accept)
        add_btn.setDefault(True)
        button_layout.addWidget(add_btn)
        
        layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            condition_name = name_input.text().strip()
            condition_desc = desc_input.toPlainText().strip()
            
            if condition_name:
                self.save_condition_to_entity(item_data["id"], condition_name, condition_desc)
                # Refresh the list to show new condition
                self.refresh_items_list()
    
    def save_condition_to_entity(self, entity_id: str, condition_name: str, condition_desc: str = ""):
        """Save condition to entity in database."""
        try:
            from core.database import DatabaseManager
            from models.entity import Entity
            from models.entity_property import EntityProperty
            from sqlalchemy.orm import joinedload
            
            with DatabaseManager() as db:
                entity = db.query(Entity).options(
                    joinedload(Entity.properties)
                ).filter(Entity.id == entity_id).first()
                
                if not entity:
                    return
                
                # Find existing conditions property
                conditions_prop = None
                for prop in entity.properties:
                    if prop.key.lower() in ["condition", "conditions", "status", "statuses"]:
                        conditions_prop = prop
                        break
                
                # Parse existing conditions
                conditions_dict = {}
                if conditions_prop:
                    try:
                        cond_data = json.loads(conditions_prop.value)
                        if isinstance(cond_data, dict):
                            conditions_dict = cond_data
                    except (json.JSONDecodeError, TypeError):
                        # If old format (array or string), convert to dict
                        try:
                            cond_list = json.loads(conditions_prop.value)
                            if isinstance(cond_list, list):
                                for cond in cond_list:
                                    conditions_dict[cond] = ""
                        except (json.JSONDecodeError, TypeError):
                            cond_list = [c.strip() for c in conditions_prop.value.split(",") if c.strip()]
                            for cond in cond_list:
                                conditions_dict[cond] = ""
                
                # Check if condition already exists
                condition_lower = condition_name.lower()
                if any(c.lower() == condition_lower for c in conditions_dict.keys()):
                    QMessageBox.information(self, "Condition Exists", f"Condition '{condition_name}' already exists.")
                    return
                
                # Add new condition
                conditions_dict[condition_name] = condition_desc
                
                # Save back to property
                conditions_json = json.dumps(conditions_dict)
                if conditions_prop:
                    conditions_prop.value = conditions_json
                else:
                    new_prop = EntityProperty(entity_id=entity.id, key="conditions", value=conditions_json)
                    db.add(new_prop)
                
                db.commit()
                
        except Exception as e:
            print(f"Error saving condition: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to save condition: {str(e)}")
    
    def get_condition_description(self, entity_id: str, condition_name: str) -> str:
        """Get description for a specific condition."""
        try:
            with DatabaseManager() as db:
                from sqlalchemy.orm import joinedload
                entity = db.query(Entity).options(
                    joinedload(Entity.properties)
                ).filter(Entity.id == entity_id).first()
                
                if not entity:
                    return ""
                
                for prop in entity.properties:
                    if prop.key.lower() in ["condition", "conditions", "status", "statuses"]:
                        try:
                            cond_data = json.loads(prop.value)
                            if isinstance(cond_data, dict):
                                return cond_data.get(condition_name, "")
                        except (json.JSONDecodeError, TypeError):
                            pass
                
                return ""
        except Exception as e:
            print(f"Error getting condition description: {e}")
            return ""
    
    def remove_condition_from_entity(self, entity_id: str, condition_name: str):
        """Remove a condition from an entity."""
        try:
            with DatabaseManager() as db:
                from sqlalchemy.orm import joinedload
                entity = db.query(Entity).options(
                    joinedload(Entity.properties)
                ).filter(Entity.id == entity_id).first()
                
                if not entity:
                    return
                
                # Find existing conditions property
                conditions_prop = None
                for prop in entity.properties:
                    if prop.key.lower() in ["condition", "conditions", "status", "statuses"]:
                        conditions_prop = prop
                        break
                
                if not conditions_prop:
                    return
                
                # Parse existing conditions
                conditions_dict = {}
                try:
                    cond_data = json.loads(conditions_prop.value)
                    if isinstance(cond_data, dict):
                        conditions_dict = cond_data
                    elif isinstance(cond_data, list):
                        # Convert list to dict
                        for cond in cond_data:
                            conditions_dict[cond] = ""
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, treat as comma-separated
                    cond_list = [c.strip() for c in conditions_prop.value.split(",") if c.strip()]
                    for cond in cond_list:
                        conditions_dict[cond] = ""
                
                # Remove condition (case-insensitive match)
                condition_lower = condition_name.lower()
                keys_to_remove = [k for k in conditions_dict.keys() if k.lower() == condition_lower]
                
                if not keys_to_remove:
                    return
                
                # Remove the condition
                for key in keys_to_remove:
                    del conditions_dict[key]
                
                # Save back to property
                if conditions_dict:
                    conditions_json = json.dumps(conditions_dict)
                    conditions_prop.value = conditions_json
                else:
                    # If no conditions left, remove the property
                    db.delete(conditions_prop)
                
                db.commit()
                
        except Exception as e:
            print(f"Error removing condition: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to remove condition: {str(e)}")
    
    def on_item_double_clicked(self, item: QListWidgetItem):
        """In combat mode: add item to combat tracker. Otherwise: prompt to remove from list."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        if self.combat_mode and self.combat_tracker_widget:
            self.combat_tracker_widget.add_combatant(data)
            return
        reply = QMessageBox.question(
            self,
            "Remove Item",
            f"Remove '{data['name']}' from the list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            index = self.items_list.row(item)
            self.remove_item_from_list(index)
    
    def on_item_selection_changed(self):
        """Handle item selection change - display only selected item."""
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the display area - show only the selected item."""
        # Clear previous display
        while self.display_layout.count() > 0:
            item = self.display_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
        
        # Reset placeholder reference
        self.placeholder = None
        
        if not self.custom_list:
            # Show placeholder
            self.placeholder = QLabel("Add items to your custom list to view them here")
            self.placeholder.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 12px;
                    font-style: italic;
                }
            """)
            self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.display_layout.addWidget(self.placeholder)
            self.display_layout.addStretch()
            return
        
        # Get selected item
        selected_items = self.items_list.selectedItems()
        if not selected_items:
            # No selection - show placeholder
            self.placeholder = QLabel("Select an item from the list above to view it")
            self.placeholder.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 12px;
                    font-style: italic;
                }
            """)
            self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.display_layout.addWidget(self.placeholder)
            self.display_layout.addStretch()
            return
        
        # Display only the selected item
        selected_item = selected_items[0]
        item_data = selected_item.data(Qt.ItemDataRole.UserRole)
        
        if item_data:
            if item_data["type"] == "entity":
                self.display_entity(item_data["id"])
            elif item_data["type"] == "note":
                self.display_note(item_data["id"])
        
        self.display_layout.addStretch()
    
    def display_entity(self, entity_id: str):
        """Display an entity in the viewer."""
        try:
            with DatabaseManager() as db:
                # Eager load properties and sections
                from sqlalchemy.orm import joinedload
                entity = db.query(Entity).options(
                    joinedload(Entity.properties),
                    joinedload(Entity.sections)
                ).filter(Entity.id == entity_id).first()
                
                if not entity:
                    return
                
                # Force load properties and sections
                _ = list(entity.properties) if entity.properties else []
                _ = list(entity.sections) if entity.sections else []
                
                self.display_statblock(entity)
        except Exception as e:
            print(f"Error loading entity: {e}")
            import traceback
            traceback.print_exc()
    
    def display_note(self, note_id: int):
        """Display a note in the viewer."""
        try:
            with DatabaseManager() as db:
                note = db.query(Note).filter(Note.id == note_id).first()
                
                if not note:
                    return
                
                # Create note display widget
                note_widget = self.create_note_widget(note)
                self.display_layout.addWidget(note_widget)
        except Exception as e:
            print(f"Error loading note: {e}")
            import traceback
            traceback.print_exc()
    
    def create_note_widget(self, note: Note) -> QWidget:
        """Create a widget to display a note."""
        widget = QFrame()
        widget.setFrameShape(QFrame.Shape.Box)
        widget.setStyleSheet("""
            QFrame {
                border: 1px solid #4c4c4c;
                border-radius: 4px;
                background-color: #2b2b2b;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Note title
        title = QLabel(note.title)
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #E2E8F0;
                padding-bottom: 4px;
                border-bottom: 2px solid #5DADE2;
            }
        """)
        layout.addWidget(title)
        
        # Note content (HTML)
        content_label = QLabel()
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        
        # Convert HTML content to plain text if needed, or display as HTML
        if note.content:
            # Use QTextDocument to properly render HTML
            doc = QTextDocument()
            doc.setHtml(note.content)
            content_label.setText(doc.toPlainText()[:500] + ("..." if len(doc.toPlainText()) > 500 else ""))
        else:
            content_label.setText("(No content)")
        
        content_label.setStyleSheet("""
            QLabel {
                color: #CBD5E0;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(content_label)
        
        return widget
    
    def display_statblock(self, entity: Entity):
        """Display the statblock for an entity (mechanics only)."""
        # Create container widget for this entity
        entity_widget = QFrame()
        entity_widget.setStyleSheet("""
            QFrame {
                border-radius: 6px;
                background-color: transparent;
                padding: 0px;
            }
        """)
        
        entity_layout = QVBoxLayout(entity_widget)
        entity_layout.setContentsMargins(0, 0, 0, 0)
        entity_layout.setSpacing(12)
        
        # Properties dict (needed early for initiative in header)
        props_list = list(entity.properties) if hasattr(entity, 'properties') and entity.properties else []
        props_dict = {p.key: p.value for p in props_list}
        
        # Top row: Title (left) | Initiative (right, italic, clickable)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title = QLabel(entity.name)
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #F4A460;
                padding: 0px;
                margin-bottom: 0px;
            }
        """)
        title_row.addWidget(title)
        title_row.addStretch()
        # Initiative: use saved value or compute from DEX + proficiency
        initiative_value = props_dict.get("initiative", "").strip()
        if not initiative_value and props_dict.get("dex"):
            try:
                score_str, _ = self.parse_ability_score(props_dict["dex"])
                if score_str:
                    dex_int = int(score_str)
                    prof = self.get_proficiency_bonus(entity)
                    init_int = calculate_initiative_from_ability_score(dex_int, prof, 0)
                    initiative_value = f"+{init_int}" if init_int >= 0 else str(init_int)
            except (ValueError, TypeError):
                pass
        if initiative_value:
            initiative_btn = self._create_initiative_display(initiative_value, entity)
            title_row.addWidget(initiative_btn)
        entity_layout.addLayout(title_row)
        
        # Title separator (thin line under title)
        title_separator = QFrame()
        title_separator.setFrameShape(QFrame.Shape.HLine)
        title_separator.setStyleSheet("""
            QFrame {
                background-color: #F4A460;
                border: none;
                max-height: 1px;
            }
        """)
        title_separator.setFixedHeight(1)
        entity_layout.addWidget(title_separator)
        
        # Type label
        if entity.type:
            type_label = QLabel(entity.type.title())
            type_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    font-style: italic;
                    color: #CBD5E0;
                    padding-bottom: 8px;
                }
            """)
            entity_layout.addWidget(type_label)
        
        # Display ability scores first (if they exist)
        ability_score_keys = ["str", "dex", "con", "int", "wis", "cha"]
        ability_scores_dict = {}
        
        for key in ability_score_keys:
            if key in props_dict:
                ability_scores_dict[key] = props_dict[key]
        
        if ability_scores_dict:
            try:
                ability_scores_widget = self.create_ability_scores_widget(ability_scores_dict, entity.name, entity)
                entity_layout.addWidget(ability_scores_widget)
            except Exception as e:
                print(f"Error creating ability scores widget: {e}")
                import traceback
                traceback.print_exc()
        
        # Display other properties (mechanics)
        if props_dict:
            props_frame = QFrame()
            props_frame.setStyleSheet("background-color: transparent;")
            props_layout = QVBoxLayout(props_frame)
            props_layout.setContentsMargins(0, 0, 0, 0)
            props_layout.setSpacing(4)
            
            # Sort properties by common statblock order (excluding ability scores)
            prop_order = [
                "ac", "hp", "speed",
                "skills", "saving_throws", "damage_immunities", "damage_resistances",
                "damage_vulnerabilities", "condition_immunities", "senses", 
                "languages", "challenge_rating", "proficiency_bonus"
            ]
            
            ordered_props = []
            remaining_props = []
            
            # Skills: if entity has skill_proficiencies, show formatted bonuses only (prof/expertise/custom)
            has_skill_proficiencies = any(p.key == "skill_proficiencies" for p in entity.properties)
            has_saving_throw_proficiencies = any(p.key == "saving_throw_proficiencies" for p in entity.properties)
            for key in prop_order:
                if key not in ability_score_keys:
                    if key == "skills":
                        if has_skill_proficiencies:
                            formatted_skills = self.format_skills_display(entity, props_dict)
                            if formatted_skills:
                                ordered_props.append(("skills", formatted_skills))
                        elif key in props_dict:
                            ordered_props.append((key, props_dict[key]))
                    elif key == "saving_throws":
                        if has_saving_throw_proficiencies:
                            formatted_saves = self.format_saving_throws_display(entity)
                            if formatted_saves:
                                ordered_props.append(("saving_throws", formatted_saves))
                        elif key in props_dict:
                            ordered_props.append((key, props_dict[key]))
                    elif key == "proficiency_bonus":
                        if key in props_dict:
                            ordered_props.append((key, props_dict[key]))
                        else:
                            # Show proficiency bonus calculated from CR if entity has CR but no explicit prop
                            prof_from_cr = self.get_proficiency_bonus_from_cr_display(entity)
                            if prof_from_cr is not None:
                                ordered_props.append(("proficiency_bonus", prof_from_cr))
                    elif key in props_dict:
                        ordered_props.append((key, props_dict[key]))
            
            for key, value in props_dict.items():
                if key not in prop_order and key not in ability_score_keys and key not in ("skill_proficiencies", "saving_throw_proficiencies", "initiative"):
                    remaining_props.append((key, value))
            
            all_props = ordered_props + remaining_props
            
            if all_props:
                for key, value in all_props:
                    try:
                        prop_widget = self.create_property_widget(key, value)
                        props_layout.addWidget(prop_widget)
                    except Exception as e:
                        print(f"Error creating property widget for {key}: {e}")
                
                if props_layout.count() > 0:
                    entity_layout.addWidget(props_frame)
        
        # Display mechanics sections only
        sections_list = list(entity.sections) if hasattr(entity, 'sections') and entity.sections else []
        sorted_sections = sorted(sections_list, key=lambda s: s.sort_order)
        mechanics_sections = [
            s for s in sorted_sections 
            if s.section_type in self.MECHANICS_SECTIONS or 
               (s.section_type not in self.LORE_SECTIONS and s.section_type not in ["description", "background"])
        ]
        
        for section in mechanics_sections:
            section_widget = self.create_section_widget(
                section.section_type,
                section.content,
                entity_name=entity.name,
                ability_name=self.format_section_type(section.section_type),
            )
            entity_layout.addWidget(section_widget)
        
        # Add entity widget to main display
        self.display_layout.addWidget(entity_widget)
    
    def _parse_initiative_to_int(self, value: str):
        """Parse initiative string (e.g. '+2', '-1', '2') to int. Returns None if unparseable."""
        if not value:
            return None
        s = value.strip()
        if not s:
            return None
        if s.startswith("+"):
            s = s[1:]
        try:
            return int(s)
        except (ValueError, TypeError):
            return None

    def _create_initiative_display(self, initiative_value: str, entity: Entity) -> QWidget:
        """Create italic 'Initiative +X' line; click: if combat started add to tracker, else show result in dice console."""
        # Display text: "Initiative +2" or "Initiative -1"
        bonus_str = initiative_value.strip()
        try:
            n = int(bonus_str.replace("+", ""))
            bonus_str = f"+{n}" if n >= 0 else str(n)
        except (ValueError, TypeError):
            if not bonus_str.startswith("+") and not bonus_str.startswith("-"):
                pass  # keep as-is
        display_text = f"Initiative {bonus_str}"
        initiative_int = self._parse_initiative_to_int(initiative_value)
        # Capture id/name while entity is still bound to session (avoid DetachedInstanceError on click)
        entity_id = entity.id
        entity_name = entity.name

        btn = QPushButton(display_text)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #CBD5E0;
                font-size: 11px;
                font-style: italic;
                text-align: left;
                padding: 2px 0;
            }
            QPushButton:hover { color: #5DADE2; text-decoration: underline; }
            QPushButton:focus { outline: none; }
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFlat(True)
        btn.setToolTip("Roll initiative (1d20+mod); show in console. In combat mode also add to tracker.")

        def _on_click():
            mod = initiative_int or 0
            expr = f"1d20+{mod}" if mod >= 0 else f"1d20{mod}"
            roll_result = DiceRoller.roll(expr)
            total = roll_result.total if roll_result else mod
            # Always show roll result in console
            mod_display = f"+{mod}" if mod >= 0 else str(mod)
            message = f"<span style='color: #F4A460;'>{entity_name}</span> — Initiative: 1d20{mod_display} = <span style='color: #66BB6A;'>{total}</span>"
            signal_hub.console_output.emit(message)
            # In combat mode also add to tracker (pass result so we don't roll twice)
            if getattr(self, "combat_mode", False) and getattr(self, "combat_tracker_widget", None):
                data = {"type": "entity", "id": entity_id, "name": entity_name, "initiative": initiative_int, "result": total}
                self.combat_tracker_widget.add_combatant(data)

        btn.clicked.connect(_on_click)
        return btn

    def create_property_widget(self, key: str, value: str) -> QWidget:
        """Create a widget to display a property."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        
        # Key label (bold)
        key_label = QLabel(self.format_property_key(key))
        key_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #E2E8F0;
                font-size: 11px;
                min-width: 120px;
            }
        """)
        
        # Value label
        value_text = self.format_property_value(value)
        value_label = QLabel(value_text)
        value_label.setStyleSheet("""
            QLabel {
                color: #CBD5E0;
                font-size: 11px;
            }
        """)
        value_label.setWordWrap(True)
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        layout.addWidget(key_label)
        layout.addWidget(value_label)
        layout.setStretchFactor(value_label, 1)
        
        return widget
    
    def format_property_key(self, key: str) -> str:
        """Format property key for display."""
        return key.replace("_", " ").title()
    
    def format_property_value(self, value: str) -> str:
        """Format property value for display."""
        # Try to parse as JSON array
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return ", ".join(str(item) for item in data)
        except (json.JSONDecodeError, TypeError):
            pass
        
        return str(value)
    
    def parse_ability_score(self, value: str) -> tuple:
        """Parse ability score value like '27 (+8)' into (score, modifier).
        Returns (score, modifier) where both are strings."""
        if not value:
            return ("", "")
        
        # Try to extract score and modifier from formats like:
        # "27 (+8)", "27(+8)", "27 +8", "27"
        match = re.match(r'(\d+)\s*(?:\(?\+?(-?\d+)\)?)?', value.strip())
        if match:
            score = match.group(1)
            modifier = match.group(2) if match.group(2) else ""
            if modifier and not modifier.startswith(('+', '-')):
                modifier = '+' + modifier
            return (score, modifier)
        
        return (value, "")
    
    def get_proficiency_bonus(self, entity: Entity) -> int:
        """Get proficiency bonus from entity (explicit property or calculated from CR)."""
        for prop in entity.properties:
            if prop.key.lower() == "proficiency_bonus":
                try:
                    val = prop.value.strip()
                    if val.startswith("+"):
                        val = val[1:]
                    return int(val)
                except (ValueError, TypeError, AttributeError):
                    pass
        # Fallback: calculate from CR
        for prop in entity.properties:
            if prop.key.lower() in ("challenge_rating", "cr") and prop.value:
                return proficiency_bonus_from_cr(prop.value)
        return 0
    
    def get_proficiency_bonus_from_cr_display(self, entity: Entity):
        """Return proficiency bonus as display string (e.g. '+2') when derived from CR, or None."""
        if any(p.key.lower() == "proficiency_bonus" for p in entity.properties):
            return None  # Entity has explicit proficiency_bonus, don't show derived
        for prop in entity.properties:
            if prop.key.lower() in ("challenge_rating", "cr") and prop.value:
                bonus = proficiency_bonus_from_cr(prop.value)
                return f"+{bonus}" if bonus else None
        return None
    
    def get_ability_modifier_int(self, entity: Entity, ability_key: str) -> int:
        """Get ability modifier as int from entity (e.g. for STR +2 returns 2)."""
        for prop in entity.properties:
            if prop.key == ability_key:
                _, mod_str = self.parse_ability_score(prop.value)
                if not mod_str:
                    return 0
                try:
                    if mod_str.startswith('+'):
                        return int(mod_str[1:])
                    elif mod_str.startswith('-'):
                        return int(mod_str)
                    return int(mod_str)
                except (ValueError, TypeError):
                    pass
        return 0
    
    def format_saving_throws_display(self, entity: Entity) -> str:
        """Format saving throws as numeric modifiers (e.g. 'STR +2, DEX +5, WIS +3')."""
        proficiencies = {}
        for prop in entity.properties:
            if prop.key == "saving_throw_proficiencies":
                try:
                    data = json.loads(prop.value)
                    if isinstance(data, dict):
                        proficiencies = data
                    break
                except (json.JSONDecodeError, TypeError):
                    pass
        if not proficiencies:
            return ""
        prof_bonus = self.get_proficiency_bonus(entity)
        ability_display = [
            ("str", "STR"), ("dex", "DEX"), ("con", "CON"),
            ("int", "INT"), ("wis", "WIS"), ("cha", "CHA")
        ]
        parts = []
        for ability_key, display_name in ability_display:
            if proficiencies.get(ability_key, False):
                base_mod = self.get_ability_modifier_int(entity, ability_key)
                total = base_mod + prof_bonus
                sign = "+" if total >= 0 else ""
                parts.append(f"{display_name} {sign}{total}")
        return ", ".join(parts)
    
    # Skill key -> (display name, ability key) for skills display
    SKILL_DISPLAY_ORDER = [
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
    
    def _parse_modifier_to_int(self, modifier_str: str) -> int:
        """Parse modifier string like '+8' or '-1' to int."""
        if not modifier_str:
            return 0
        s = modifier_str.strip()
        if s.startswith('+'):
            s = s[1:]
        try:
            return int(s)
        except (ValueError, TypeError):
            return 0
    
    def format_skills_display(self, entity: Entity, props_dict: dict) -> str:
        """Build Skills line from skill_proficiencies: show only bonus (prof = prof bonus, expertise = 2×prof, custom = +N (custom))."""
        skill_proficiencies = None
        for prop in entity.properties:
            if prop.key == "skill_proficiencies":
                try:
                    skill_proficiencies = json.loads(prop.value)
                    if not isinstance(skill_proficiencies, dict):
                        skill_proficiencies = None
                except (json.JSONDecodeError, TypeError) as e:
                    skill_proficiencies = None
                break
        if not skill_proficiencies:
            return ""
        
        prof_bonus = self.get_proficiency_bonus(entity)
        ability_mods = {}
        for ab in ["str", "dex", "con", "int", "wis", "cha"]:
            raw = props_dict.get(ab, "")
            _, mod_str = self.parse_ability_score(raw)
            ability_mods[ab] = self._parse_modifier_to_int(mod_str)
        
        parts = []
        for skill_key, display_name, ability_key in sorted(self.SKILL_DISPLAY_ORDER, key=lambda x: x[1].lower()):
            if skill_key not in skill_proficiencies:
                continue
            val = skill_proficiencies[skill_key]
            ability_mod = ability_mods.get(ability_key, 0)
            if isinstance(val, dict):
                ptype = (val.get("type") or "proficiency")
                ptype = ptype.lower() if isinstance(ptype, str) else "proficiency"
                try:
                    custom = int(val.get("bonus", 0))
                except (TypeError, ValueError):
                    custom = 0
                if custom != 0:
                    # Custom bonus (with or without prof/expertise type)
                    bonus = ability_mod + custom
                    sign = "+" if bonus >= 0 else ""
                    parts.append(f"{display_name} {sign}{bonus} (custom)")
                elif ptype == "none":
                    # Should not happen if we only save custom when bonus != 0
                    continue
                else:
                    if ptype == "expertise":
                        bonus = ability_mod + 2 * prof_bonus
                    else:
                        bonus = ability_mod + prof_bonus
                    sign = "+" if bonus >= 0 else ""
                    parts.append(f"{display_name} {sign}{bonus}")
            else:
                ptype = str(val).lower() if val else "proficiency"
                if ptype == "expertise":
                    bonus = ability_mod + 2 * prof_bonus
                else:
                    bonus = ability_mod + prof_bonus
                sign = "+" if bonus >= 0 else ""
                parts.append(f"{display_name} {sign}{bonus}")
        return ", ".join(parts) if parts else ""
    
    def has_saving_throw_proficiency(self, entity: Entity, ability_key: str) -> bool:
        """Check if entity has saving throw proficiency for given ability."""
        for prop in entity.properties:
            if prop.key == "saving_throw_proficiencies":
                try:
                    proficiencies = json.loads(prop.value)
                    if isinstance(proficiencies, dict):
                        return proficiencies.get(ability_key, False)
                except (json.JSONDecodeError, TypeError):
                    pass
        return False
    
    def calculate_save_mod(self, entity: Entity, ability_key: str, base_modifier: str) -> str:
        """Calculate save modifier including proficiency bonus if applicable."""
        if not entity:
            # No entity, return base modifier
            return base_modifier if base_modifier else "-"
        
        # Parse base modifier
        try:
            if base_modifier.startswith('+'):
                base_mod = int(base_modifier[1:])
            elif base_modifier.startswith('-'):
                base_mod = int(base_modifier)
            else:
                base_mod = int(base_modifier) if base_modifier else 0
        except (ValueError, TypeError):
            base_mod = 0
        
        # Check if has saving throw proficiency
        if self.has_saving_throw_proficiency(entity, ability_key):
            proficiency_bonus = self.get_proficiency_bonus(entity)
            total_mod = base_mod + proficiency_bonus
            if total_mod >= 0:
                return f"+{total_mod}"
            else:
                return str(total_mod)
        
        # No proficiency, return base modifier
        if base_mod >= 0 and base_modifier:
            return f"+{base_mod}" if not base_modifier.startswith('+') else base_modifier
        elif base_mod < 0:
            return str(base_mod)
        else:
            return base_modifier if base_modifier else "-"
    
    def create_ability_scores_widget(self, ability_scores: dict, entity_name: str = "", entity: Entity = None) -> QWidget:
        """Create a widget to display ability scores side by side in a grid layout (3x2)."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                border-radius: 4px;
                background-color: #2b2b2b;
                padding: 8px;
            }
        """)
        
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # Grid layout for ability scores (2 rows x 3 columns)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Ability names and display order
        ability_names = ["str", "dex", "con", "int", "wis", "cha"]
        ability_display_names = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        
        for i, (ability_name, display_name) in enumerate(zip(ability_names, ability_display_names)):
            row = i // 3
            col = i % 3
            
            if ability_name not in ability_scores:
                continue
            
            # Parse ability score
            score_value = ability_scores[ability_name]
            score, modifier = self.parse_ability_score(score_value)
            
            # Create container for this ability
            ability_widget = QWidget()
            ability_widget.setStyleSheet("""
                QWidget {
                    background-color: #3c3c3c;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
            ability_layout = QVBoxLayout(ability_widget)
            ability_layout.setContentsMargins(6, 4, 6, 4)
            ability_layout.setSpacing(2)
            
            # Ability name (bold, centered)
            name_frame = QFrame()
            name_frame.setStyleSheet("""
                QFrame {
                    background-color: #313131;
                    border-radius: 4px;
                    padding: 2px 6px;
                    min-width: 28px;
                    min-height: 18px;
                }
            """)
            name_layout = QVBoxLayout(name_frame)
            name_layout.setContentsMargins(0, 0, 0, 0)
            name_label = QLabel(display_name)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setStyleSheet("""
                QLabel {
                    color: #E2E8F0;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
            name_layout.addWidget(name_label)
            ability_layout.addWidget(name_frame)
            
            # Score value (smaller, white, centered)
            score_label = QPushButton(score if score else "-")
            score_label.setFlat(True)
            score_label.setEnabled(False)
            score_label.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    border: 1px solid #4c4c4c;
                    border-radius: 4px;
                    color: #FFFFFF;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 4px 8px;
                    min-width: 32px;
                    min-height: 24px;
                }
                QPushButton:hover {
                    background-color: #4c4c4c;
                }
            """)
            ability_layout.addWidget(score_label)
            
            # MOD and SAVE in horizontal layout
            mod_save_container = QWidget()
            mod_save_layout = QHBoxLayout(mod_save_container)
            mod_save_layout.setContentsMargins(0, 0, 0, 0)
            mod_save_layout.setSpacing(8)
            
            # MOD widget
            mod_widget = QWidget()
            mod_layout = QVBoxLayout(mod_widget)
            mod_layout.setContentsMargins(0, 0, 0, 0)
            mod_layout.setSpacing(2)
            
            mod_header = QLabel("MOD")
            mod_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mod_header.setStyleSheet("font-size: 7px; color: #E2E8F0; background-color: #313131;")
            mod_layout.addWidget(mod_header)
            
            mod_value = QPushButton(modifier if modifier else "-")
            mod_value.setFlat(True)
            mod_value.setEnabled(True)
            mod_value.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    border: 1px solid #4c4c4c;
                    border-radius: 4px;
                    color: #5DADE2;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 2px 6px;
                    min-width: 24px;
                    min-height: 16px;
                }
                QPushButton:hover {
                    background-color: #4c4c4c;
                }
            """)
            # Store entity name and ability info for click handler
            mod_value.setProperty("entity_name", entity_name)
            mod_value.setProperty("ability_name", display_name)
            mod_value.setProperty("modifier", modifier)
            mod_value.clicked.connect(lambda checked, btn=mod_value: self.on_mod_clicked(btn))
            mod_layout.addWidget(mod_value)
            mod_save_layout.addWidget(mod_widget)
            
            # SAVE widget
            save_widget = QWidget()
            save_layout = QVBoxLayout(save_widget)
            save_layout.setContentsMargins(0, 0, 0, 0)
            save_layout.setSpacing(2)
            
            save_header = QLabel("SAVE")
            save_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            save_header.setStyleSheet("font-size: 7px; color: #E2E8F0; background-color: #313131;")
            save_layout.addWidget(save_header)
            
            # Calculate save mod with proficiency if applicable
            save_mod = self.calculate_save_mod(entity if entity else None, ability_name.lower(), modifier)
            save_value = QPushButton(save_mod if save_mod else "-")
            save_value.setFlat(True)
            save_value.setEnabled(True)
            save_value.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    border: 1px solid #4c4c4c;
                    border-radius: 4px;
                    color: #5DADE2;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 2px 6px;
                    min-width: 24px;
                    min-height: 16px;
                }
                QPushButton:hover {
                    background-color: #4c4c4c;
                }
            """)
            # Store entity name and ability info for click handler
            save_value.setProperty("entity_name", entity_name)
            save_value.setProperty("ability_name", display_name)
            save_value.setProperty("modifier", save_mod)
            save_value.clicked.connect(lambda checked, btn=save_value: self.on_save_clicked(btn))
            save_layout.addWidget(save_value)
            mod_save_layout.addWidget(save_widget)
            
            mod_save_layout.addStretch()
            ability_layout.addWidget(mod_save_container)
            
            grid_layout.addWidget(ability_widget, row, col)
        
        main_layout.addLayout(grid_layout)
        
        widget.setMinimumHeight(100)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        return widget
    
    def create_section_widget(
        self,
        section_type: str,
        content: str,
        entity_name: str = "",
        ability_name: str = "",
    ) -> QWidget:
        """Create a widget to display a section. entity_name/ability_name used for dice link console output."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                border-radius: 4px;
                background-color: transparent;
                padding: 0px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)
        
        # Section header
        header = QLabel(self.format_section_type(section_type))
        header.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 12px;
                color: #F4A460;
                padding: 0px;
                margin-bottom: 0px;
            }
        """)
        layout.addWidget(header)
        
        # Section separator (thin line under section header)
        section_separator = QFrame()
        section_separator.setFrameShape(QFrame.Shape.HLine)
        section_separator.setStyleSheet("""
            QFrame {
                background-color: #F4A460;
                border: none;
                max-height: 1px;
            }
        """)
        section_separator.setFixedHeight(1)
        layout.addWidget(section_separator)
        
        # Section content (markdown-style formatting, clickable words + dice as links)
        content_text = self.format_section_content(content)
        content_text = self._wrap_clickable_words(content_text)
        content_text = self._wrap_clickable_dice(content_text)
        content_text = self._wrap_clickable_to_hit(content_text)
        content_label = QLabel(content_text)
        content_label.setStyleSheet("""
            QLabel {
                color: #CBD5E0;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        content_label.setOpenExternalLinks(False)
        en = entity_name or "Unknown"
        ab = ability_name or section_type.replace("_", " ").title()
        content_label.linkActivated.connect(
            lambda link, e=en, a=ab: self.on_statblock_word_clicked(link, entity_name=e, ability_name=a)
        )
        layout.addWidget(content_label)
        
        return widget
    
    def format_section_type(self, section_type: str) -> str:
        """Format section type for display."""
        return section_type.replace("_", " ").title()
    
    def _wrap_clickable_words(self, html: str) -> str:
        """Wrap clickable terms in HTML with <a href='word:Term'> so linkActivated is emitted on click."""
        if not html or not self.CLICKABLE_WORDS:
            return html
        from html import escape as html_escape
        replacements = []  # list of (href_term, display_text) to preserve original casing

        def make_repl(term):
            def repl(m):
                replacements.append((term, m.group(1)))
                return f"__CLK_{len(replacements) - 1}__"
            return repl

        text = html
        for term in sorted(self.CLICKABLE_WORDS, key=len, reverse=True):
            text = re.sub(
                r"\b(" + re.escape(term) + r")\b",
                make_repl(term),
                text,
                flags=re.IGNORECASE,
            )
        for i, (href_term, display) in enumerate(replacements):
            safe = html_escape(display)
            link = f'<a href="word:{href_term}" style="color:#5DADE2;text-decoration:underline;">{safe}</a>'
            text = text.replace(f"__CLK_{i}__", link)
        return text

    # Regex to find dice expressions: 2d6, d20, 1d8+3, d10+8, d10 + 8, 3d10-2, etc.
    _DICE_PATTERN = re.compile(r"\b(\d*d\d+(?:\s*[+-]\s*\d+)?)\b", re.IGNORECASE)

    def _wrap_clickable_dice(self, html: str) -> str:
        """Wrap dice expressions (e.g. 2d6, 1d8+3) in clickable links; click rolls and shows result in console."""
        if not html:
            return html
        from html import escape as html_escape
        replacements = []  # list of (expression, display_text)

        def repl(m):
            expr = m.group(1)
            # Normalize for href (e.g. "2D6" -> "2d6"); display keeps original
            normalized = expr.strip().lower().replace(" ", "")
            if normalized.startswith("d"):
                normalized = "1" + normalized
            replacements.append((normalized, expr))
            return f"__DICE_{len(replacements) - 1}__"

        text = self._DICE_PATTERN.sub(repl, html)
        for i, (norm_expr, display) in enumerate(replacements):
            safe = html_escape(display)
            link = f'<a href="dice:{norm_expr}" style="color:#F4A460;text-decoration:underline;">{safe}</a>'
            text = text.replace(f"__DICE_{i}__", link)
        return text

    # Match "+14" or "-1" when followed by " to hit" (attack bonus -> roll d20+mod)
    _TO_HIT_PATTERN = re.compile(r"([+-]\d+)(\s+to\s+hit)")

    def _wrap_clickable_to_hit(self, html: str) -> str:
        """Wrap attack bonuses like '+14 to hit' so the +14 is clickable; click rolls 1d20+14 and shows in console."""
        if not html:
            return html
        from html import escape as html_escape
        replacements = []  # list of (dice_expr, display_text) e.g. ("1d20+14", "+14")

        def repl(m):
            mod_str = m.group(1)   # e.g. "+14" or "-1"
            rest = m.group(2)      # " to hit"
            # Roll 1d20 + modifier
            expr = "1d20" + mod_str
            replacements.append((expr, mod_str))
            return f"__TOHIT_{len(replacements) - 1}__" + rest

        text = self._TO_HIT_PATTERN.sub(repl, html)
        for i, (dice_expr, display) in enumerate(replacements):
            safe = html_escape(display)
            link = f'<a href="dice:{dice_expr}" style="color:#F4A460;text-decoration:underline;">{safe}</a>'
            text = text.replace(f"__TOHIT_{i}__", link)
        return text

    def format_section_content(self, content: str) -> str:
        """Format section content (basic markdown to HTML conversion)."""
        if not content:
            return ""
        
        # Convert **bold** to <b>bold</b>
        content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)
        
        # Convert *italic* to <i>italic</i> (only if not already bold markers)
        content = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', content)
        
        # Convert line breaks to <br>
        content = content.replace('\n', '<br>')
        
        # Convert bullet points (-) to HTML list items
        lines = content.split('<br>')
        in_list = False
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                if not in_list:
                    formatted_lines.append('<ul>')
                    in_list = True
                list_content = line[2:].strip()
                formatted_lines.append(f'<li>{list_content}</li>')
            else:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                if line:
                    formatted_lines.append(line)
                else:
                    formatted_lines.append('<br>')
        
        if in_list:
            formatted_lines.append('</ul>')
        
        return '<br>'.join(formatted_lines)
    
    def on_statblock_word_clicked(
        self,
        link: str,
        entity_name: str = "Unknown",
        ability_name: str = "Unknown",
    ):
        """Handle click on a clickable word or dice expression in statblock section content."""
        if link.startswith("word:"):
            term = link[5:].strip()
            if term:
                self.word_clicked.emit(term)
        elif link.startswith("dice:"):
            expr = link[5:].strip()
            if expr:
                self._roll_dice_and_show_in_console(expr, entity_name=entity_name, ability_name=ability_name)

    def _roll_dice_and_show_in_console(
        self,
        expression: str,
        entity_name: str = "Unknown",
        ability_name: str = "Unknown",
    ):
        """Roll dice expression (e.g. 2d6, 1d8+3) and emit result to console with entity and ability context."""
        result = DiceRoller.roll(expression)
        if result:
            message = (
                f"🎲 <span style='color: #FF5252;'>{entity_name}</span> - "
                f"<span style='color: #42A5F5;'>{ability_name}</span>: "
                f"<span style='color: #42A5F5;'>{result.expression}</span> = "
                f"<span style='color: #66BB6A;'>{result.total}</span> {result.details}"
            )
            signal_hub.console_output.emit(message)
        else:
            signal_hub.console_output.emit(
                f"🎲 <span style='color: #FF5252;'>{entity_name}</span> - "
                f"<span style='color: #42A5F5;'>{ability_name}</span>: "
                f"<span style='color: #FF5252;'>❌ Invalid dice expression:</span> {expression}"
            )
    
    def on_mod_clicked(self, button: QPushButton):
        """Handle MOD button click - roll D20 + modifier."""
        entity_name = button.property("entity_name") or "Unknown"
        ability_name = button.property("ability_name") or "Unknown"
        modifier_str = button.property("modifier") or "0"
        
        # Parse modifier (remove + if present, handle negative)
        try:
            if modifier_str.startswith('+'):
                modifier = int(modifier_str[1:])
            elif modifier_str.startswith('-'):
                modifier = int(modifier_str)
            else:
                modifier = int(modifier_str) if modifier_str else 0
        except (ValueError, TypeError):
            modifier = 0    
        
        # Roll D20
        roll = random.randint(1, 20)
        total = roll + modifier
        
        # Format modifier display
        if modifier == 0:
            dice_expr = "D20"
        else:
            mod_display = f"{'+' if modifier >= 0 else ''}{modifier}"
            dice_expr = f"D20{mod_display}"
        
        # Send to console with colored HTML
        message = (
            f"🎲 <span style='color: #FF5252;'>{entity_name}</span> - "
            f"<span style='color: #42A5F5;'>{ability_name} MOD</span>: "
            f"{dice_expr} = {roll} + {modifier} = <span style='color: #66BB6A;'>{total}</span>"
        )
        signal_hub.console_output.emit(message)
    
    def on_save_clicked(self, button: QPushButton):
        """Handle SAVE button click - roll D20 + modifier (with proficiency if applicable)."""
        entity_name = button.property("entity_name") or "Unknown"
        ability_name = button.property("ability_name") or "Unknown"
        modifier_str = button.property("modifier") or "0"
        
        # Parse modifier (remove + if present, handle negative)
        try:
            if modifier_str.startswith('+'):
                modifier = int(modifier_str[1:])
            elif modifier_str.startswith('-'):
                modifier = int(modifier_str)
            else:
                modifier = int(modifier_str) if modifier_str else 0
        except (ValueError, TypeError):
            modifier = 0
        
        # Roll D20
        roll = random.randint(1, 20)
        total = roll + modifier
        
        # Format modifier display
        if modifier == 0:
            dice_expr = "D20"
        else:
            mod_display = f"{'+' if modifier >= 0 else ''}{modifier}"
            dice_expr = f"D20{mod_display}"
        
        # Send to console with colored HTML
        message = (
            f"🎲 <span style='color: #FF5252;'>{entity_name}</span> - "
            f"<span style='color: #42A5F5;'>{ability_name} SAVE</span>: "
            f"{dice_expr} = {roll} + {modifier} = <span style='color: #66BB6A;'>{total}</span>"
        )
        signal_hub.console_output.emit(message)
    
    def on_data_saved(self, entity_type: str, data: dict):
        """Handle data saved signal - refresh display if item is in list."""
        entity_id = data.get("id") if isinstance(data, dict) else None
        
        # Check if saved item is in our custom list
        for item in self.custom_list:
            if item["type"] == "entity" and item["id"] == entity_id:
                # Refresh the display
                self.refresh_display()
                break
            elif item["type"] == "note" and item["id"] == entity_id:
                # Refresh the display
                self.refresh_display()
                break
    
    def on_data_selected(self, data_type: str, data: object):
        """Handle data selection from data manager - add to list if requested."""
        # This could be extended to auto-add selected items
        pass


class AddItemDialog(QDialog):
    """Dialog for adding items (entities, notes) to the custom list."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_item = None
        self.setup_ui()
        self.load_items()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Add Item to List")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        
        # Type selector
        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        type_label.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Entity", "Note"])
        self.type_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: #E2E8F0;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #4c4c4c;
                font-size: 11px;
            }
        """)
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Items list
        list_label = QLabel("Select Item:")
        list_label.setStyleSheet("color: #E2E8F0; font-size: 11px;")
        layout.addWidget(list_label)
        
        self.items_list = QListWidget()
        self.items_list.setStyleSheet("""
            QListWidget {
                background-color: #3c3c3c;
                color: #E2E8F0;
                border: 1px solid #4c4c4c;
                border-radius: 6px;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #4c4c4c;
            }
            QListWidget::item:selected {
                background-color: #5DADE2;
            }
        """)
        layout.addWidget(self.items_list)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet("""
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
        """)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet("""
            QPushButton {
                background-color: #718096;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover {
                background-color: #4A5568;
            }
        """)
        layout.addWidget(buttons)
        
    def on_type_changed(self, index: int):
        """Handle type selection change."""
        self.load_items()
    
    def load_items(self):
        """Load items based on selected type."""
        self.items_list.clear()
        item_type = self.type_combo.currentText().lower()
        
        try:
            with DatabaseManager() as db:
                if item_type == "entity":
                    entities = db.query(Entity).order_by(Entity.name).all()
                    for entity in entities:
                        item = QListWidgetItem(f"{entity.name} ({entity.type})")
                        item.setData(Qt.ItemDataRole.UserRole, {
                            "type": "entity",
                            "id": entity.id,
                            "name": entity.name
                        })
                        self.items_list.addItem(item)
                elif item_type == "note":
                    notes = db.query(Note).order_by(Note.title).all()
                    for note in notes:
                        item = QListWidgetItem(note.title)
                        item.setData(Qt.ItemDataRole.UserRole, {
                            "type": "note",
                            "id": note.id,
                            "name": note.title
                        })
                        self.items_list.addItem(item)
        except Exception as e:
            print(f"Error loading items: {e}")
            import traceback
            traceback.print_exc()
    
    def accept(self):
        """Handle dialog acceptance."""
        current_item = self.items_list.currentItem()
        if current_item:
            self.selected_item = current_item.data(Qt.ItemDataRole.UserRole)
            super().accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select an item to add.")
    
    def get_selected_item(self) -> dict:
        """Get the selected item."""
        return self.selected_item

