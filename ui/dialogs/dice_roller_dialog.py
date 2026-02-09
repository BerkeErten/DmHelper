"""Dice roller dialog window."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QTextEdit, QLabel, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from core.dice_roller import DiceRoller
from core.events import signal_hub


class DiceRollerDialog(QDialog):
    """Dialog for rolling dice with quick buttons and history."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.roller = DiceRoller()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI components."""
        self.setWindowTitle("Dice Roller")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Input section
        input_group = QGroupBox("Roll Dice")
        input_layout = QVBoxLayout(input_group)
        
        # Expression input
        input_row = QHBoxLayout()
        self.expression_input = QLineEdit()
        self.expression_input.setPlaceholderText("e.g., 2d20+5, 2d20kh1 (advantage), 4d6kh3")
        self.expression_input.returnPressed.connect(self.roll_custom)
        input_row.addWidget(self.expression_input)
        
        roll_btn = QPushButton("Roll")
        roll_btn.clicked.connect(self.roll_custom)
        roll_btn.setDefault(True)
        input_row.addWidget(roll_btn)
        
        input_layout.addLayout(input_row)
        layout.addWidget(input_group)
        
        # Quick roll buttons
        quick_group = QGroupBox("Quick Rolls")
        quick_layout = QGridLayout(quick_group)
        
        quick_rolls = [
            ("d4", "1d4"),
            ("d6", "1d6"),
            ("d8", "1d8"),
            ("d10", "1d10"),
            ("d12", "1d12"),
            ("d20", "1d20"),
            ("d100", "1d100"),
            ("2d6", "2d6"),
            ("3d6", "3d6"),
            ("4d6 (drop low)", "ability"),
            ("Advantage", "adv"),
            ("Disadvantage", "dis"),
        ]
        
        row, col = 0, 0
        for label, expr in quick_rolls:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, e=expr: self.quick_roll(e))
            quick_layout.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1
        
        layout.addWidget(quick_group)
        
        # Results area
        results_label = QLabel("Roll History")
        results_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(results_label)
        
        self.results_area = QTextEdit()
        self.results_area.setReadOnly(True)
        self.results_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.results_area)
        
        # Clear button
        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self.clear_history)
        layout.addWidget(clear_btn)
        
        # Welcome message
        self.results_area.append("=== Dice Roller Ready ===")
        self.results_area.append("Enter a dice expression or use quick buttons.")
        self.results_area.append("Examples: 2d20+5, 2d20kh1 (advantage), 2d20kl1 (disadvantage), 4d6kh3\n")
        
    def roll_custom(self):
        """Roll dice based on custom expression."""
        expression = self.expression_input.text().strip()
        if not expression:
            return
        
        result = self.roller.roll(expression)
        if result:
            self.display_result(result)
            # Send to console
            signal_hub.console_output.emit(f"🎲 {result.expression} = {result.total} {result.details}")
        else:
            self.results_area.append(f"❌ Invalid expression: {expression}\n")
        
        self.expression_input.clear()
        
    def quick_roll(self, expression: str):
        """Handle quick roll buttons."""
        if expression == "ability":
            # Roll 4d6 drop lowest
            total, rolls = self.roller.roll_ability_score()
            rolls_str = ", ".join(map(str, rolls))
            kept_str = ", ".join(map(str, sorted(rolls)[1:]))
            self.results_area.append(f"🎲 4d6 (drop lowest)")
            self.results_area.append(f"   Rolls: [{rolls_str}]")
            self.results_area.append(f"   Kept: [{kept_str}]")
            self.results_area.append(f"   Total: {total}")
            self.results_area.append("")
            signal_hub.console_output.emit(f"🎲 4d6 drop lowest = {total} (rolls: {rolls_str})")
            
        elif expression == "adv":
            # Roll with advantage
            roll1, roll2, result = self.roller.roll_with_advantage()
            self.results_area.append(f"🎲 d20 with Advantage")
            self.results_area.append(f"   Roll 1: {roll1}")
            self.results_area.append(f"   Roll 2: {roll2}")
            self.results_area.append(f"   Result: {result} (higher)")
            self.results_area.append("")
            signal_hub.console_output.emit(f"🎲 d20 Advantage = {result} ({roll1}, {roll2})")
            
        elif expression == "dis":
            # Roll with disadvantage
            roll1, roll2, result = self.roller.roll_with_disadvantage()
            self.results_area.append(f"🎲 d20 with Disadvantage")
            self.results_area.append(f"   Roll 1: {roll1}")
            self.results_area.append(f"   Roll 2: {roll2}")
            self.results_area.append(f"   Result: {result} (lower)")
            self.results_area.append("")
            signal_hub.console_output.emit(f"🎲 d20 Disadvantage = {result} ({roll1}, {roll2})")
            
        else:
            # Regular roll
            result = self.roller.roll(expression)
            if result:
                self.display_result(result)
                signal_hub.console_output.emit(f"🎲 {result.expression} = {result.total} {result.details}")
                
    def display_result(self, result):
        """Display a roll result."""
        self.results_area.append(f"🎲 {result.expression}")
        self.results_area.append(f"   {result.details}")
        self.results_area.append(f"   Total: {result.total}")
        self.results_area.append("")
        
        # Scroll to bottom
        self.results_area.verticalScrollBar().setValue(
            self.results_area.verticalScrollBar().maximum()
        )
        
    def clear_history(self):
        """Clear the roll history."""
        self.results_area.clear()
        self.results_area.append("=== History Cleared ===\n")

