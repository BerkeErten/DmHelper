"""Console widget for command input and output."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QTextCursor, QColor, QPalette, QCursor
from core.events import signal_hub


class ConsoleWidget(QWidget):
    """Console for command input and output."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.command_history = []
        self.history_index = -1
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        

        
        # Container for buttons with no spacing after header
        buttons_container = QWidget()
        buttons_container_layout = QVBoxLayout(buttons_container)
        buttons_container_layout.setContentsMargins(0, -5, 0, 0)  # Negative top margin to remove gap (will expand when labels appear)
        buttons_container_layout.setSpacing(0)
        # Store references for dynamic spacing updates
        self.buttons_container = buttons_container
        self.buttons_container_layout = buttons_container_layout
        
        # Buttons row (fixed position)
        dice_buttons_layout = QHBoxLayout()
        dice_buttons_layout.setSpacing(5)
        dice_buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        # Quick dice buttons (d4, d6, d8, d10, d12, d20, d100)
        self.dice_buttons = {}
        self.dice_labels = {}
        dice_types = ["d4", "d6", "d8", "d10", "d12", "d20", "d100"]
        
        for dice_type in dice_types:
            # Create container widget for button (fixed size, never changes)
            button_container = QWidget()
            button_container.setFixedSize(60, 28)  # Fixed at button height - never changes
            
            # Create button at top of container (fixed position, never moves)
            btn = QPushButton(dice_type)
            btn.setParent(button_container)
            btn.setFixedWidth(60)
            btn.setFixedHeight(28)
            btn.move(0, 0)  # Fixed position - never moves
            btn.setToolTip(f"Add {dice_type} to input")
            btn.clicked.connect(lambda checked, dt=dice_type: self.add_dice_to_input(dt))
            self.dice_buttons[dice_type] = btn
            
            # Create label that will appear above button (parented to buttons_container to allow overflow)
            label = QLabel("", buttons_container)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    font-weight: bold;
                    color: #66BB6A;
                    background-color: rgba(76, 175, 80, 0.15);
                    border: 1px solid rgba(76, 175, 80, 0.4);
                    border-radius: 3px;
                    min-height: 16px;
                    max-height: 16px;
                    min-width: 18px;
                    padding: 1px 1px;
                    margin: 0px;
                }
                QLabel:hover {
                    background-color: rgba(76, 175, 80, 0.25);
                }
            """)
            label.setFixedSize(32, 32)  # Match the CSS min-width and min-height
            label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))  # Set pointer cursor
            label.hide()  # Hide by default, will show when dice are added
            # Store button_container reference for positioning
            label.setProperty("button_container", button_container)
            # Store dice_type in label property for click handler
            label.setProperty("dice_type", dice_type)
            # Connect click handler
            label.mousePressEvent = lambda event, dt=dice_type: self._on_label_clicked(event, dt)
            self.dice_labels[dice_type] = label
            
            dice_buttons_layout.addWidget(button_container)
        
        # Add modifier buttons (in containers to match dice button height/position)
        dice_buttons_layout.addSpacing(10)
        
        # Minus button container (starts small, will expand when labels appear)
        minus_container = QWidget()
        minus_container.setFixedSize(40, 28)  # Start at button height
        minus_btn = QPushButton("-", minus_container)
        minus_btn.setFixedWidth(40)
        minus_btn.setFixedHeight(28)
        minus_btn.move(0, 0)  # Fixed position - never moves
        minus_btn.setToolTip("Add negative modifier")
        minus_btn.clicked.connect(lambda: self.add_modifier("-"))
        dice_buttons_layout.addWidget(minus_container)
        self.minus_container = minus_container
        self.minus_btn = minus_btn
        
        # Plus button container (starts small, will expand when labels appear)
        plus_container = QWidget()
        plus_container.setFixedSize(40, 28)  # Start at button height
        plus_btn = QPushButton("+", plus_container)
        plus_btn.setFixedWidth(40)
        plus_btn.setFixedHeight(28)
        plus_btn.move(0, 0)  # Fixed position - never moves
        plus_btn.setToolTip("Add positive modifier")
        plus_btn.clicked.connect(lambda: self.add_modifier("+"))
        dice_buttons_layout.addWidget(plus_container)
        self.plus_container = plus_container
        self.plus_btn = plus_btn
        
        # Custom modifier input (starts small, will expand when labels appear)
        modifier_container = QWidget()
        modifier_container.setFixedSize(60, 28)  # Start at button height
        self.modifier_input = QLineEdit(modifier_container)
        self.modifier_input.setPlaceholderText("Mod")
        self.modifier_input.setFixedWidth(60)
        self.modifier_input.setFixedHeight(28)
        self.modifier_input.move(0, 0)  # Fixed position - never moves
        self.modifier_input.setToolTip("Enter custom modifier and press +/- button")
        dice_buttons_layout.addWidget(modifier_container)
        self.modifier_container = modifier_container
        
        dice_buttons_layout.addStretch()
        buttons_container_layout.addLayout(dice_buttons_layout)
        layout.addWidget(buttons_container)
        
        # Note: Labels will appear above buttons using absolute positioning, buttons never move
        
        # Output area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setPlaceholderText("Console output will appear here...")
        layout.addWidget(self.output_area)
        
        # Input line
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Enter command... (e.g., 'roll 2d20', 'help')")
        layout.addWidget(self.input_line)
        
        # Set minimum height
        self.setMinimumHeight(150)
        
        # Initial welcome message
        self.write_output("=== DM Helper Console ===")
        self.write_output("Type 'help' for available commands.")
        self.write_output("Quick start: /r 2d20+5, /r 2d20kh1 (advantage), /r 2d20kl1 (disadvantage)\n")
        
    def connect_signals(self):
        """Connect signals and slots."""
        self.input_line.returnPressed.connect(self.on_command_entered)
        self.input_line.textChanged.connect(self._on_input_changed)
        signal_hub.console_output.connect(self.write_output)

    def _on_input_changed(self):
        self.update_dice_labels()
        # Adjust spacing if input is empty
        if not self.input_line.text().strip():
            self.update_container_spacing()
        
    def add_dice_to_input(self, dice_type: str):
        """Add dice notation to the input line, combining all instances of same type. Add new dice on the left."""
        import re
        current_text = self.input_line.text().strip()
        
        # If input is empty, start with /r prefix
        if not current_text:
            self.input_line.setText(f"/r {dice_type}")
        else:
            # Check if we need to add /r prefix
            if not current_text.startswith("/r"):
                current_text = f"/r {current_text}"
            
            # Extract modifier if present (on the right side)
            modifier_match = re.search(r'\s*\[([+-]?\d+)\]$', current_text)
            modifier_str = ""
            dice_text = current_text
            
            if modifier_match:
                # Remove modifier temporarily to work with dice
                modifier_str = modifier_match.group(0)  # Keep the [±N] part
                dice_text = current_text[:-len(modifier_str)].strip()
            
            # Extract dice expressions (everything after /r)
            if dice_text.startswith("/r"):
                dice_part = dice_text[2:].strip()
            else:
                dice_part = dice_text
            
            # Split dice part by + to get individual dice expressions
            dice_expressions = [p.strip() for p in dice_part.split("+")] if dice_part else []
            
            # Find all instances of this dice type and combine them
            total_count = 0
            first_match_index = None
            dice_pattern = re.compile(r'^(\d*)' + re.escape(dice_type) + r'$')
            
            # Find all matches and their positions
            for i, expr in enumerate(dice_expressions):
                match = dice_pattern.match(expr)
                if match:
                    # This is the same dice type
                    count_str = match.group(1)
                    count = int(count_str) if count_str else 1
                    total_count += count
                    if first_match_index is None:
                        first_match_index = i  # Remember position of first occurrence
            
            # Add 1 for the new dice being added
            total_count += 1
            
            # Create the combined dice expression
            if total_count == 1:
                combined_dice_expr = dice_type
            else:
                combined_dice_expr = f"{total_count}{dice_type}"
            
            # Build the final expression: update where it is, remove duplicates
            if first_match_index is not None:
                # Update the existing dice where it is, remove other instances
                new_expressions = []
                for i, expr in enumerate(dice_expressions):
                    match = dice_pattern.match(expr)
                    if match:
                        # Only keep the first occurrence (updated)
                        if i == first_match_index:
                            new_expressions.append(combined_dice_expr)
                        # Skip other instances
                    else:
                        # Keep other dice types
                        new_expressions.append(expr)
                final_dice = " + ".join(new_expressions)
            else:
                # Dice type doesn't exist yet, add it on the left
                if dice_expressions:
                    final_dice = f"{dice_type} + {' + '.join(dice_expressions)}"
                else:
                    final_dice = dice_type
            
            self.input_line.setText(f"/r {final_dice}{modifier_str}")
        
        # Update all dice labels to reflect current counts
        self.update_dice_labels()
        
        # Focus back on input line
        self.input_line.setFocus()
        # Move cursor to end
        self.input_line.setCursorPosition(len(self.input_line.text()))
    
    def _on_label_clicked(self, event, dice_type: str):
        """Handle label click event to subtract dice."""
        self.subtract_dice_from_input(dice_type)
        self.update_container_spacing()
        # Call the base mousePressEvent to maintain normal behavior
        event.accept()
    def subtract_dice_from_input(self, dice_type: str):
        """Subtract one dice of the specified type from the input line."""
        import re
        current_text = self.input_line.text().strip()
        
        # If no input or doesn't start with /r, nothing to subtract
        if not current_text or not current_text.startswith("/r"):
            return
        
        # Extract modifier if present (on the right side)
        modifier_match = re.search(r'\s*\[([+-]?\d+)\]$', current_text)
        modifier_str = ""
        dice_text = current_text
        
        if modifier_match:
            # Remove modifier temporarily to work with dice
            modifier_str = modifier_match.group(0)  # Keep the [±N] part
            dice_text = current_text[:-len(modifier_str)].strip()
        
        # Extract dice expressions (everything after /r)
        dice_part = dice_text[2:].strip() if dice_text.startswith("/r") else dice_text
        
        if not dice_part:
            # No dice expressions, nothing to subtract
            return
        
        # Split dice part by + to get individual dice expressions
        dice_expressions = [p.strip() for p in dice_part.split("+")]
        
        # Find all instances of this dice type and combine them
        total_count = 0
        first_match_index = None
        dice_pattern = re.compile(r'^(\d*)' + re.escape(dice_type) + r'$')
        
        # Find all matches and their positions
        for i, expr in enumerate(dice_expressions):
            match = dice_pattern.match(expr)
            if match:
                # This is the same dice type
                count_str = match.group(1)
                count = int(count_str) if count_str else 1
                total_count += count
                if first_match_index is None:
                    first_match_index = i  # Remember position of first occurrence
        
        if total_count == 0:
            # No dice of this type to subtract
            return
        
        # Subtract 1 from the count
        total_count -= 1
        
        # Build the final expression
        if total_count == 0:
            # Remove this dice type completely
            new_expressions = []
            for i, expr in enumerate(dice_expressions):
                match = dice_pattern.match(expr)
                if not match:
                    # Keep other dice types
                    new_expressions.append(expr)
            
            if not new_expressions:
                # No dice left, clear input (but keep /r)
                final_dice = ""
            else:
                final_dice = " + ".join(new_expressions)
        else:
            # Update the count
            if total_count == 1:
                combined_dice_expr = dice_type
            else:
                combined_dice_expr = f"{total_count}{dice_type}"
            
            # Update the existing dice where it is, remove other instances
            new_expressions = []
            for i, expr in enumerate(dice_expressions):
                match = dice_pattern.match(expr)
                if match:
                    # Only keep the first occurrence (updated)
                    if i == first_match_index:
                        new_expressions.append(combined_dice_expr)
                    # Skip other instances
                else:
                    # Keep other dice types
                    new_expressions.append(expr)
            final_dice = " + ".join(new_expressions)
        
        # Update the input line
        if final_dice:
            self.input_line.setText(f"/r {final_dice}{modifier_str}")
        else:
            self.input_line.setText(f"/r {modifier_str}".strip())
        
        # Update all dice labels to reflect current counts
        self.update_dice_labels()
        
        # Focus back on input line
        self.input_line.setFocus()
        self.input_line.setCursorPosition(len(self.input_line.text()))
    
    def update_dice_labels(self):
        """Update all dice labels to show current counts from input."""
        import re
        current_text = self.input_line.text().strip()
        
        # Extract dice part (remove /r and modifier)
        if not current_text.startswith("/r"):
            # No dice in input, hide all labels
            for label in self.dice_labels.values():
                label.setText("")
                label.hide()
            return
        
        dice_text = current_text[2:].strip()  # Remove "/r "
        
        # Remove modifier if present
        modifier_match = re.search(r'\s*\[([+-]?\d+)\]$', dice_text)
        if modifier_match:
            dice_text = dice_text[:-len(modifier_match.group(0))].strip()
        
        if not dice_text:
            # No dice expressions, hide all labels
            for label in self.dice_labels.values():
                label.setText("")
                label.hide()
            return
        
        # Parse all dice expressions
        dice_expressions = [p.strip() for p in dice_text.split("+")]
        
        # Count each dice type
        dice_counts = {}
        for dice_type in self.dice_labels.keys():
            dice_pattern = re.compile(r'^(\d*)' + re.escape(dice_type) + r'$')
            total_count = 0
            
            for expr in dice_expressions:
                match = dice_pattern.match(expr)
                if match:
                    count_str = match.group(1)
                    count = int(count_str) if count_str else 1
                    total_count += count
            
            # Update label - show if count > 0, hide otherwise
            label = self.dice_labels[dice_type]
            button_container = label.property("button_container")
            button = self.dice_buttons.get(dice_type)
            
            if total_count > 0:
                label.setText(str(total_count))
                label.show()
            else:
                label.setText("")
                label.hide()
        
        # Update spacing ONCE after all labels are shown/hidden
        self.update_container_spacing()
        
        # Update ALL visible label positions AFTER spacing is stable
        # Use QTimer to defer position update until after layout has processed
        QTimer.singleShot(0, self._update_all_label_positions)
    
    def _update_all_label_positions(self):
        """Update positions of all visible labels. Called after layout updates."""
        for dice_type in self.dice_labels.keys():
            label = self.dice_labels[dice_type]
            if label.isVisible():
                self.update_label_position(dice_type)
    
    def update_label_position(self, dice_type: str):
        """Update label position to be above its button using absolute positioning."""
        label = self.dice_labels.get(dice_type)
        button_container = label.property("button_container") if label else None
        
        if label and button_container and label.isVisible():
            # Get button_container's position relative to buttons_container
            button_pos = button_container.pos()
            # Position label centered above button (x: button x + 14px to center, y: 14px above button top)
            label.move(button_pos.x() + 14, button_pos.y() - 16)
    
    def update_container_spacing(self):
        """Update top margin of buttons_container when labels appear/disappear."""
        # Check if any labels are visible
        any_labels_visible = any(lbl.isVisible() for lbl in self.dice_labels.values())
        
        if any_labels_visible:
            # Increase top margin to create more space above buttons when labels are visible
            self.buttons_container_layout.setContentsMargins(0, 16, 0, 0)  # Larger space above
        else:
            # Reduce top margin when no labels are visible
            self.buttons_container_layout.setContentsMargins(0, 0, 0, 0)  # Original spacing
        
    def add_modifier(self, operator: str):
        """Add/subtract modifier in the input text area (always on the right after dice)."""
        # Get custom modifier value
        mod_value = self.modifier_input.text().strip()
        
        if not mod_value:
            # Default to 1 if no custom value
            mod_value = "1"
        
        try:
            modifier = int(mod_value)
            if operator == "-":
                modifier = -modifier
            
            # Get current input text
            current_text = self.input_line.text().strip()
            
            # Ensure /r prefix if empty
            if not current_text:
                current_text = "/r "
            
            import re
            
            # Extract current modifier from text (look for [±N] pattern at the end)
            mod_match = re.search(r'\[([+-]?\d+)\]$', current_text)
            
            if mod_match:
                # Already has modifier on the right, add to it
                current_mod = int(mod_match.group(1))
                new_mod = current_mod + modifier
                
                # Replace old modifier with new one (keep it on the right)
                new_text = re.sub(r'\s*\[([+-]?\d+)\]$', f' [{new_mod:+d}]', current_text)
                self.input_line.setText(new_text)
            else:
                # No modifier yet, add it at the end (on the right)
                mod_str = f" [{modifier:+d}]"
                self.input_line.setText(current_text + mod_str)
            
            # Clear modifier input
            self.modifier_input.clear()
            
            # Focus back on input line
            self.input_line.setFocus()
            # Move cursor to end
            self.input_line.setCursorPosition(len(self.input_line.text()))
        except ValueError:
            self.write_output(f"❌ Invalid modifier value: {mod_value}", color="#FF5252")
            self.modifier_input.clear()
        
    def on_command_entered(self):
        """Handle command entered."""
        command = self.input_line.text().strip()
        
        if command:
            # Add to history
            self.command_history.append(command)
            self.history_index = len(self.command_history)
            
            # Display command
            self.write_output(f"> {command}", color="#4CAF50")
            
            # Clear input
            self.input_line.clear()
            
            # Emit signal for processing
            signal_hub.console_command.emit(command)
            
            # Simple echo response (placeholder)
            self.process_command(command)
            self.update_container_spacing()
            
    def process_command(self, command: str):
        """Process command (placeholder implementation)."""
        from core.dice_roller import DiceRoller
        
        cmd_lower = command.lower().strip()
        
        if cmd_lower == "help":
            self.write_output("Available commands:")
            self.write_output("  help - Show this help message")
            self.write_output("  clear - Clear console output")
            self.write_output("  /r XdY+Z - Roll dice (e.g., /r 2d20+5)")
            self.write_output("  /r XdYkhN - Keep highest N (e.g., /r 2d20kh1 for advantage)")
            self.write_output("  /r XdYklN - Keep lowest N (e.g., /r 2d20kl1 for disadvantage)")
            self.write_output("  adv - Quick roll d20 with advantage")
            self.write_output("  dis - Quick roll d20 with disadvantage")
            self.write_output("  stat - Roll 4d6 drop lowest for ability score")
            self.write_output("")
        elif cmd_lower == "clear":
            self.output_area.clear()
        elif cmd_lower.startswith("/r"):
            # Extract dice expression (handle both "/r 2d20" and "/r2d20")
            if cmd_lower.startswith("/r "):
                expr = command[3:].strip()
            else:
                expr = command[2:].strip()
            # 
            # Handle multiple dice expressions (stacked)
            self.roll_dice_expressions(expr)
        elif cmd_lower.startswith("roll "):
            # Keep backward compatibility with "roll" command
            expr = command[5:].strip()
            roller = DiceRoller()
            result = roller.roll(expr)
            if result:
                self.write_output(f"🎲 {result.expression}", color="#4CAF50")
                self.write_output(f"   {result.details}")
                self.write_output(f"   Total: {result.total}", color="#4CAF50")
                self.write_output("")
            else:
                self.write_output(f"Invalid dice expression: {expr}", color="#FF5252")
                self.write_output("Examples: roll 1d20, roll 2d6+3\n")
        elif cmd_lower == "adv":
            # Use the new kh syntax
            roller = DiceRoller()
            result = roller.roll("2d20kh1")
            if result:
                self.write_output("🎲 d20 with Advantage (2d20kh1)", color="#4CAF50")
                self.write_output(f"   {result.details}")
                self.write_output(f"   Result: {result.total}", color="#4CAF50")
                self.write_output("")
        elif cmd_lower == "dis":
            # Use the new kl syntax
            roller = DiceRoller()
            result = roller.roll("2d20kl1")
            if result:
                self.write_output("🎲 d20 with Disadvantage (2d20kl1)", color="#FF9800")
                self.write_output(f"   {result.details}")
                self.write_output(f"   Result: {result.total}", color="#FF9800")
                self.write_output("")
        elif cmd_lower == "stat":
            # Use the new kh syntax for ability scores
            roller = DiceRoller()
            result = roller.roll("4d6kh3")
            if result:
                self.write_output("🎲 Ability Score (4d6kh3)", color="#4CAF50")
                self.write_output(f"   {result.details}")
                self.write_output(f"   Total: {result.total}", color="#4CAF50")
                self.write_output("")
        else:
            # Check if it's a dice expression (starts with d or number)
            # Try to roll it as dice expressions
            roller = DiceRoller()
            expr_list = command.split()
            is_dice = False
            
            for expr in expr_list:
                # Check if expression looks like dice notation
                if any(expr.lower().startswith(prefix) for prefix in ['d', '1d', '2d', '3d', '4d', '5d', '6d', '7d', '8d', '9d']) or \
                   any(char in expr.lower() for char in ['d', 'kh', 'kl']):
                    is_dice = True
                    break
            
            if is_dice:
                # Treat as dice expression(s)
                self.roll_dice_expressions(command)
            else:
                self.write_output(f"Unknown command: {command}", color="#FF5252")
                self.write_output("Type 'help' for available commands or use dice buttons above.\n")
            
    def roll_dice_expressions(self, expressions: str):
        """Roll one or more dice expressions, apply modifiers to total."""
        from core.dice_roller import DiceRoller
        import re
        roller = DiceRoller()
        
        # Extract modifier from text (look for [±N] at the end, on the right)
        modifier = 0
        mod_match = re.search(r'\[([+-]?\d+)\]$', expressions)
        if mod_match:
            modifier = int(mod_match.group(1))
            # Remove modifier from expressions string (keep it on the right but extract it)
            expressions = re.sub(r'\s*\[([+-]?\d+)\]$', '', expressions).strip()
        
        # Remove /r prefix if present
        if expressions.startswith("/r"):
            expressions = expressions[2:].strip()
        
        # Split by + to handle multiple dice expressions
        parts = re.split(r'\s*\+\s*', expressions)
        valid_results = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Skip pure numbers (these would be modifiers, but we handle them separately)
            if re.match(r'^-?\d+$', part):
                continue
            
            # It's a dice expression
            result = roller.roll(part)
            if result:
                valid_results.append(result)
                self.write_output(f"🎲 {result.expression}", color="#4CAF50")
                self.write_output(f"   {result.details}")
                self.write_output(f"   Total: {result.total}", color="#4CAF50")
            else:
                self.write_output(f"❌ Invalid: {part}", color="#FF5252")
        
        if valid_results:
            # Calculate total with modifier applied
            dice_total = sum(r.total for r in valid_results)
            final_total = dice_total + modifier
            
            expressions_str = " + ".join(r.expression for r in valid_results)
            
            if modifier != 0:
                mod_str = f"{modifier:+d}"
                if len(valid_results) > 1:
                    # Multiple dice with modifier
                    self.write_output(f"📊 Dice Total: {expressions_str} = {dice_total}", color="#4CAF50")
                    self.write_output(f"📊 Final Total: {dice_total} {mod_str} = {final_total}", color="#4CAF50")
                else:
                    # Single dice with modifier
                    self.write_output(f"📊 Final Total: {dice_total} {mod_str} = {final_total}", color="#4CAF50")
            else:
                # No modifier
                if len(valid_results) > 1:
                    self.write_output(f"📊 Total: {expressions_str} = {final_total}", color="#4CAF50")
                else:
                    self.write_output(f"📊 Total: {final_total}", color="#4CAF50")
            
            self.write_output("")
        elif modifier != 0 and not valid_results:
            # Only modifiers, no dice
            self.write_output(f"⚠️ Modifier only: {modifier:+d} (no dice to apply to)", color="#FFA726")
            self.write_output("")
        elif not valid_results:
            self.write_output(f"Invalid dice expressions. Examples: d20, 2d6+3, 2d20kh1\n", color="#FF5252")
            
    def write_output(self, text: str, color: str = None):
        """Write text to output area."""
        from PyQt6.QtGui import QColor
        
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if color:
            self.output_area.setTextColor(QColor(color))
        
        self.output_area.append(text)
        
        # Reset color
        if color:
            self.output_area.setTextColor(QColor("#e0e0e0"))
            
        # Scroll to bottom
        self.output_area.verticalScrollBar().setValue(
            self.output_area.verticalScrollBar().maximum()
        )

