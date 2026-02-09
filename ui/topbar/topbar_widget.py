"""Top bar widget with session info and quick actions."""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from ui.base_widget import BaseWidget


class TopBarWidget(QWidget):
    """Top bar with session information and quick actions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # Session info
        self.session_label = QLabel("Session: No Active Session")
        self.session_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(self.session_label)
        
        # Spacer
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Quick action buttons
        self.new_note_btn = QPushButton("+ New Note")
        self.new_note_btn.setToolTip("Create a new note (Ctrl+T)")
        self.new_note_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        layout.addWidget(self.new_note_btn)
        
        self.new_stat_block_btn = QPushButton("📊 Stat Block")
        self.new_stat_block_btn.setToolTip("Create a new stat block tab")
        self.new_stat_block_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        layout.addWidget(self.new_stat_block_btn)
        
        self.dice_roller_btn = QPushButton("🎲 Roll Dice")
        self.dice_roller_btn.setToolTip("Open dice roller")
        self.dice_roller_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        layout.addWidget(self.dice_roller_btn)
        
        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.setToolTip("Search references (Ctrl+F)")
        self.search_btn.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        layout.addWidget(self.search_btn)
        
        # Set fixed height - more compact
        self.setFixedHeight(42)
        
    def connect_signals(self):
        """Connect signals and slots."""
        self.new_note_btn.clicked.connect(self.create_new_note)
        self.new_stat_block_btn.clicked.connect(self.create_new_stat_block)
        self.dice_roller_btn.clicked.connect(self.open_dice_roller)
        
    def create_new_note(self):
        """Create a new note tab."""
        from core.events import signal_hub
        import uuid
        note_id = f"Note-{str(uuid.uuid4())[:8]}"
        signal_hub.tab_created.emit(note_id)
    
    def create_new_stat_block(self):
        """Create a new stat block tab."""
        # Get the main window to access tab manager
        from PyQt6.QtWidgets import QApplication
        
        # Find the main window
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'tab_manager'):
                widget.tab_manager.add_stat_block_tab()
                break
        
    def open_dice_roller(self):
        """Open the dice roller dialog."""
        from ui.dialogs.dice_roller_dialog import DiceRollerDialog
        dialog = DiceRollerDialog(self)
        dialog.exec()
        
    def update_session_info(self, session_name: str):
        """Update the session label."""
        self.session_label.setText(f"Session: {session_name}")

