"""Settings UI: two-pane layout — left nav, right scrollable content with section headings and setting rows (app theme: neutral dark grays)."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QDialogButtonBox, QMessageBox,
    QStackedWidget, QWidget, QFrame, QCheckBox, QScrollArea,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QFocusEvent

from core.settings import (
    get_combat_tracker_property_keys,
    set_combat_tracker_property_keys,
    get_combat_tracker_show_mark_defeated,
    set_combat_tracker_show_mark_defeated,
)

# Shared styles (app theme: neutral dark grays)
_PAGE_TITLE = "font-weight: bold; color: #E2E8F0; font-size: 16px; margin-bottom: 4px;"
_SECTION_HEADING = "font-weight: bold; color: #E2E8F0; font-size: 13px; margin-top: 16px;"
_ROW_TITLE = "font-weight: 500; color: #E2E8F0; font-size: 12px;"
_ROW_DESC = "color: #888; font-size: 11px;"

# Display label -> storage key for combat tracker stats
STAT_SUGGESTIONS = [
    ("HP", "hp"),
    ("AC", "ac"),
    ("Initiative", "initiative"),
    ("Speed", "speed"),
    ("Passive Perception", "passive_perception"),
    ("Conditions", "conditions"),
]


def _key_to_display(key: str) -> str:
    """Return display label for a storage key (e.g. hp -> HP)."""
    key = (key or "").strip().lower()
    for label, k in STAT_SUGGESTIONS:
        if k == key:
            return label
    return key.replace("_", " ").title() if key else key


def _add_section_heading(layout: QVBoxLayout, text: str) -> None:
    lbl = QLabel(text)
    lbl.setStyleSheet(_SECTION_HEADING)
    layout.addWidget(lbl)


def _add_setting_row(layout: QVBoxLayout, title: str, description: str, control: QWidget) -> None:
    """Cursor-style row: title + description left, control right-aligned."""
    row = QWidget()
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 6, 0, 6)
    row_layout.setSpacing(16)
    left = QWidget()
    left_layout = QVBoxLayout(left)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(2)
    t = QLabel(title)
    t.setStyleSheet(_ROW_TITLE)
    t.setWordWrap(True)
    left_layout.addWidget(t)
    d = QLabel(description)
    d.setStyleSheet(_ROW_DESC)
    d.setWordWrap(True)
    left_layout.addWidget(d)
    row_layout.addWidget(left, stretch=1)
    row_layout.addWidget(control, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(row)


def _make_toggle_checkbox() -> QCheckBox:
    """Standard checkbox (fully clickable); label/description are in the setting row."""
    cb = QCheckBox()
    cb.setStyleSheet("color: #E2E8F0;")
    return cb


def _pill_style(bg: str = "#3c3c3c") -> str:
    return (
        f"QPushButton {{ background-color: {bg}; color: #E2E8F0; border: none; "
        "border-radius: 12px; padding: 6px 12px; font-size: 11px; } "
        "QPushButton:hover { background-color: #4c4c4c; } "
        "QPushButton:pressed { background-color: #2b2b2b; }"
    )


class _AddStatLineEdit(QLineEdit):
    """Consumes Enter so the settings dialog does not close when adding a stat."""

    focusLost = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
            self.returnPressed.emit()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event: QFocusEvent):
        super().focusOutEvent(event)
        self.focusLost.emit()


class CombatTrackerSettingsPage(QWidget):
    """Combat tracker: visible stats (drag to reorder) + context menu option."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pills_container = None  # QWidget for pills row, rebuilt on _load / _sync_pills
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Page title
        title = QLabel("Combat Tracker Settings")
        title.setStyleSheet(_PAGE_TITLE)
        layout.addWidget(title)

        # --- Visible Stats ---
        _add_section_heading(layout, "Visible Stats")
        hint = QLabel("Choose which stats appear in the combat tracker.")
        hint.setWordWrap(True)
        hint.setStyleSheet(_ROW_DESC)
        layout.addWidget(hint)

        # Pills row (current stats + "+ Add" button that reveals text field)
        self._pills_container = QWidget()
        pills_layout = QHBoxLayout(self._pills_container)
        pills_layout.setContentsMargins(0, 4, 0, 4)
        pills_layout.setSpacing(8)
        layout.addWidget(self._pills_container)
        self._add_btn = QPushButton("+ Add")
        self._add_btn.setStyleSheet(_pill_style("#2b2b2b"))
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add_btn_clicked)
        self._add_edit = _AddStatLineEdit()
        self._add_edit.setPlaceholderText("Stat name…")
        self._add_edit.setMinimumWidth(120)
        self._add_edit.setStyleSheet(
            "QLineEdit { background-color: #2b2b2b; color: #E2E8F0; padding: 6px 12px; border-radius: 12px; "
            "border: 1px solid #4c4c4c; font-size: 11px; }"
        )
        self._add_edit.returnPressed.connect(self._on_add_edit_enter)
        self._add_edit.focusLost.connect(self._on_add_edit_focus_lost)
        self._add_edit.setVisible(False)

        # Drag to reorder
        reorder_hint = QLabel("Drag to reorder how stats appear.")
        reorder_hint.setStyleSheet(_ROW_DESC)
        layout.addWidget(reorder_hint)

        row_layout = QHBoxLayout()
        self.keys_list = QListWidget()
        self.keys_list.setMinimumHeight(120)
        self.keys_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.keys_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.keys_list.setStyleSheet(
            "QListWidget { background-color: #2b2b2b; border: 1px solid #4c4c4c; border-radius: 6px; color: #E2E8F0; padding: 4px; } "
            "QListWidget::item { padding: 6px 8px; } "
            "QListWidget::item:selected { background-color: #3c3c3c; }"
        )
        self.keys_list.model().layoutChanged.connect(self._sync_pills)
        row_layout.addWidget(self.keys_list)
        # TODO: Re-add Suggestions panel (right side): pills for HP, AC, Initiative, Speed, Passive Perception, Conditions; click adds stat to list.
        layout.addLayout(row_layout)

        # --- Context Menu ---
        _add_section_heading(layout, "Context Menu")
        self.show_mark_defeated_cb = _make_toggle_checkbox()
        _add_setting_row(
            layout,
            "Enable 'Mark as defeated'",
            "Adds a right-click option to mark combatants as defeated or alive again.",
            self.show_mark_defeated_cb,
        )

        layout.addStretch()

    def _sync_pills(self):
        """Rebuild pills row from current keys_list; keep + Add button and text field."""
        pills_layout = self._pills_container.layout()
        while pills_layout.count():
            child = pills_layout.takeAt(0)
            w = child.widget()
            if w is not None and w is not self._add_btn and w is not self._add_edit:
                w.deleteLater()
        for i in range(self.keys_list.count()):
            item = self.keys_list.item(i)
            key = item.data(Qt.ItemDataRole.UserRole)
            if key is None:
                key = (item.text() or "").strip().lower()
            if not key:
                continue
            label = _key_to_display(key)
            btn = QPushButton(label)
            btn.setStyleSheet(_pill_style())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("key_index", i)
            btn.clicked.connect(self._on_pill_clicked)
            pills_layout.addWidget(btn)
        pills_layout.addWidget(self._add_btn)
        pills_layout.addWidget(self._add_edit)
        pills_layout.addStretch()
        self._add_btn.setVisible(True)
        self._add_edit.setVisible(False)

    def _on_add_btn_clicked(self):
        """Show the add-stat text field and focus it."""
        self._add_btn.setVisible(False)
        self._add_edit.setVisible(True)
        self._add_edit.clear()
        self._add_edit.setFocus()

    def _on_add_edit_focus_lost(self):
        """When text field loses focus, hide it and show + Add button again."""
        self._add_edit.setVisible(False)
        self._add_btn.setVisible(True)

    def _on_pill_clicked(self):
        btn = self.sender()
        if isinstance(btn, QPushButton):
            idx = btn.property("key_index")
            if idx is not None and 0 <= idx < self.keys_list.count():
                self.keys_list.takeItem(idx)
                self._sync_pills()

    def _on_add_edit_enter(self):
        """Add stat from the '+ Add' text field on Enter."""
        if not getattr(self, "_add_edit", None):
            return
        raw = self._add_edit.text().strip()
        if not raw:
            return
        key = raw.lower().replace(" ", "_")
        if key not in self.get_keys():
            item = QListWidgetItem(_key_to_display(key))
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.keys_list.addItem(item)
        self._add_edit.clear()
        self._sync_pills()

    def _add_suggestion_key(self, key: str):
        if key in self.get_keys():
            return
        item = QListWidgetItem(_key_to_display(key))
        item.setData(Qt.ItemDataRole.UserRole, key)
        self.keys_list.addItem(item)
        self._sync_pills()

    def _load(self):
        keys = get_combat_tracker_property_keys()
        self.keys_list.clear()
        for k in keys:
            item = QListWidgetItem(_key_to_display(k))
            item.setData(Qt.ItemDataRole.UserRole, k)
            self.keys_list.addItem(item)
        self._sync_pills()
        self.show_mark_defeated_cb.setChecked(get_combat_tracker_show_mark_defeated())

    def get_keys(self):
        keys = []
        for i in range(self.keys_list.count()):
            item = self.keys_list.item(i)
            k = item.data(Qt.ItemDataRole.UserRole)
            if k is None:
                k = (item.text() or "").strip().lower()
            if k and k not in keys:
                keys.append(k)
        return keys

    def save(self):
        keys = self.get_keys()
        if not keys:
            QMessageBox.warning(
                self,
                "Empty list",
                "Add at least one stat (e.g. HP, AC) for the combat tracker.",
            )
            return False
        set_combat_tracker_property_keys(keys)
        set_combat_tracker_show_mark_defeated(self.show_mark_defeated_cb.isChecked())
        return True


def _placeholder_page(title: str) -> QWidget:
    """Build a placeholder content page with a section heading."""
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(24, 24, 24, 24)
    _add_section_heading(layout, "General")
    label = QLabel(f"No options available yet for {title}.")
    label.setStyleSheet(_ROW_DESC)
    label.setWordWrap(True)
    layout.addWidget(label)
    layout.addStretch()
    return w


class SettingsDialog(QDialog):
    """Dialog with left nav list (Combat tracker, Statblock viewer, Data manager, Knowledge base) and right content."""

    NAV_ITEMS = ["Combat tracker", "Statblock viewer", "Data manager", "Knowledge base"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(720)
        self.setMinimumHeight(520)
        self.resize(800, 580)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Row: nav (left) + content (right)
        row = QHBoxLayout()
        row.setSpacing(0)

        # Left: nav list (app theme)
        nav_frame = QFrame()
        nav_frame.setObjectName("SettingsNav")
        nav_frame.setStyleSheet(
            """
            QFrame#SettingsNav {
                background-color: #2b2b2b;
                border-right: 1px solid #4c4c4c;
            }
        """
        )
        nav_frame.setFixedWidth(220)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 16, 0, 16)

        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet(
            """
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                padding: 4px 0;
            }
            QListWidget::item {
                padding: 10px 16px;
                color: #E2E8F0;
                font-size: 12px;
            }
            QListWidget::item:selected {
                background-color: #3c3c3c;
                border-left: 3px solid #5DADE2;
                color: #E2E8F0;
            }
            QListWidget::item:hover:!selected {
                background-color: #353535;
            }
        """
        )
        for title in self.NAV_ITEMS:
            self.nav_list.addItem(QListWidgetItem(title))
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        nav_layout.addWidget(self.nav_list)
        row.addWidget(nav_frame)

        # Right: scrollable content per category (Cursor-style — no section list, single scroll area per page)
        self._combat_tracker_page = CombatTrackerSettingsPage(self)
        pages = [
            self._combat_tracker_page,
            _placeholder_page("Statblock viewer"),
            _placeholder_page("Data manager"),
            _placeholder_page("Knowledge base"),
        ]
        self.right_stacked = QStackedWidget()
        for page_widget in pages:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet(
                "QScrollArea { background-color: #2b2b2b; border: none; } "
                "QScrollArea > QWidget > QWidget { background-color: #2b2b2b; }"
            )
            scroll.setWidget(page_widget)
            self.right_stacked.addWidget(scroll)

        self.right_stacked.setCurrentIndex(0)
        row.addWidget(self.right_stacked, stretch=1)
        main_layout.addLayout(row)

        # Bottom: buttons (full width)
        button_bar = QFrame()
        button_bar.setStyleSheet("background-color: #252525; border-top: 1px solid #4c4c4c;")
        bar_layout = QHBoxLayout(button_bar)
        bar_layout.setContentsMargins(16, 10, 16, 10)
        bar_layout.addStretch()
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._apply_and_accept)
        self.buttons.rejected.connect(self.reject)
        bar_layout.addWidget(self.buttons)
        main_layout.addWidget(button_bar)

    def _on_nav_changed(self, row: int):
        if 0 <= row < self.right_stacked.count():
            self.right_stacked.setCurrentIndex(row)

    def _apply_and_accept(self):
        if isinstance(self._combat_tracker_page, CombatTrackerSettingsPage) and not self._combat_tracker_page.save():
            return
        self.accept()


def open_settings_dialog(parent=None) -> bool:
    """Show the settings dialog. Returns True if user accepted, False otherwise."""
    dlg = SettingsDialog(parent)
    return dlg.exec() == QDialog.DialogCode.Accepted
