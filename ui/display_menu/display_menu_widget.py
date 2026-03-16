"""Display Menu container: stacked content driven by tree selection."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import Qt

from core.events import signal_hub
from ui.display_menu.placeholder_widget import PlaceholderDisplayWidget

_BG = "#2b2b2b"


class DisplayMenuWidget(QWidget):
    """Modular panel: QStackedWidget with placeholder at index 0; swaps content from data_selected."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(f"background-color: {_BG};")

        self._stack = QStackedWidget()
        self._stack.addWidget(PlaceholderDisplayWidget())
        layout.addWidget(self._stack)

    def connect_signals(self):
        signal_hub.data_selected.connect(self._on_data_selected)

    def _on_data_selected(self, data_type: str, data_object):
        """Show placeholder for now; later switch by data_type (entity, note, category, etc.)."""
        if not data_type or data_type == "none" or data_object is None:
            self._stack.setCurrentIndex(0)
            return
        # Future: set current widget by data_type / payload
        self._stack.setCurrentIndex(0)
