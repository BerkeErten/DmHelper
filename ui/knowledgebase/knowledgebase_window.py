"""Knowledge Base window - two columns: item list left, detail right."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QComboBox,
    QScrollArea, QFrame, QCheckBox, QFormLayout,
    QListWidget, QListWidgetItem, QPushButton, QTabWidget,
)
from PyQt6.QtCore import Qt
from core.database import DatabaseManager
from core.events import signal_hub
from core.settings import get_open_knowledge_base_at_startup, set_open_knowledge_base_at_startup
from models.entity import Entity
from sqlalchemy.orm import joinedload
import json
import re

# Category display names (same as Data Manager); order for chips
CATEGORY_NAMES = {
    "statblock": "Stat Blocks",
    "creature": "Creatures",
    "npc": "NPCs",
    "location": "Locations",
    "item": "Items",
    "spell": "Spells",
    "note": "Notes",
}
# Chip colors (reference-style accent)
CHIP_COLORS = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
    "#EC4899", "#06B6D4", "#84CC16",
]
# Chips sized like other filter controls (height 20px, padding aligned with QLineEdit/QComboBox)
CHIP_STYLE = """
    QPushButton {
        background-color: #374151;
        color: #E5E7EB;
        border: none;
        padding: 2px 6px;
        margin: 0;
        min-height: 20px;
        max-height: 20px;
        border-radius: 2px;
        font-size: 10px;
    }
    QPushButton:hover { background-color: #4B5563; }
    QPushButton:checked {
        background-color: %s;
        color: white;
    }
"""


def _format_property_value(value: str) -> str:
    if not value:
        return ""
    try:
        data = json.loads(value)
        if isinstance(data, list):
            return ", ".join(str(x) for x in data)
    except (json.JSONDecodeError, TypeError):
        pass
    return str(value)


class KnowledgeBaseWindow(QWidget):
    """Standalone window: filters + entity list on the left, detail panel on the right."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Knowledge Base")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setMinimumSize(420, 560)
        self.resize(580, 780)
        self._entity_cache = []  # list of (entity_id, name, type, properties_dict) for filtering
        self._all_property_keys = []  # distinct property keys for dropdown
        self._selected_category = None  # from chips; None = All
        self.setup_ui()
        self.connect_signals()
        self.load_entities()
        self.apply_filters()

    @staticmethod
    def _filter_label(text: str, style: str) -> QLabel:
        lbl = QLabel(text + ":")
        lbl.setStyleSheet(style)
        return lbl

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Top bar (minimal gap between title and checkbox)
        header = QHBoxLayout()
        header.setSpacing(4)
        title = QLabel("Knowledge Base")
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #E2E8F0;")
        header.addWidget(title)
        header.addStretch()
        self.open_at_startup_cb = QCheckBox("Open at startup")
        self.open_at_startup_cb.setChecked(get_open_knowledge_base_at_startup())
        self.open_at_startup_cb.setStyleSheet("color: #CBD5E0; font-size: 10px;")
        self.open_at_startup_cb.toggled.connect(lambda c: set_open_knowledge_base_at_startup(c))
        header.addWidget(self.open_at_startup_cb)
        layout.addLayout(header)

        # Filter bar — unified background
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame { background-color: #252525; border-radius: 2px; }
            QFrame QLabel { margin: 0; padding: 0; }
            QFrame QLineEdit, QFrame QComboBox {
                background-color: #2d2d2d;
                color: #E5E7EB;
                padding: 1px 4px;
                margin: 0;
                border: 1px solid #404040;
                border-radius: 2px;
            }
            QFrame QLineEdit:focus, QFrame QComboBox:focus {
                border-color: #525252;
            }
        """)
        filter_frame.setFrameShape(QFrame.Shape.NoFrame)
        filter_frame.setLineWidth(0)
        filter_frame.setMidLineWidth(0)
        filter_frame.setMaximumHeight(72)
        filter_layout = QVBoxLayout(filter_frame)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(0)

        # Row 1: Filter, Search, count, Reset
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(2)
        filter_label = QLabel("Filter")
        filter_label.setFixedHeight(14)
        row1.addWidget(filter_label)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(100)
        self.search_edit.setMaximumHeight(20)
        row1.addWidget(self.search_edit)
        self.count_label = QLabel("0 / 0")
        self.count_label.setStyleSheet("color: #94A3B8; font-size: 9px;")
        self.count_label.setFixedHeight(14)
        row1.addWidget(self.count_label)
        row1.addStretch()
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setStyleSheet("padding: 1px 6px; font-size: 9px;")
        self.reset_btn.clicked.connect(self._reset_filters)
        row1.addWidget(self.reset_btn)
        filter_layout.addLayout(row1)

        # Row 2: Tag, Property
        row3 = QHBoxLayout()
        row3.setContentsMargins(0, 0, 0, 0)
        row3.setSpacing(2)
        label_style = "color: #94A3B8; font-size: 9px; margin: 0; padding: 0;"
        tag_lbl = self._filter_label("Tag", label_style)
        tag_lbl.setFixedHeight(14)
        row3.addWidget(tag_lbl)
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("tag")
        self.tag_edit.setClearButtonEnabled(True)
        self.tag_edit.setMinimumWidth(60)
        self.tag_edit.setMaximumHeight(20)
        row3.addWidget(self.tag_edit)
        prop_lbl = self._filter_label("Prop", label_style)
        prop_lbl.setFixedHeight(14)
        row3.addWidget(prop_lbl)
        self.property_key_combo = QComboBox()
        self.property_key_combo.addItem("Any", None)
        self.property_key_combo.setMinimumWidth(72)
        self.property_key_combo.setMaximumHeight(20)
        row3.addWidget(self.property_key_combo)
        self.property_value_edit = QLineEdit()
        self.property_value_edit.setPlaceholderText("val")
        self.property_value_edit.setClearButtonEnabled(True)
        self.property_value_edit.setMinimumWidth(60)
        self.property_value_edit.setMaximumHeight(20)
        row3.addWidget(self.property_value_edit)
        row3.addStretch()
        filter_layout.addLayout(row3)

        # Row 3: Category chips (after tag area), left-aligned
        chips_wrapper = QFrame()
        chips_row = QHBoxLayout(chips_wrapper)
        chips_row.setContentsMargins(0, 0, 0, 0)
        chips_row.setSpacing(2)
        chips_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.category_chips = []
        all_btn = QPushButton("All")
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        all_btn.setStyleSheet(CHIP_STYLE % CHIP_COLORS[0])
        all_btn.clicked.connect(lambda: self._set_category_chip(None))
        self.category_chips.append((None, all_btn))
        chips_row.addWidget(all_btn)
        for i, (key, label) in enumerate(CATEGORY_NAMES.items()):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(CHIP_STYLE % CHIP_COLORS[(i + 1) % len(CHIP_COLORS)])
            btn.clicked.connect(lambda checked, k=key: self._set_category_chip(k))
            self.category_chips.append((key, btn))
            chips_row.addWidget(btn)
        chips_row.addStretch()
        filter_layout.addWidget(chips_wrapper)

        layout.addWidget(filter_frame)

        # Two columns side by side: left = item list (filter part), right = detail (reference UI)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left column: item list
        left = QWidget()
        left.setMinimumWidth(220)
        left.setMaximumWidth(380)
        left.setStyleSheet("background-color: #1e1e1e;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 2, 0, 0)
        left_layout.setSpacing(2)
        self.list_heading = QLabel("Entries")
        self.list_heading.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #E2E8F0; padding: 1px 0;"
        )
        left_layout.addWidget(self.list_heading)
        self.entity_list = QListWidget()
        self.entity_list.setMinimumHeight(160)
        self.entity_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 1px;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 2px 4px;
                color: #E5E7EB;
            }
            QListWidget::item:selected {
                background-color: #374151;
                color: #fff;
            }
            QListWidget::item:hover {
                background-color: #363636;
            }
        """)
        left_layout.addWidget(self.entity_list, 1)
        splitter.addWidget(left)

        # Right column: item detail
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background-color: #1e1e1e; }
            QTabBar::tab { padding: 2px 8px; font-size: 10px; color: #94A3B8; }
            QTabBar::tab:selected { color: #E2E8F0; font-weight: bold; border-bottom: 2px solid #3B82F6; }
        """)
        self.detail_placeholder = QFrame()
        self.detail_placeholder.setStyleSheet("QFrame { background-color: #1e1e1e; border: none; }")
        self.detail_layout = QVBoxLayout(self.detail_placeholder)
        self.detail_layout.setContentsMargins(6, 6, 6, 6)
        self.detail_layout.setSpacing(2)
        self._empty_label = QLabel("Select an item from the list.")
        self._empty_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_layout.addWidget(self._empty_label)
        self.detail_tabs.addTab(self.detail_placeholder, "Stat Block")
        self.info_placeholder = QFrame()
        self.info_placeholder.setStyleSheet("QFrame { background-color: #1e1e1e; border: none; }")
        self.info_layout = QVBoxLayout(self.info_placeholder)
        self.info_layout.setContentsMargins(6, 6, 6, 6)
        self.info_layout.setSpacing(2)
        self._info_empty = QLabel("Select an item for basic info.")
        self._info_empty.setStyleSheet("color: #6B7280; font-size: 11px;")
        self.info_layout.addWidget(self._info_empty)
        self.detail_tabs.addTab(self.info_placeholder, "Info")
        right_layout.addWidget(self.detail_tabs)
        right_scroll.setWidget(right_container)
        splitter.addWidget(right_scroll)

        splitter.setSizes([280, 400])
        layout.addWidget(splitter)

    def connect_signals(self):
        self.search_edit.textChanged.connect(self.apply_filters)
        self.tag_edit.textChanged.connect(self.apply_filters)
        self.property_key_combo.currentIndexChanged.connect(self.apply_filters)
        self.property_value_edit.textChanged.connect(self.apply_filters)
        self.entity_list.currentItemChanged.connect(self.on_selection_changed)
        signal_hub.data_saved.connect(self._on_data_saved)

    def _set_category_chip(self, category_key):
        """Set category filter from chip click; None = All."""
        self._selected_category = category_key
        for key, btn in self.category_chips:
            btn.setChecked(key == category_key)
        self.list_heading.setText(CATEGORY_NAMES.get(category_key, "Entries") if category_key else "Entries")
        self.apply_filters()

    def _reset_filters(self):
        """Clear all filters and reset chips to All."""
        self.search_edit.clear()
        self.tag_edit.clear()
        self.property_key_combo.setCurrentIndex(0)
        self.property_value_edit.clear()
        self._selected_category = None
        self.list_heading.setText("Entries")
        for key, btn in self.category_chips:
            btn.setChecked(key is None)
        self.apply_filters()

    def _on_data_saved(self, entity_type: str, entity_data: dict):
        """Refresh list when entities are saved elsewhere."""
        self.load_entities()

    def load_entities(self):
        """Load all entities with properties; populate cache and property keys."""
        self._entity_cache.clear()
        self._all_property_keys = []
        keys_set = set()
        try:
            with DatabaseManager() as db:
                entities = db.query(Entity).options(
                    joinedload(Entity.properties)
                ).order_by(Entity.name).all()
                for e in entities:
                    props = {p.key: (p.value or "") for p in (e.properties or [])}
                    self._entity_cache.append((e.id, e.name or "", e.type or "", props))
                    for k in props:
                        if k and k not in keys_set:
                            keys_set.add(k)
                            self._all_property_keys.append(k)
                self._all_property_keys.sort(key=str.lower)
        except Exception as ex:
            print(f"Knowledge Base load error: {ex}")
            import traceback
            traceback.print_exc()
            return
        # Refresh property key combo
        self.property_key_combo.clear()
        self.property_key_combo.addItem("Any", None)
        for k in self._all_property_keys:
            self.property_key_combo.addItem(k.replace("_", " ").title(), k)
        self.apply_filters()

    def apply_filters(self):
        search = self.search_edit.text().strip().lower()
        category = self._selected_category
        tag = self.tag_edit.text().strip().lower()
        prop_key = self.property_key_combo.currentData()
        prop_value = self.property_value_edit.text().strip().lower()

        filtered = []
        for eid, name, etype, props in self._entity_cache:
            if search and search not in (name or "").lower():
                continue
            if category and etype != category:
                continue
            if tag:
                found = False
                for v in props.values():
                    if v and tag in v.lower():
                        found = True
                        break
                if not found:
                    continue
            if prop_key:
                val = props.get(prop_key, "")
                if not val:
                    continue
                if prop_value and prop_value not in (val or "").lower():
                    continue
            cr = (props.get("challenge_rating") or props.get("cr") or "").strip()
            source = CATEGORY_NAMES.get(etype, (etype or "").title())
            filtered.append((eid, name or "(No name)", etype, cr, source))
        filtered.sort(key=lambda x: (x[1] or "").lower())

        total = len(self._entity_cache)
        self.count_label.setText(f"{len(filtered)} / {total}")

        self.entity_list.clear()
        for eid, name, etype, cr, source in filtered:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, eid)
            self.entity_list.addItem(item)

    def on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            self.show_empty_detail()
            return
        entity_id = current.data(Qt.ItemDataRole.UserRole)
        if entity_id:
            self.show_entity_detail(entity_id)
        else:
            self.show_empty_detail()

    def show_empty_detail(self):
        self._clear_detail_layout()
        self._clear_info_layout()
        self.detail_layout.addWidget(self._empty_label)
        self._empty_label.show()
        self.info_layout.addWidget(self._info_empty)
        self._info_empty.show()

    def _clear_layout_recursive(self, layout):
        """Remove and delete all widgets in a layout and its nested layouts."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout_recursive(item.layout())

    def _clear_detail_layout(self):
        while self.detail_layout.count():
            child = self.detail_layout.takeAt(0)
            if child.widget() and child.widget() != self._empty_label:
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout_recursive(child.layout())
        self._empty_label.hide()

    def _clear_info_layout(self):
        while self.info_layout.count():
            child = self.info_layout.takeAt(0)
            w = child.widget()
            if w and w != self._info_empty:
                w.deleteLater()
            elif child.layout():
                self._clear_layout_recursive(child.layout())
        self._info_empty.hide()

    def show_entity_detail(self, entity_id: str):
        self._clear_detail_layout()
        self._clear_info_layout()
        try:
            with DatabaseManager() as db:
                entity = db.query(Entity).options(
                    joinedload(Entity.properties),
                    joinedload(Entity.sections)
                ).filter(Entity.id == entity_id).first()
                if not entity:
                    self.show_empty_detail()
                    return
                _ = list(entity.properties or [])
                _ = list(entity.sections or [])
                self._build_detail_content(entity)
                self._build_info_content(entity)
        except Exception as e:
            print(f"Knowledge Base detail error: {e}")
            import traceback
            traceback.print_exc()
            lab = QLabel("Error loading entry.")
            lab.setStyleSheet("color: #EF4444;")
            self.detail_layout.addWidget(lab)

    def _build_detail_content(self, entity: Entity):
        # Title
        title = QLabel(entity.name or "Unnamed")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #E2E8F0;")
        title.setWordWrap(True)
        self.detail_layout.addWidget(title)
        # Type
        if entity.type:
            type_lab = QLabel(CATEGORY_NAMES.get(entity.type, entity.type.title()))
            type_lab.setStyleSheet("font-size: 12px; color: #94A3B8; margin-bottom: 8px;")
            self.detail_layout.addWidget(type_lab)
        # Properties
        if entity.properties:
            prop_frame = QFrame()
            prop_frame.setStyleSheet("background-color: transparent;")
            prop_layout = QFormLayout(prop_frame)
            prop_layout.setSpacing(4)
            for p in sorted(entity.properties, key=lambda x: (x.key or "").lower()):
                if not p.key:
                    continue
                key_label = QLabel(p.key.replace("_", " ").title() + ":")
                key_label.setStyleSheet("font-weight: bold; color: #E2E8F0; font-size: 11px;")
                val_label = QLabel(_format_property_value(p.value))
                val_label.setWordWrap(True)
                val_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                val_label.setStyleSheet("color: #CBD5E0; font-size: 11px;")
                prop_layout.addRow(key_label, val_label)
            self.detail_layout.addWidget(prop_frame)
        # Sections
        if entity.sections:
            sorted_sections = sorted(entity.sections, key=lambda s: (s.sort_order or 0, s.section_type or ""))
            for sec in sorted_sections:
                sec_heading = QLabel(sec.section_type.replace("_", " ").title())
                sec_heading.setStyleSheet("font-size: 12px; font-weight: bold; color: #94A3B8; margin-top: 12px;")
                self.detail_layout.addWidget(sec_heading)
                content = (sec.content or "").strip()
                if content:
                    # Simple markdown-like: **bold** and newlines
                    content = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", content)
                    content = content.replace("\n", "<br>")
                    content_lab = QLabel(content)
                    content_lab.setWordWrap(True)
                    content_lab.setTextFormat(Qt.TextFormat.RichText)
                    content_lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    content_lab.setStyleSheet("color: #CBD5E0; font-size: 11px;")
                    self.detail_layout.addWidget(content_lab)
        self.detail_layout.addStretch()

    # Section types shown in Info tab (lore only; matches statblock viewer lore)
    _INFO_LORE_SECTIONS = {"description", "background", "history", "personality", "appearance", "notes", "lore"}

    def _build_info_content(self, entity: Entity):
        """Fill Info tab with name, type, and lore sections only."""
        name_lab = QLabel(entity.name or "Unnamed")
        name_lab.setStyleSheet("font-size: 16px; font-weight: bold; color: #E2E8F0;")
        self.info_layout.addWidget(name_lab)
        if entity.type:
            type_lab = QLabel(CATEGORY_NAMES.get(entity.type, entity.type.title()))
            type_lab.setStyleSheet("color: #94A3B8; font-size: 12px;")
            self.info_layout.addWidget(type_lab)
        if entity.sections:
            sorted_sections = sorted(entity.sections, key=lambda s: (s.sort_order or 0, s.section_type or ""))
            for sec in sorted_sections:
                if (sec.section_type or "").strip().lower() not in self._INFO_LORE_SECTIONS:
                    continue
                sec_heading = QLabel(sec.section_type.replace("_", " ").title())
                sec_heading.setStyleSheet("font-size: 12px; font-weight: bold; color: #94A3B8; margin-top: 12px;")
                self.info_layout.addWidget(sec_heading)
                content = (sec.content or "").strip()
                if content:
                    content = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", content)
                    content = content.replace("\n", "<br>")
                    content_lab = QLabel(content)
                    content_lab.setWordWrap(True)
                    content_lab.setTextFormat(Qt.TextFormat.RichText)
                    content_lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    content_lab.setStyleSheet("color: #CBD5E0; font-size: 11px;")
                    self.info_layout.addWidget(content_lab)
        self.info_layout.addStretch()
