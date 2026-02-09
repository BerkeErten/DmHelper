"""Application initialization and configuration."""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import sys
from core.config import APP_NAME, DEFAULT_THEME
from core.events import signal_hub


class DMHelperApp(QApplication):
    """Main application class with global settings."""
    
    def __init__(self, argv):
        super().__init__(argv)
        
        # Set application metadata
        self.setApplicationName(APP_NAME)
        
        # Configure application settings
        self.setup_fonts()
        self.setup_theme(DEFAULT_THEME)
        
    def setup_fonts(self):
        """Configure default application fonts."""
        font = QFont("Segoe UI", 10)
        self.setFont(font)
        
    def setup_theme(self, theme_name: str):
        """Apply theme to the application."""
        if theme_name == "dark":
            self.setStyle("Fusion")
            self.apply_dark_theme()
        else:
            self.setStyle("Fusion")
            
    def apply_dark_theme(self):
        """Apply dark theme styling."""
        dark_stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #e0e0e0;
        }
        QSplitter::handle {
            background-color: #3c3c3c;
        }
        QSplitter::handle:hover {
            background-color: #505050;
        }
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #505050;
            padding: 5px 15px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #252525;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #1e1e1e;
            border: 1px solid #3c3c3c;
            padding: 5px;
            border-radius: 3px;
        }
        QLabel {
            background-color: transparent;
        }
        QMenuBar {
            background-color: #2b2b2b;
            border-bottom: 1px solid #3c3c3c;
        }
        QMenuBar::item:selected {
            background-color: #3c3c3c;
        }
        QMenu {
            background-color: #2b2b2b;
            border: 1px solid #3c3c3c;
        }
        QMenu::item:selected {
            background-color: #3c3c3c;
        }
        """
        self.setStyleSheet(dark_stylesheet)


def create_app():
    """Factory function to create and configure the application."""
    app = DMHelperApp(sys.argv)
    return app

