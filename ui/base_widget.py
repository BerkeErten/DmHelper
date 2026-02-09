"""Base widget interface for all UI components."""
from PyQt6.QtWidgets import QWidget
from abc import ABCMeta


class CombinedMeta(type(QWidget), ABCMeta):
    """Combined metaclass for QWidget and ABC."""
    pass


class BaseWidget(QWidget, metaclass=CombinedMeta):
    """Base class for all UI widgets with standard interface."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the UI components. Override in subclass."""
        raise NotImplementedError("Subclass must implement setup_ui()")
        
    def connect_signals(self):
        """Connect signals and slots. Override in subclass."""
        raise NotImplementedError("Subclass must implement connect_signals()")

