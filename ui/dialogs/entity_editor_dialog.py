"""Entity editor dialog for creating/editing entities."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QLabel, QTextEdit, QComboBox, QFormLayout
)
from PyQt6.QtCore import Qt


class EntityEditorDialog(QDialog):
    """Dialog for creating or editing entities (NPCs, locations, items, etc.)."""
    
    def __init__(self, entity_type: str = "NPC", entity_data: dict = None, parent=None):
        super().__init__(parent)
        self.entity_type = entity_type
        self.entity_data = entity_data or {}
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """Setup the UI components."""
        title = "Edit" if self.entity_data else "New"
        self.setWindowTitle(f"{title} {self.entity_type}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Name field
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(f"Enter {self.entity_type.lower()} name...")
        form_layout.addRow("Name:", self.name_input)
        
        # Type/Category field (varies by entity type)
        self.type_input = QLineEdit()
        if self.entity_type == "NPC":
            self.type_input.setPlaceholderText("e.g., Wizard, Rogue, Merchant")
            form_layout.addRow("Class/Role:", self.type_input)
        elif self.entity_type == "Location":
            self.type_input.setPlaceholderText("e.g., Forest, Tavern, Dungeon")
            form_layout.addRow("Type:", self.type_input)
        elif self.entity_type == "Item":
            self.type_input.setPlaceholderText("e.g., Weapon, Potion, Armor")
            form_layout.addRow("Category:", self.type_input)
        elif self.entity_type == "Monster":
            self.type_input.setPlaceholderText("e.g., Dragon, Goblin, Undead")
            form_layout.addRow("Type:", self.type_input)
        
        # Description/Notes field
        description_label = QLabel("Description:")
        form_layout.addRow(description_label)
        
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter description and notes...")
        self.description_input.setMaximumHeight(200)
        form_layout.addRow(self.description_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
    def load_data(self):
        """Load existing entity data into fields."""
        if self.entity_data:
            self.name_input.setText(self.entity_data.get("name", ""))
            self.type_input.setText(self.entity_data.get("type", ""))
            self.description_input.setPlainText(self.entity_data.get("description", ""))
            
    def get_data(self):
        """Get the entity data from the form."""
        return {
            "name": self.name_input.text().strip(),
            "type": self.type_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "entity_type": self.entity_type
        }

