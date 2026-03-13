"""Wrapper widget that adds an attach icon in the upper right of tab pages (note or statblock)."""
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QToolButton,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal


# Height of the top bar that holds the attach icon
ATTACH_BAR_HEIGHT = 36


class TabPageWithAttach(QWidget):
    """
    Wraps a tab page widget (NoteEditor or StatBlockEditor) with an attach icon
    in the upper right corner. Forwards attribute/method access to the inner widget
    so tab manager logic (has_unsaved_changes, get_note_id, etc.) works unchanged.
    """

    attach_clicked = pyqtSignal()

    def __init__(self, content_widget: QWidget, parent=None):
        super().__init__(parent)
        self._content = content_widget
        self._content.setParent(self)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar: empty space on left, attach icon on the right (upper right corner)
        top_bar = QFrame()
        top_bar.setFixedHeight(ATTACH_BAR_HEIGHT)
        top_bar.setStyleSheet("background-color: #2b2b2b; border: none;")
        top_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.setSpacing(0)
        bar_layout.addStretch()

        # Paperclip icon (U+1F4CE) for "Attach" in upper right
        self._attach_btn = QToolButton()
        self._attach_btn.setText("\U0001f4ce")
        self._attach_btn.setToolTip("Attach")
        self._attach_btn.setFixedSize(28, 28)
        self._attach_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QToolButton:hover { background-color: #3c3c3c; }
            QToolButton:pressed { background-color: #4c4c4c; }
        """)
        self._attach_btn.clicked.connect(self.attach_clicked.emit)
        bar_layout.addWidget(self._attach_btn)

        layout.addWidget(top_bar)
        layout.addWidget(self._content, stretch=1)

    def __getattr__(self, name):
        """Forward unresolved attributes to the content widget."""
        return getattr(self._content, name)
