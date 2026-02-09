"""Quick reference widget for D&D rules and information."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QTextEdit, 
    QLabel, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from core.events import signal_hub


class QuickRefWidget(QWidget):
    """Quick reference panel for searching D&D rules and information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header_label = QLabel("Quick Reference")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header_label)
        
        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search rules, spells, items...")
        layout.addWidget(self.search_input)
        
        # Results area
        self.results_area = QTextEdit()
        self.results_area.setReadOnly(True)
        self.results_area.setPlaceholderText(
            "Search for D&D rules and references.\n\n"
            "Try searching for:\n"
            "• Spells (e.g., 'fireball')\n"
            "• Conditions (e.g., 'grappled')\n"
            "• Actions (e.g., 'dash')\n"
        )
        layout.addWidget(self.results_area)
        
        # Set minimum width
        self.setMinimumWidth(300)
        
    def connect_signals(self):
        """Connect signals and slots."""
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.returnPressed.connect(self.on_search_submitted)
        signal_hub.quickref_search.connect(self.perform_search)
        
    def on_search_changed(self, text: str):
        """Handle search text change."""
        # Real-time search would go here
        pass
        
    def on_search_submitted(self):
        """Handle search submission."""
        query = self.search_input.text().strip()
        if query:
            self.perform_search(query)
            
    def perform_search(self, query: str):
        """Perform search and display results."""
        # Placeholder implementation
        self.results_area.clear()
        self.results_area.append(f"<h3>Search Results for: '{query}'</h3>")
        self.results_area.append("<p><i>Search functionality not yet implemented.</i></p>")
        self.results_area.append("<p>This will eventually search through:</p>")
        self.results_area.append("<ul>")
        self.results_area.append("<li>Spells</li>")
        self.results_area.append("<li>Conditions</li>")
        self.results_area.append("<li>Rules</li>")
        self.results_area.append("<li>Items</li>")
        self.results_area.append("<li>Monsters</li>")
        self.results_area.append("</ul>")

