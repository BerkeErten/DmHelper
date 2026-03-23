"""Improvised Damage widget.

UI goals:
- Dice Examples as vertical cards (not a grid table)
- Damage by Level as zebra-striped table (light = panel bg, dark = subtle step down)
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QSizePolicy,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont


_BG = "#2b2b2b"
_PANEL_BG = "#2f2f2f"
_BORDER = "#3c3c3c"
_HEADER = "#E2E8F0"
_MUTED = "#94a3b8"
_TEXT = "#E2E8F0"
_ACCENT = "#5DADE2"
# Zebra: light rows match display panel bg; dark rows are a modest step darker.
_EVEN_ROW_BG = _BG
_ODD_ROW_BG = "#242424"

_SECTION_TITLE_STYLE = "color: #94a3b8; font-size: 12px; font-weight: 700;"
_BIG_TITLE_STYLE = "color: #E2E8F0; font-size: 14px; font-weight: 800;"
_DICE_CARD_STYLE = f"""
QFrame {{
    background-color: {_PANEL_BG};
    border-radius: 12px;
}}
"""

_DICE_LABEL_STYLE = "color: #E2E8F0; font-size: 13px; font-weight: 800;"
_DICE_DESC_STYLE = "color: #94a3b8; font-size: 12px;"

# Do not style QTableWidget::item here — on Windows/Fusion, item rules often ignore
# QTableWidgetItem.setBackground() and every row paints the same. Header is styled alone.
_TABLE_VIEW_STYLE = """
QTableWidget {
    background-color: transparent;
    border: none;
    gridline-color: transparent;
}
"""
_TABLE_HEADER_STYLE = f"""
QHeaderView::section {{
    background: #242424;
    color: {_HEADER};
    border: none;
    padding: 6px 8px;
    font-weight: 700;
    font-size: 12px;
}}
"""


class _DiceCard(QFrame):
    def __init__(self, dice: str, example: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_DICE_CARD_STYLE)
        self.setObjectName("DiceCard")
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._title = QLabel(dice)
        self._title.setStyleSheet(_DICE_LABEL_STYLE)

        self._desc = QLabel(example)
        self._desc.setStyleSheet(_DICE_DESC_STYLE)
        self._desc.setWordWrap(True)

        self._mode = None  # "v" or "h"
        self._apply_layout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_layout()

    def _apply_layout(self):
        horizontal = self.width() >= 260
        mode = "h" if horizontal else "v"
        if mode == self._mode:
            return
        self._mode = mode

        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)

        if horizontal:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(12, 4, 12, 10)
            layout.setSpacing(10)
            # Title left, description fills remaining space
            self._title.setFixedWidth(64)
            layout.addWidget(self._title, 0, Qt.AlignmentFlag.AlignTop)
            layout.addWidget(self._desc, 1, Qt.AlignmentFlag.AlignTop)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 4, 12, 10)
            layout.setSpacing(6)
            self._title.setFixedWidth(0)
            layout.addWidget(self._title, 0, Qt.AlignmentFlag.AlignTop)
            layout.addWidget(self._desc, 0, Qt.AlignmentFlag.AlignTop)


class ImprovisedDamageTableWidget(QWidget):
    """Improvised damage UI with dice cards and severity table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        top_title = QLabel("Improvised Damage")
        top_title.setStyleSheet(_BIG_TITLE_STYLE)
        root.addWidget(top_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background-color: transparent; border: none; } "
            "QScrollArea > QWidget > QWidget { background-color: transparent; }"
        )

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        # Damage by Level (table)
        lvl_title = QLabel("Damage by Level")
        lvl_title.setStyleSheet(_SECTION_TITLE_STYLE)
        inner_layout.addWidget(lvl_title)

        self._sev_table = QTableWidget(4, 3)
        self._sev_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._sev_table.setStyleSheet(_TABLE_VIEW_STYLE)
        self._sev_table.horizontalHeader().setStyleSheet(_TABLE_HEADER_STYLE)
        _tf = QFont(self._sev_table.font())
        _tf.setPixelSize(12)
        self._sev_table.setFont(_tf)
        self._sev_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._sev_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._sev_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._sev_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._sev_table.verticalHeader().setVisible(False)
        self._sev_table.horizontalHeader().setStretchLastSection(True)
        self._sev_table.setHorizontalHeaderLabels(["Level", "Nuisance", "Deadly"])

        sev_rows = [
            ("1–4", "5 (1d10)", "11 (2d10)"),
            ("5–10", "11 (2d10)", "22 (4d10)"),
            ("11–16", "22 (4d10)", "55 (10d10)"),
            ("17–20", "55 (10d10)", "99 (18d10)"),
        ]
        
        for r, (lvl, nui, dead) in enumerate(sev_rows):
            row_bg = QColor(_PANEL_BG) if r % 2 == 0 else QColor(_EVEN_ROW_BG)
            
            it0 = QTableWidgetItem(lvl)
            it1 = QTableWidgetItem(nui)
            it2 = QTableWidgetItem(dead)

            it0.setForeground(QColor(_TEXT))
            it1.setForeground(QColor(_TEXT))
            it2.setForeground(QColor(_TEXT))
            it0.setBackground(row_bg)
            it1.setBackground(row_bg)
            it2.setBackground(row_bg)

            self._sev_table.setItem(r, 0, it0)
            self._sev_table.setItem(r, 1, it1)
            self._sev_table.setItem(r, 2, it2)

        self._sev_table.resizeColumnsToContents()
        # Keep columns consistent for readability
        self._sev_table.setColumnWidth(0, 100)
        self._sev_table.setColumnWidth(1, 100)
        self._sev_table.setColumnWidth(2, 100)
        self._sev_table.resizeRowsToContents()
        _hdr = self._sev_table.horizontalHeader()
        _table_h = _hdr.sizeHint().height() + sum(
            self._sev_table.rowHeight(r) for r in range(self._sev_table.rowCount())
        )
        self._sev_table.setFixedHeight(_table_h)

        inner_layout.addWidget(self._sev_table)
        inner_layout.addSpacing(8)

        # Dice Examples (cards)
        dice_title = QLabel("Dice Examples")
        dice_title.setStyleSheet(_SECTION_TITLE_STYLE)
        inner_layout.addWidget(dice_title)

        dice_rows = [
            ("1d10", "Burned by coals, hit by a falling bookcase, pricked by a poison needle"),
            ("2d10", "Struck by lightning, stumbling into a firepit"),
            ("4d10", "Hit by falling rubble in a collapsing tunnel, tumbling into a vat of acid"),
            ("10d10", "Crushed by compacting walls, hit by whirling steel blades, wading through lava"),
            ("18d10", "Submerged in lava, hit by a crashing flying fortress"),
            ("24d10", "Tumbling into a vortex of fire on the Elemental Plane of Fire, crushed in the jaws of a godlike creature or a moon-sized monster"),
        ]
        
        
        for dice, text in dice_rows:
            inner_layout.addWidget(_DiceCard(dice, text))

     
        scroll.setWidget(inner)
        root.addWidget(scroll)

