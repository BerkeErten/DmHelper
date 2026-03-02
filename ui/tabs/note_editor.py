"""Rich text note editor widget."""
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QToolBar, QFontComboBox, QSpinBox, QLabel, QCheckBox,
    QFileDialog, QMessageBox, QLineEdit, QPushButton, QSizePolicy,
    QToolButton, QGraphicsDropShadowEffect, QMenu, QWidgetAction,
)
from PyQt6.QtGui import QAction, QFont, QTextCharFormat, QColor, QTextCursor, QPainter, QPainterPath
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from pathlib import Path


class NoteEditor(QWidget):
    """Rich text editor for notes with formatting toolbar."""

    attach_clicked = pyqtSignal(str, object)  # (source_kind, source_id)

    def __init__(self, parent=None, note_id=None, note_title=None, parent_id=None):
        super().__init__(parent)
        self.note_id = note_id  # Database note ID
        self.note_title = note_title or "Untitled"
        self.parent_id = parent_id  # Parent note ID for subnotes
        self.tags = []  # List of tag names
        self.tag_colors = {}  # Dictionary: tag_name -> color
        self.file_path = None  # Local file path for text file save
        self.is_modified = False
        self.auto_save_enabled = True
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_delay = 2000  # 2 seconds after typing stops
        self.setup_ui()
        self.connect_signals()
        
        # Load note if ID is provided
        if self.note_id:
            self.load_note()
        
    def setup_ui(self):
        """Setup the UI components."""
        # Set size policy to expand in both directions
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Title area - editable label that becomes line edit on double-click
        title_container = QWidget()
        title_container.setStyleSheet("margin: 0px; padding: 0px; border: none; background-color: #2b2b2b;")
        # Set size policy to keep it at top - don't expand vertically
        title_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(8, 0, 8, 2)
        title_layout.setSpacing(0)
        
        self.title_label = QLabel(self.note_title)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 0px;")
        self.title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_label.installEventFilter(self)
        self.title_editing = False
        
        # Hidden line edit for editing title (overlays the label)
        self.title_line_edit = QLineEdit()
        self.title_line_edit.setStyleSheet("font-size: 18px; font-weight: bold; padding: 3px; border: 2px solid #0078d4;")
        self.title_line_edit.setVisible(False)
        self.title_line_edit.editingFinished.connect(self.finish_title_edit)
        self.title_line_edit.installEventFilter(self)
        
        # Add both widgets to the same layout position (they'll be shown/hidden)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.title_line_edit)
        # Set stretch to make both widgets take full width
        title_layout.setStretchFactor(self.title_label, 1)
        title_layout.setStretchFactor(self.title_line_edit, 1)
        
        # Add title container at top without stretch (fixed height)
        layout.addWidget(title_container, 0)  # stretch=0 means no vertical expansion
        
        # Tags section
        self.tags_container = QWidget()
        tags_layout = QHBoxLayout(self.tags_container)
        tags_layout.setContentsMargins(10, 5, 10, 5)
        tags_layout.setSpacing(8)
        
        tags_label = QLabel("Tags:")
        tags_label.setStyleSheet("font-size: 12px; color: #666666;")
        tags_layout.addWidget(tags_label)
        
        # Container for tag widgets
        self.tags_widget_container = QWidget()
        self.tags_widget_layout = QHBoxLayout(self.tags_widget_container)
        self.tags_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_widget_layout.setSpacing(6)
        
        tags_layout.addWidget(self.tags_widget_container)
        tags_layout.addStretch()
        
        layout.addWidget(self.tags_container)
        
        # Tag widgets dictionary: tag_name -> TagWidget
        self.tag_widgets = {}
        # Empty tag widget for adding new tags
        self.empty_tag_widget = None
        self._setup_tags_ui()
        
        # Formatting toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        
        # Font family
        self.font_combo = QFontComboBox()
        self.font_combo.setMaximumWidth(200)
        self.toolbar.addWidget(self.font_combo)
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setValue(11)
        self.font_size.setMinimum(6)
        self.font_size.setMaximum(72)
        self.font_size.setSuffix(" pt")
        self.toolbar.addWidget(self.font_size)
        
        self.toolbar.addSeparator()
        
        # Bold
        self.bold_action = QAction("B", self)
        self.bold_action.setCheckable(True)
        self.bold_action.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.bold_action.setToolTip("Bold (Ctrl+B)")
        self.toolbar.addAction(self.bold_action)
        
        # Italic
        self.italic_action = QAction("I", self)
        self.italic_action.setCheckable(True)
        font = QFont("Arial", 10)
        font.setItalic(True)
        self.italic_action.setFont(font)
        self.italic_action.setToolTip("Italic (Ctrl+I)")
        self.toolbar.addAction(self.italic_action)
        
        # Underline
        self.underline_action = QAction("U", self)
        self.underline_action.setCheckable(True)
        font = QFont("Arial", 10)
        font.setUnderline(True)
        self.underline_action.setFont(font)
        self.underline_action.setToolTip("Underline (Ctrl+U)")
        self.toolbar.addAction(self.underline_action)
        
        self.toolbar.addSeparator()
        
        # Align left
        self.align_left_action = QAction("≡", self)
        self.align_left_action.setCheckable(True)
        self.align_left_action.setToolTip("Align Left")
        self.toolbar.addAction(self.align_left_action)
        
        # Align center
        self.align_center_action = QAction("≡", self)
        self.align_center_action.setCheckable(True)
        self.align_center_action.setToolTip("Align Center")
        self.toolbar.addAction(self.align_center_action)
        
        # Align right
        self.align_right_action = QAction("≡", self)
        self.align_right_action.setCheckable(True)
        self.align_right_action.setToolTip("Align Right")
        self.toolbar.addAction(self.align_right_action)
        
        self.toolbar.addSeparator()
        
        # Bullet list
        self.bullet_action = QAction("• List", self)
        self.bullet_action.setToolTip("Bullet List")
        self.toolbar.addAction(self.bullet_action)
        
        # Numbered list
        self.number_action = QAction("1. List", self)
        self.number_action.setToolTip("Numbered List")
        self.toolbar.addAction(self.number_action)
        
        self.toolbar.addSeparator()
        
        # Save to file button
        self.save_file_action = QAction("📄 Save File", self)
        self.save_file_action.setToolTip("Save note to file (Markdown format)")
        self.toolbar.addAction(self.save_file_action)
        
        # Load from file button
        self.load_file_action = QAction("📂 Load File", self)
        self.load_file_action.setToolTip("Load note from file")
        self.toolbar.addAction(self.load_file_action)
        
        self.toolbar.addSeparator()
        
        # Save to database button
        self.save_db_action = QAction("💾 Save DB", self)
        self.save_db_action.setToolTip("Save note to database (Ctrl+S) - for syncing")
        self.toolbar.addAction(self.save_db_action)
        
        # Auto-save toggle
        self.auto_save_action = QAction("⚡ Auto", self)
        self.auto_save_action.setCheckable(True)
        self.auto_save_action.setChecked(True)
        self.auto_save_action.setToolTip("Auto-save enabled")
        self.toolbar.addAction(self.auto_save_action)
        # Spacer to push attach button to the right (same line, right-aligned)
        toolbar_spacer = QWidget()
        toolbar_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(toolbar_spacer)
        # Attach button (right-aligned on same line as auto-save) with button shadow
        self.attach_btn = QToolButton()
        self.attach_btn.setText("\U0001f4ce")
        self.attach_btn.setToolTip("Attach")
        self.attach_btn.setFixedSize(28, 28)
        self.attach_btn.setStyleSheet("""
            QToolButton {
                background-color: #3c3c3c;
                border: 1px solid #4c4c4c;
                border-radius: 4px;
                font-size: 16px;
            }
            QToolButton:hover { background-color: #4a4a4a; border-color: #5c5c5c; }
            QToolButton:pressed { background-color: #2e2e2e; border-color: #383838; }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(6)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.attach_btn.setGraphicsEffect(shadow)
        self.attach_btn.clicked.connect(self._on_attach_btn_clicked)
        self.toolbar.addWidget(self.attach_btn)
        
        layout.addWidget(self.toolbar)
        
        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Start typing your notes here...\n\n"
            "Use the toolbar above for formatting or use Markdown:\n"
            "  # Header 1, ## Header 2, ### Header 3\n"
            "  --- for horizontal rule\n"
            "  **bold**, *italic*, `code`\n"
            "  - Bullet list\n"
            "  1. Numbered list\n"
            "  > Blockquote\n\n"
            "You can drag and drop entities from the Data Manager!"
        )
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border-left: 1px solid #3c3c3c;
                border-right: 1px solid #3c3c3c;
                border-bottom: 1px solid #3c3c3c;
            }
        """)

        self.text_edit.setAcceptDrops(True)
        # Set size policy to expand and fill available space
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Set smaller tab stop distance (default is 80 pixels, we'll use 20)
        self.text_edit.setTabStopDistance(20)
        # Set document margin to reduce left indent for lists
        from PyQt6.QtGui import QTextDocument
        doc = self.text_edit.document()
        doc.setIndentWidth(20)  # Match tab stop distance
        # Add with stretch factor so it takes all available vertical space
        layout.addWidget(self.text_edit, stretch=1)
        
        # Install event filter to handle drops and key presses
        self.text_edit.installEventFilter(self)
        self.markdown_enabled = True  # Enable markdown by default
        
    def connect_signals(self):
        """Connect signals and slots."""
        # Font changes
        self.font_combo.currentFontChanged.connect(self.change_font_family)
        self.font_size.valueChanged.connect(self.change_font_size)
        
        # Text formatting
        self.bold_action.triggered.connect(self.toggle_bold)
        self.italic_action.triggered.connect(self.toggle_italic)
        self.underline_action.triggered.connect(self.toggle_underline)
        
        # Alignment
        self.align_left_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignLeft))
        self.align_center_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignCenter))
        self.align_right_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignRight))
        
        # Lists
        self.bullet_action.triggered.connect(self.insert_bullet_list)
        self.number_action.triggered.connect(self.insert_numbered_list)
        
        # Save actions
        self.save_file_action.triggered.connect(self.save_to_file)
        self.load_file_action.triggered.connect(self.load_from_file)
        self.save_db_action.triggered.connect(self.save_to_database)
        self.auto_save_action.triggered.connect(self.toggle_auto_save)
        
        # Track content changes for auto-save
        self.text_edit.textChanged.connect(self.on_content_changed)
        
        # Update toolbar state when cursor moves
        self.text_edit.cursorPositionChanged.connect(self.update_format_actions)
        
        # Keyboard shortcuts
        from PyQt6.QtGui import QKeySequence, QShortcut
        save_db_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_db_shortcut.activated.connect(self.save_to_database)
    
    def _on_add_relation_triggered(self):
        """Emit attach_clicked with context if note is saved; else prompt to save first."""
        if self.note_id is None:
            QMessageBox.information(
                self,
                "Save first",
                "Save the note first to add relations.",
            )
            return
        self.attach_clicked.emit("note", self.note_id)

    def _on_attach_btn_clicked(self):
        """Show popup menu with search bar and relation options list."""
        if self.note_id is None:
            QMessageBox.information(
                self,
                "Save first",
                "Save the note first to add relations.",
            )
            return
        from ui.dialogs.add_relation_dialog import AddRelationPopupWidget
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #e0e0e0;
                padding: 0;
                border: 1px solid #4c4c4c;
                border-radius: 4px;
            }
        """)
        content = AddRelationPopupWidget("note", self.note_id, menu)
        action = QWidgetAction(menu)
        action.setDefaultWidget(content)
        menu.addAction(action)
        content.closed_requested.connect(menu.close)
        menu.exec(self.attach_btn.mapToGlobal(self.attach_btn.rect().bottomLeft()))
        
    def change_font_family(self, font):
        """Change the font family."""
        fmt = QTextCharFormat()
        fmt.setFontFamily(font.family())
        self.merge_format(fmt)
        
    def change_font_size(self, size):
        """Change the font size."""
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self.merge_format(fmt)
        
    def toggle_bold(self):
        """Toggle bold formatting."""
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.bold_action.isChecked() else QFont.Weight.Normal)
        self.merge_format(fmt)
        
    def toggle_italic(self):
        """Toggle italic formatting."""
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_action.isChecked())
        self.merge_format(fmt)
        
    def toggle_underline(self):
        """Toggle underline formatting."""
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.underline_action.isChecked())
        self.merge_format(fmt)
        
    def set_alignment(self, alignment):
        """Set text alignment."""
        self.text_edit.setAlignment(alignment)
        
    def insert_bullet_list(self):
        """Insert a bullet list."""
        cursor = self.text_edit.textCursor()
        cursor.insertList(QTextCursor.ListStyle.ListDisc)
        
    def insert_numbered_list(self):
        """Insert a numbered list."""
        cursor = self.text_edit.textCursor()
        cursor.insertList(QTextCursor.ListStyle.ListDecimal)
        
    def merge_format(self, fmt):
        """Merge format into current selection."""
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.text_edit.mergeCurrentCharFormat(fmt)
        
    def update_format_actions(self):
        """Update toolbar actions based on current cursor format."""
        cursor = self.text_edit.textCursor()
        fmt = cursor.charFormat()
        
        # Update font combo and size
        font = fmt.font()
        self.font_combo.setCurrentFont(font)
        if fmt.fontPointSize() > 0:
            self.font_size.setValue(int(fmt.fontPointSize()))
        
        # Update formatting buttons
        self.bold_action.setChecked(font.weight() == QFont.Weight.Bold)
        self.italic_action.setChecked(font.italic())
        self.underline_action.setChecked(font.underline())
        
        # Update alignment buttons
        alignment = self.text_edit.alignment()
        self.align_left_action.setChecked(alignment == Qt.AlignmentFlag.AlignLeft)
        self.align_center_action.setChecked(alignment == Qt.AlignmentFlag.AlignCenter)
        self.align_right_action.setChecked(alignment == Qt.AlignmentFlag.AlignRight)
        
    def get_content(self):
        """Get the HTML content of the editor."""
        return self.text_edit.toHtml()
        
    def set_content(self, html_content):
        """Set the HTML content of the editor."""
        self.text_edit.setHtml(html_content)
        
    def get_plain_text(self):
        """Get the plain text content."""
        return self.text_edit.toPlainText()
        
    def toggle_markdown(self):
        """Toggle markdown support. (Function kept for compatibility, markdown is always enabled)"""
        # Markdown is always enabled, this function is kept for compatibility
        self.markdown_enabled = True
        
    def eventFilter(self, obj, event):
        """Handle drop events and key presses in the text editor, and title double-click."""
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QDropEvent, QKeyEvent, QMouseEvent
        
        # Handle title label double-click
        if obj == self.title_label and event.type() == QEvent.Type.MouseButtonDblClick:
            if not self.title_editing:
                self.start_title_edit()
            return True
        
        # Handle Escape key to cancel title editing
        if obj == self.title_line_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.cancel_title_edit()
                return True
        
        # Check if text_edit exists before accessing it (it's created after title_label)
        if hasattr(self, 'text_edit') and obj == self.text_edit:
            if event.type() == QEvent.Type.Drop:
                # Handle drop from Data Manager
                mime_data = event.mimeData()
                
                if mime_data.hasText():
                    # Insert the dropped text at cursor position
                    cursor = self.text_edit.cursorForPosition(event.position().toPoint())
                    self.text_edit.setTextCursor(cursor)
                    
                    # Format the dropped entity as a link-style reference
                    entity_name = mime_data.text()
                    cursor.insertHtml(f'<strong>[{entity_name}]</strong> ')
                    
                    event.acceptProposedAction()
                    return True
            
            elif event.type() == QEvent.Type.KeyPress and self.markdown_enabled:
                # Handle inline markdown conversion as you type
                cursor = self.text_edit.textCursor()
                
                # Check for Space or Enter to trigger markdown conversion
                if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Enter):
                    # Get current line text up to cursor (before space/enter is inserted)
                    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                    line = cursor.selectedText()
                    
                    # Check if line starts with markdown prefix (before space/enter)
                    # Headers: #, ##, ###, etc. (without space yet, or with trailing spaces)
                    header_match = re.match(r'^(#{1,6})\s*$', line)
                    if header_match:
                        # Just typed # and about to type space - convert to header format
                        level = len(header_match.group(1))
                        self._apply_header_format(cursor, level)
                        if event.key() == Qt.Key.Key_Space:
                            return True  # Consume space, format is applied
                    
                    # Bullet list: -, *, + (without space yet)
                    elif re.match(r'^[-*+]\s*$', line):
                        self._apply_list_format(cursor, 'bullet')
                        if event.key() == Qt.Key.Key_Space:
                            return True
                    
                    # Numbered list: 1., 2., etc. (without space yet)
                    elif re.match(r'^\d+\.\s*$', line):
                        self._apply_list_format(cursor, 'numbered')
                        if event.key() == Qt.Key.Key_Space:
                            return True
                    
                    # Blockquote: > (without space yet)
                    elif re.match(r'^>\s*$', line):
                        self._apply_blockquote_format(cursor)
                        if event.key() == Qt.Key.Key_Space:
                            return True
                    
                    # Full line processing for Enter key (complete markdown conversion)
                    if event.key() == Qt.Key.Key_Enter:
                        cursor = self.text_edit.textCursor()
                        # Check if we're currently in a list
                        current_list = cursor.currentList()
                        
                        # Check current format to detect header/blockquote styling
                        # Get format from the current character position
                        current_format = cursor.charFormat()
                        font_size = current_format.fontPointSize()
                        font_weight = current_format.fontWeight()
                        is_italic = current_format.fontItalic()
                        text_color = current_format.foreground().color()
                        
                        # Detect header: bold + larger font size (> 11pt)
                        is_header_format = (font_weight == QFont.Weight.Bold and font_size > 11)
                        # Detect blockquote: italic + gray color
                        is_blockquote_format = (is_italic and text_color.name().lower() in ("#888888", "#888"))
                        
                        from core.markdown_parser import MarkdownParser
                        markdown_processed = MarkdownParser.process_line(cursor, line)
                        
                        if markdown_processed:
                            return True  # Prevent default Enter behavior - markdown was processed
                        
                        # If not in a list but in header/blockquote format, reset formatting to normal
                        # Use a timer to reset after the new line is created by Enter
                        if not current_list and (is_header_format or is_blockquote_format):
                            from PyQt6.QtCore import QTimer
                            QTimer.singleShot(0, self._reset_to_normal_format)
                        
        return super().eventFilter(obj, event)
    
    def on_content_changed(self):
        """Handle content changes for auto-save."""
        self.is_modified = True
        if self.auto_save_enabled:
            # Restart auto-save timer
            self.auto_save_timer.stop()
            self.auto_save_timer.start(self.auto_save_delay)
    
    def toggle_auto_save(self, enabled: bool):
        """Toggle auto-save functionality."""
        self.auto_save_enabled = enabled
        status = "enabled" if enabled else "disabled"
        self.auto_save_action.setToolTip(f"Auto-save {status}")
        if not enabled:
            self.auto_save_timer.stop()
    
    def auto_save(self):
        """Auto-save note after delay."""
        if self.is_modified and self.auto_save_enabled:
            # Auto-save to both file and database
            if self.file_path:
                self.save_to_file(silent=True)
            self.save_to_database(show_message=False)
    
    def save_to_file(self, silent=False):
        """Save note to a text file (Markdown format)."""
        from core.config import DATA_DIR
        
        # Ensure data directory exists (check if it's a file first)
        if DATA_DIR.exists() and DATA_DIR.is_file():
            # If it's a file, we can't use it as a directory
            # Use parent directory instead
            save_dir = DATA_DIR.parent
        else:
            save_dir = DATA_DIR
            save_dir.mkdir(parents=True, exist_ok=True)
        
        # Get plain text (readable in any editor)
        plain_text = self.get_plain_text()
        
        # If we have a file path, use it; otherwise ask for location
        if not self.file_path or not silent:
            # Clean filename from title
            safe_title = "".join(c for c in self.note_title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Note to File",
                str(save_dir / f"{safe_title}.md"),
                "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)"
            )
            if not file_path:
                return
            self.file_path = Path(file_path)
        
        try:
            # Update note title from filename (without extension)
            file_stem = self.file_path.stem  # Gets filename without extension
            if file_stem and file_stem != self.note_title:
                self.note_title = file_stem
                self.title_label.setText(file_stem)
                # Update tab title
                from core.events import signal_hub
                signal_hub.note_saved.emit(self.note_id, file_stem)
            
            # Save as markdown (plain text with some formatting preserved)
            # We'll save the plain text which is readable in any editor
            with open(self.file_path, 'w', encoding='utf-8') as f:
                # Write title as first line
                f.write(f"# {self.note_title}\n\n")
                # Write content (plain text)
                f.write(plain_text)
            
            self.is_modified = False
            if not silent:
                QMessageBox.information(self, "Saved", f"Note saved to:\n{self.file_path}")
            else:
                self._show_save_status(f"Saved to {self.file_path.name}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving file:\n{str(e)}")
    
    def load_from_file(self):
        """Load note from a text file."""
        from core.config import DATA_DIR
        
        # Use parent directory if DATA_DIR is a file
        if DATA_DIR.exists() and DATA_DIR.is_file():
            load_dir = DATA_DIR.parent
        else:
            load_dir = DATA_DIR
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Note from File",
            str(load_dir),
            "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            file_path_obj = Path(file_path)
            # Use filename (without extension) as the note title
            title = file_path_obj.stem  # Gets filename without extension
            
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract content (skip first line if it's a markdown header, but use filename as title)
            lines = content.split('\n')
            content_start = 0
            
            # Skip first line if it's a markdown header (we'll use filename as title instead)
            if lines and lines[0].startswith('# '):
                content_start = 1
                # Skip empty line after title if present
                if len(lines) > 1 and not lines[1].strip():
                    content_start = 2
            
            # Convert markdown content to HTML
            remaining_content = '\n'.join(lines[content_start:])
            html_content = self._convert_markdown_to_html(remaining_content)
            # Set HTML content with proper document styling
            self.text_edit.setHtml(html_content)
            # Ensure default text color is set for dark theme
            default_format = QTextCharFormat()
            default_format.setForeground(QColor("#e0e0e0"))
            self.text_edit.setCurrentCharFormat(default_format)
            
            # Set note title from filename
            self.note_title = title
            self.title_label.setText(title)
            self.file_path = file_path_obj
            self.is_modified = False
            
            # Update tab title
            from core.events import signal_hub
            signal_hub.note_saved.emit(None, title)
            
            QMessageBox.information(self, "Loaded", f"Note loaded from:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading file:\n{str(e)}")
    
    def save_to_database(self, show_message=True):
        """Save note to database (for syncing across computers)."""
        from core.database import DatabaseManager
        from models.note import Note, Tag
        from datetime import datetime
        
        content = self.get_content()
        title = self.note_title
        parent_id = self.parent_id
        tags = self.tags or []
        
        try:
            with DatabaseManager() as db:
                if self.note_id:
                    # Update existing note
                    note = db.query(Note).filter(Note.id == self.note_id).first()
                    if note:
                        note.title = title
                        note.content = content
                        note.parent_id = parent_id
                        note.updated_at = datetime.utcnow()
                        
                        # Update tags
                        self._update_note_tags(db, note, tags)
                        
                        db.commit()
                        if show_message:
                            self._show_save_status("Note saved successfully")
                    else:
                        # Note not found, create new one
                        self._create_new_note(db, title, content, parent_id, tags, show_message)
                else:
                    # Create new note
                    self._create_new_note(db, title, content, parent_id, tags, show_message)
            
            self.is_modified = False
            
            # Emit signal to update tab title
            from core.events import signal_hub
            signal_hub.note_saved.emit(self.note_id, title)
            
        except Exception as e:
            self._show_save_status(f"Error saving note: {str(e)}", is_error=True)
    
    def _create_new_note(self, db, title: str, content: str, parent_id, tags, show_message: bool = True):
        """Create a new note in the database."""
        from models.note import Note, Tag
        from datetime import datetime
        
        note = Note(
            title=title,
            content=content,
            parent_id=parent_id,
            session_id=None,  # Can be set later
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add tags
        self._update_note_tags(db, note, tags)
        
        db.add(note)
        db.commit()
        db.refresh(note)
        self.note_id = note.id
        self.note_title = note.title
        self.parent_id = note.parent_id
        if show_message:
            self._show_save_status("Note created and saved successfully")
    
    def _update_note_tags(self, db, note, tag_names: list):
        """Update note tags - create tags if they don't exist, preserving colors."""
        from models.note import Tag
        
        # Clear existing tags
        note.tags.clear()
        
        # Add/update tags
        for tag_name in tag_names:
            if not tag_name:
                continue
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                # Create new tag with color
                tag_color = self.tag_colors.get(tag_name)
                tag = Tag(name=tag_name, color=tag_color)
                db.add(tag)
            else:
                # Update color if we have a new one
                if tag_name in self.tag_colors:
                    tag.color = self.tag_colors[tag_name]
            note.tags.append(tag)
    
    def load_note(self):
        """Load note from database."""
        if not self.note_id:
            return
        
        from core.database import DatabaseManager
        from sqlalchemy import text
        
        try:
            with DatabaseManager() as db:
                result = db.execute(text("""
                    SELECT title, content, parent_id 
                    FROM notes 
                    WHERE id = :id
                """), {'id': self.note_id})
                note_data = result.fetchone()
                
                if note_data:
                    title, content, parent_id = note_data
                    self.note_title = title
                    # Update title label display
                    self.title_label.setText(title)
                    self.parent_id = parent_id
                    
                    # Load tags separately with colors
                    tag_result = db.execute(text("""
                        SELECT t.name, t.color FROM tags t
                        INNER JOIN note_tags nt ON t.id = nt.tag_id
                        WHERE nt.note_id = :note_id
                    """), {'note_id': self.note_id})
                    tag_data = tag_result.fetchall()
                    self.tags = [row[0] for row in tag_data]
                    # Store colors (use existing color if tag doesn't have one)
                    self.tag_colors = {}
                    for row in tag_data:
                        tag_name = row[0]
                        tag_color = row[1]
                        if tag_color:
                            self.tag_colors[tag_name] = tag_color
                    # Update tags UI
                    self._refresh_tags_ui()
                    
                    if content:
                        self.set_content(content)
                    self.is_modified = False
        except Exception as e:
            self._show_save_status(f"Error loading note: {str(e)}", is_error=True)
            import traceback
            traceback.print_exc()
    
    def _show_save_status(self, message: str, is_error: bool = False):
        """Show save status message (placeholder for status bar)."""
        # This could be connected to a status bar in the future
        print(f"[{'ERROR' if is_error else 'INFO'}] {message}")
    
    def set_note_id(self, note_id: int):
        """Set the note ID and load it."""
        self.note_id = note_id
        if note_id:
            self.load_note()
    
    def get_note_id(self):
        """Get the current note ID."""
        return self.note_id
    
    def start_title_edit(self):
        """Start editing the title - replace label with line edit."""
        if self.title_editing:
            return
        
        self.title_editing = True
        self.title_line_edit.setText(self.note_title)
        self.title_line_edit.setVisible(True)
        self.title_label.setVisible(False)
        self.title_line_edit.setFocus()
        self.title_line_edit.selectAll()
    
    def cancel_title_edit(self):
        """Cancel editing the title without saving changes."""
        if not self.title_editing:
            return
        
        # Restore label visibility
        self.title_line_edit.setVisible(False)
        self.title_label.setVisible(True)
        self.title_editing = False
        self.title_label.setFocus()
    
    def finish_title_edit(self):
        """Finish editing the title - update and save."""
        if not self.title_editing:
            return
        
        new_title = self.title_line_edit.text().strip()
        
        # Restore label visibility
        self.title_line_edit.setVisible(False)
        self.title_label.setVisible(True)
        self.title_editing = False
        
        # Only update if title actually changed and is not empty
        if new_title and new_title != self.note_title:
            self.note_title = new_title
            self.title_label.setText(new_title)
            
            # Update in database
            self.update_note_title_in_db(new_title)
            
            # Emit signal to update tab title
            from core.events import signal_hub
            signal_hub.note_saved.emit(self.note_id, new_title)
        elif not new_title:
            # Empty title - restore original
            self.title_label.setText(self.note_title)
    
    def update_note_title_in_db(self, new_title: str):
        """Update the note title in the database."""
        if not self.note_id:
            return  # New note not yet saved
        
        try:
            from core.database import DatabaseManager
            from models.note import Note
            from sqlalchemy import text
            
            with DatabaseManager() as db:
                # Update title in database
                db.execute(
                    text("UPDATE notes SET title = :title, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
                    {"title": new_title, "id": self.note_id}
                )
                print(f"✓ Updated note title to '{new_title}' (ID: {self.note_id})")
        except Exception as e:
            print(f"Error updating note title: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def set_note_title(self, title: str):
        """Set the note title."""
        self.note_title = title
        if not self.title_editing:
            self.title_label.setText(title)
    
    def get_note_title(self):
        """Get the current note title."""
        return self.note_title
    
    def set_parent_id(self, parent_id: int):
        """Set the parent note ID."""
        self.parent_id = parent_id
    
    def get_parent_id(self):
        """Get the parent note ID."""
        return self.parent_id
    
    
    def _setup_tags_ui(self):
        """Set up the tags UI with empty tag widget."""
        from ui.tabs.tag_widget import EmptyTagWidget
        
        # Add empty tag widget for adding new tags
        self.empty_tag_widget = EmptyTagWidget()
        self.empty_tag_widget.tag_added.connect(self.add_tag)
        self.tags_widget_layout.addWidget(self.empty_tag_widget)
    
    def _refresh_tags_ui(self):
        """Refresh the tags UI with current tags."""
        # Remove empty tag widget temporarily
        if self.empty_tag_widget:
            self.tags_widget_layout.removeWidget(self.empty_tag_widget)
        
        # Clear existing tag widgets
        for tag_widget in list(self.tag_widgets.values()):
            self.tags_widget_layout.removeWidget(tag_widget)
            tag_widget.setParent(None)
            tag_widget.deleteLater()
        self.tag_widgets.clear()
        
        # Add tag widgets for each tag
        for tag_name in self.tags:
            tag_color = self.tag_colors.get(tag_name)
            self._add_tag_widget(tag_name, tag_color)
        
        # Add empty tag widget at the end
        if self.empty_tag_widget:
            self.tags_widget_layout.addWidget(self.empty_tag_widget)
    
    def _add_tag_widget(self, tag_name: str, tag_color: str = None):
        """Add a tag widget to the UI."""
        from ui.tabs.tag_widget import TagWidget
        
        if tag_name in self.tag_widgets:
            return  # Already exists
        
        tag_widget = TagWidget(tag_name, tag_color)
        tag_widget.tag_edited.connect(self.on_tag_edited)
        tag_widget.tag_deleted.connect(self.on_tag_deleted)
        
        # Store color if generated
        if not tag_color:
            tag_color = tag_widget.get_tag_color()
            self.tag_colors[tag_name] = tag_color
        
        # Insert before empty tag widget (or at end if no empty widget)
        if self.empty_tag_widget:
            insert_index = self.tags_widget_layout.indexOf(self.empty_tag_widget)
            if insert_index >= 0:
                self.tags_widget_layout.insertWidget(insert_index, tag_widget)
            else:
                self.tags_widget_layout.addWidget(tag_widget)
        else:
            self.tags_widget_layout.addWidget(tag_widget)
        
        self.tag_widgets[tag_name] = tag_widget
    
    def add_tag(self, tag_name: str):
        """Add a new tag."""
        tag_name = tag_name.strip()
        if not tag_name:
            return
        
        # Check if tag already exists
        if tag_name in self.tags:
            return
        
        self.tags.append(tag_name)
        self._add_tag_widget(tag_name)
        
        # Mark as modified
        self.is_modified = True
        
        # Auto-save if enabled
        if self.auto_save_enabled and self.note_id:
            self.save_to_database(show_message=False)
    
    def on_tag_edited(self, old_name: str, new_name: str):
        """Handle tag being edited."""
        if old_name in self.tags:
            index = self.tags.index(old_name)
            self.tags[index] = new_name
        
        # Update tag widget mapping
        if old_name in self.tag_widgets:
            widget = self.tag_widgets.pop(old_name)
            self.tag_widgets[new_name] = widget
            
            # Update color mapping
            if old_name in self.tag_colors:
                self.tag_colors[new_name] = self.tag_colors.pop(old_name)
            else:
                self.tag_colors[new_name] = widget.get_tag_color()
        
        # Mark as modified
        self.is_modified = True
        
        # Auto-save if enabled
        if self.auto_save_enabled and self.note_id:
            self.save_to_database(show_message=False)
    
    def on_tag_deleted(self, tag_name: str):
        """Handle tag being deleted."""
        if tag_name in self.tags:
            self.tags.remove(tag_name)
        
        if tag_name in self.tag_widgets:
            self.tag_widgets.pop(tag_name)
        
        if tag_name in self.tag_colors:
            self.tag_colors.pop(tag_name)
        
        # Mark as modified
        self.is_modified = True
        
        # Auto-save if enabled
        if self.auto_save_enabled and self.note_id:
            self.save_to_database(show_message=False)
    
    def set_tags(self, tags: list):
        """Set the note tags (list of tag names)."""
        self.tags = tags if tags else []
        self._refresh_tags_ui()
    
    def get_tags(self):
        """Get the note tags (list of tag names)."""
        return self.tags or []
    
    def has_unsaved_changes(self):
        """Check if there are unsaved changes."""
        return self.is_modified
    
    def _apply_header_format(self, cursor: QTextCursor, level: int):
        """Apply header format inline and continue typing in that style."""
        # Remove the markdown prefix (# symbols)
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()
        # Remove the # prefix (keep any text after)
        text_after_prefix = re.sub(r'^#{1,6}\s*', '', line_text)
        
        # Set header format based on level
        char_format = QTextCharFormat()
        sizes = {1: 24, 2: 20, 3: 18, 4: 16, 5: 14, 6: 12}
        char_format.setFontPointSize(sizes.get(level, 18))
        char_format.setFontWeight(QFont.Weight.Bold)
        char_format.setForeground(QColor("#e0e0e0"))
        
        # Replace the line with formatted text (add space if converting from prefix)
        cursor.removeSelectedText()
        cursor.setCharFormat(char_format)
        # Insert space first, then any existing text
        cursor.insertText(' ' + text_after_prefix)
        # Continue with header format for next characters
        self.text_edit.setCurrentCharFormat(char_format)
    
    def _apply_list_format(self, cursor: QTextCursor, list_type: str):
        """Apply list format inline and continue typing in that style."""
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()
        
        # Remove the list prefix
        if list_type == 'bullet':
            text_after_prefix = re.sub(r'^[-*+]\s*', '', line_text)
            list_style = QTextCursor.ListStyle.ListDisc
        else:  # numbered
            text_after_prefix = re.sub(r'^\d+\.\s*', '', line_text)
            list_style = QTextCursor.ListStyle.ListDecimal
        
        # Create list format
        from PyQt6.QtGui import QTextListFormat
        list_format = QTextListFormat()
        list_format.setStyle(list_style)
        list_format.setIndent(1)
        
        # Replace the line
        cursor.removeSelectedText()
        cursor.insertList(list_format)
        # Insert space first, then any existing text
        cursor.insertText(' ' + text_after_prefix)
        # Continue with list format
        char_format = QTextCharFormat()
        char_format.setForeground(QColor("#e0e0e0"))
        cursor.setCharFormat(char_format)
        self.text_edit.setCurrentCharFormat(char_format)
    
    def _apply_blockquote_format(self, cursor: QTextCursor):
        """Apply blockquote format inline and continue typing in that style."""
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()
        
        # Remove the > prefix
        text_after_prefix = re.sub(r'^>\s*', '', line_text)
        
        # Apply blockquote styling
        char_format = QTextCharFormat()
        char_format.setForeground(QColor("#888888"))
        font = char_format.font()
        font.setItalic(True)
        char_format.setFont(font)
        
        # Replace the line
        cursor.removeSelectedText()
        cursor.setCharFormat(char_format)
        # Insert space first, then any existing text
        cursor.insertText(' ' + text_after_prefix)
        # Continue with blockquote format
        self.text_edit.setCurrentCharFormat(char_format)
    
    def _reset_to_normal_format(self):
        """Reset text formatting to normal (default) style."""
        normal_format = QTextCharFormat()
        normal_format.setForeground(QColor("#e0e0e0"))
        normal_format.setFontWeight(QFont.Weight.Normal)
        normal_format.setFontItalic(False)
        normal_format.setFontPointSize(11)  # Default font size
        self.text_edit.setCurrentCharFormat(normal_format)
    
    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown text to HTML with proper styling for dark theme."""
        from core.markdown_parser import MarkdownParser
        
        if not markdown_text.strip():
            return ""
        
        lines = markdown_text.split('\n')
        html_lines = []
        in_list = False
        list_type = None
        
        for line in lines:
            stripped = line.strip()
            
            # Horizontal rule
            if re.match(r'^(-{3,}|_{3,}|\*{3,})$', stripped):
                if in_list:
                    html_lines.append('</ul>' if list_type == 'bullet' else '</ol>')
                    in_list = False
                html_lines.append('<hr style="border-color: #3c3c3c; margin: 10px 0;">')
                continue
            
            # Headers (check original line to preserve indentation context)
            header_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if header_match:
                if in_list:
                    html_lines.append('</ul>' if list_type == 'bullet' else '</ol>')
                    in_list = False
                level = len(header_match.group(1))
                text = header_match.group(2)
                # Process inline markdown in header
                text = MarkdownParser.convert_inline_markdown(text)
                # Add dark theme styling for headers
                sizes = {1: '24px', 2: '20px', 3: '18px', 4: '16px', 5: '14px', 6: '12px'}
                size = sizes.get(level, '18px')
                html_lines.append(f'<h{level} style="color: #e0e0e0; font-size: {size}; font-weight: bold; margin: 12px 0 8px 0;">{text}</h{level}>')
                continue
            
            # Bullet list (check original line to handle indentation)
            bullet_match = re.match(r'^(\s*)[-*+]\s+(.+)$', line)
            if bullet_match:
                if not in_list or list_type != 'bullet':
                    if in_list:
                        html_lines.append('</ol>')
                    html_lines.append('<ul style="color: #e0e0e0; margin: 8px 0; padding-left: 20px;">')
                    in_list = True
                    list_type = 'bullet'
                text = bullet_match.group(2)
                text = MarkdownParser.convert_inline_markdown(text)
                html_lines.append(f'<li style="color: #e0e0e0; margin: 4px 0;">{text}</li>')
                continue
            
            # Numbered list (check original line to handle indentation)
            numbered_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
            if numbered_match:
                if not in_list or list_type != 'numbered':
                    if in_list:
                        html_lines.append('</ul>')
                    html_lines.append('<ol style="color: #e0e0e0; margin: 8px 0; padding-left: 20px;">')
                    in_list = True
                    list_type = 'numbered'
                text = numbered_match.group(2)
                text = MarkdownParser.convert_inline_markdown(text)
                html_lines.append(f'<li style="color: #e0e0e0; margin: 4px 0;">{text}</li>')
                continue
            
            # Blockquote
            if line.startswith('> '):
                if in_list:
                    html_lines.append('</ul>' if list_type == 'bullet' else '</ol>')
                    in_list = False
                text = line[2:]
                text = MarkdownParser.convert_inline_markdown(text)
                html_lines.append(f'<blockquote style="border-left: 4px solid #4CAF50; padding-left: 15px; margin-left: 5px; background-color: rgba(76, 175, 80, 0.1); font-style: italic; color: #888; margin: 8px 0;">{text}</blockquote>')
                continue
            
            # Regular paragraph
            if in_list:
                html_lines.append('</ul>' if list_type == 'bullet' else '</ol>')
                in_list = False
            
            if stripped:
                # Process inline markdown
                text = MarkdownParser.convert_inline_markdown(stripped)
                html_lines.append(f'<p style="color: #e0e0e0; margin: 6px 0;">{text}</p>')
            else:
                # Empty line
                html_lines.append('<p style="margin: 4px 0;"><br></p>')
        
        # Close any open list
        if in_list:
            html_lines.append('</ul>' if list_type == 'bullet' else '</ol>')
        
        # Wrap in a styled div for dark theme
        body_content = '\n'.join(html_lines)
        # Update inline code styling for dark theme
        body_content = body_content.replace(
            'style="background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px;"',
            'style="background-color: #3c3c3c; color: #66BB6A; padding: 2px 4px; border-radius: 3px; font-family: monospace;"'
        )
        
        return f'<div style="color: #e0e0e0; background-color: #1e1e1e;">{body_content}</div>'

