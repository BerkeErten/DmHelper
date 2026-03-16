"""Placeholder content for the Display Menu when no item is selected."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame,
)
from PyQt6.QtCore import Qt

# Match app dark theme
_BG = "#2b2b2b"
_TEXT_STYLE = "color: #94a3b8; font-size: 13px;"


class PlaceholderDisplayWidget(QWidget):
    """Scrollable empty state: 'Select an item to display'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {_BG}; border: none; }} "
            f"QScrollArea > QWidget > QWidget {{ background-color: {_BG}; }}"
        )

        inner = QWidget()
        inner.setStyleSheet(f"background-color: {_BG};")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(24, 24, 24, 24)

        label = QLabel("Select an item to display")
        label.setStyleSheet(_TEXT_STYLE)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner_layout.addWidget(label)
        inner_layout.addStretch()

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        self.setMinimumWidth(200)
