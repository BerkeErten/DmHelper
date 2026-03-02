"""Tab manager for handling multiple note tabs."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTextEdit, QPushButton, QLabel, QStackedWidget, QSizePolicy
from PyQt6.QtCore import Qt
from core.events import signal_hub


class TabManagerWidget(QWidget):
    """Tab manager for multiple note tabs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        # Don't load notes on startup - just show welcome screen
        # self.load_existing_notes()
        
    def setup_ui(self):
        """Setup the UI components."""
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # Tab widget (shown when notes exist) - tab bar will be extracted
            self.tab_widget = QTabWidget()
            self.tab_widget.setTabsClosable(True)
            self.tab_widget.setMovable(True)
            self.tab_widget.setDocumentMode(True)
            self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            # Hide the tab bar (we show it separately in main_window)
            self.tab_widget.tabBar().setFixedHeight(0)
            self.tab_widget.tabBar().setStyleSheet("height: 0px; margin: 0px; padding: 0px; border: 0px;")

            from ui.themes.tab_styles import TAB_WIDGET_STYLESHEET
            self.tab_widget.setStyleSheet(TAB_WIDGET_STYLESHEET)
            
            # Stacked widget to switch between welcome background and tabs
            self.stacked_widget = QStackedWidget()
            self.stacked_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            self.welcome_widget = self.create_welcome_widget()
            self.welcome_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.stacked_widget.addWidget(self.welcome_widget)
            
            self.stacked_widget.addWidget(self.tab_widget)
            layout.addWidget(self.stacked_widget, stretch=1)
            self.stacked_widget.setCurrentWidget(self.welcome_widget)
        except Exception as e:
            print(f"Error in TabManagerWidget.setup_ui: {e}")
            import traceback
            traceback.print_exc()
            raise
        
    def connect_signals(self):
        """Connect signals and slots."""
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        signal_hub.tab_created.connect(self.on_tab_created)
        signal_hub.note_content_set.connect(self.on_note_content_set)
        signal_hub.note_saved.connect(self.on_note_saved)
        signal_hub.note_open_requested.connect(self.on_note_open_requested)
        signal_hub.note_deleted.connect(self.on_note_deleted)
        signal_hub.stat_block_open_requested.connect(self.on_stat_block_open_requested)
        self.last_created_tab_index = -1
        # Map note_id to tab index for quick lookup
        self.note_id_to_index = {}
        # Map entity_id to tab index for quick lookup
        self.entity_id_to_index = {}
        
    def create_welcome_widget(self):
        """Create welcome background widget with instructions."""
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setContentsMargins(20, 20, 20, 20)
        welcome_layout.setSpacing(15)
        
        # Add stretch at the top to push content to vertical center
        welcome_layout.addStretch()
        
        welcome_label = QLabel("Welcome to DM Helper!")
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #888888;")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(welcome_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        instructions = QLabel(
            "Get started by:\n\n"
            "• Creating a new note (+ New Note button)\n"
            "• Opening an existing session (File → Open Session)\n"
            "• Exploring the Quick Reference (Ctrl+R)\n"
        )
        instructions.setStyleSheet("font-size: 14px; color: #666666;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(instructions, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Add stretch at the bottom to complete vertical centering
        welcome_layout.addStretch()
        
        return welcome_widget
    
    def show_welcome_background(self):
        """Show welcome background (no tabs)."""
        self.stacked_widget.setCurrentWidget(self.welcome_widget)
        # Make tabs not closable when showing welcome (no tabs to close)
        self.tab_widget.setTabsClosable(False)
    
    def show_tabs(self):
        """Show tab widget (notes exist)."""
        self.stacked_widget.setCurrentWidget(self.tab_widget)
        # Enable tab closing when tabs are shown
        self.tab_widget.setTabsClosable(True)
        
    def add_note_tab(self, title: str = "Untitled", note_id: int = None, note_title: str = None):
        """Add a new note tab."""
        from ui.tabs.note_editor import NoteEditor
        
        # Switch to tab view if currently showing welcome
        if self.stacked_widget.currentWidget() == self.welcome_widget:
            self.show_tabs()
        
        # Use note_title if provided, otherwise use title parameter
        display_title = note_title or title
        note_editor = NoteEditor(note_id=note_id, note_title=display_title)
        # Ensure note editor expands to fill available space
        note_editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        note_editor.attach_clicked.connect(self._on_attach_clicked)
        
        index = self.tab_widget.addTab(note_editor, display_title)
        self.tab_widget.setCurrentIndex(index)
        self.last_created_tab_index = index
        
        # Track note_id to tab index mapping
        if note_id:
            self.note_id_to_index[note_id] = index
        
        return index
    
    def add_stat_block_tab(self, title: str = "Stat Block", entity_id: str = None):
        """Add a new stat block editor tab."""
        from ui.tabs.stat_block_editor import StatBlockEditor
        
        # Switch to tab view if currently showing welcome
        if self.stacked_widget.currentWidget() == self.welcome_widget:
            self.show_tabs()
        
        stat_block = StatBlockEditor(entity_id=entity_id)
        # Ensure stat block expands to fill available space
        stat_block.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        stat_block.attach_clicked.connect(self._on_attach_clicked)
        
        index = self.tab_widget.addTab(stat_block, title)
        self.tab_widget.setCurrentIndex(index)
        self.last_created_tab_index = index
        
        return index
        
    def _on_attach_clicked(self, source_kind: str, source_id):
        """Open Add Relation dialog when user chooses 'Click to add relation'."""
        if source_id is None:
            return
        from ui.dialogs.add_relation_dialog import AddRelationDialog
        dialog = AddRelationDialog(source_kind, source_id, parent=self)
        dialog.exec()
    
    def close_tab(self, index: int):
        """Close a tab."""
        if self.tab_widget.count() == 0:
            return
        
        widget = self.tab_widget.widget(index)
        
        # Save note before closing if it's a NoteEditor with unsaved changes
        if widget and hasattr(widget, 'has_unsaved_changes') and widget.has_unsaved_changes():
            widget.save_note(show_message=False)
        
        # Remove from note_id mapping if it exists
        if widget and hasattr(widget, 'get_note_id'):
            note_id = widget.get_note_id()
            if note_id and note_id in self.note_id_to_index:
                del self.note_id_to_index[note_id]
        
        # Remove from entity_id mapping if it exists
        if widget and hasattr(widget, 'entity_id'):
            entity_id = widget.entity_id
            if entity_id and entity_id in self.entity_id_to_index:
                del self.entity_id_to_index[entity_id]
        
        self.tab_widget.removeTab(index)
        
        if widget:
            widget.deleteLater()
        
        # Rebuild mapping after tab removal
        self._rebuild_note_id_mapping()
        
        # If no tabs left, show welcome background
        if self.tab_widget.count() == 0:
            self.show_welcome_background()
            self.note_id_to_index = {}
            
    def on_tab_created(self, tab_id: str):
        """Handle tab created signal - create new empty note."""
        # Create new note tab (will be saved when user edits it with auto-save)
        self.add_note_tab(title=tab_id, note_id=None)
        
    def on_note_content_set(self, html_content: str):
        """Handle setting content for the last created note."""
        if self.last_created_tab_index >= 0:
            widget = self.tab_widget.widget(self.last_created_tab_index)
            if widget and hasattr(widget, 'set_content'):
                widget.set_content(html_content)
    
    def on_note_saved(self, note_id: int, title: str):
        """Handle note saved signal - update tab title."""
        # Try to find the tab by note_id first
        if note_id and note_id in self.note_id_to_index:
            index = self.note_id_to_index[note_id]
            self.tab_widget.setTabText(index, title)
            # Also update the editor's note_title
            widget = self.tab_widget.widget(index)
            if hasattr(widget, 'set_note_title'):
                widget.set_note_title(title)
            return
        
        # If note_id not in mapping, search through all tabs to find a match
        found = False
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if widget and hasattr(widget, 'get_note_id'):
                widget_note_id = widget.get_note_id()
                # Update if it matches, or if both are None/empty (new notes)
                if (note_id is None and widget_note_id is None) or widget_note_id == note_id:
                    self.tab_widget.setTabText(i, title)
                    if hasattr(widget, 'set_note_title'):
                        widget.set_note_title(title)
                    # Update mapping if note_id was just assigned
                    if note_id and note_id not in self.note_id_to_index:
                        self.note_id_to_index[note_id] = i
                    found = True
                    break
        
        # If still not found and note_id is None, update current tab (for new notes)
        if not found and note_id is None:
            current_index = self.tab_widget.currentIndex()
            if current_index >= 0:
                self.tab_widget.setTabText(current_index, title)
                widget = self.tab_widget.widget(current_index)
                if widget and hasattr(widget, 'set_note_title'):
                    widget.set_note_title(title)
    
    def on_note_deleted(self, note_id: int):
        """Handle note deleted signal - close the tab if it's open."""
        if note_id not in self.note_id_to_index:
            return  # Note tab not open, nothing to do
        
        index = self.note_id_to_index[note_id]
        
        # Validate index is within bounds
        if index < 0 or index >= self.tab_widget.count():
            # Invalid index, just remove from mapping
            del self.note_id_to_index[note_id]
            self._check_and_show_welcome()
            return
        
        # Get widget before removing tab
        widget = self.tab_widget.widget(index)
        
        # Remove the tab
        self.tab_widget.removeTab(index)
        
        # Clean up widget if it exists
        if widget:
            widget.deleteLater()
        
        # Update indices for all tabs after the removed one (indices shift down)
        # Rebuild the mapping since indices changed - this automatically removes the deleted note
        self._rebuild_note_id_mapping()
        
        # Check if we should show welcome background (no tabs left)
        self._check_and_show_welcome()
    
    def _rebuild_note_id_mapping(self):
        """Rebuild the note_id to tab index mapping after tabs are removed/added."""
        self.note_id_to_index = {}
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if widget and hasattr(widget, 'get_note_id'):
                note_id = widget.get_note_id()
                if note_id:
                    self.note_id_to_index[note_id] = i
    
    def _check_and_show_welcome(self):
        """Check if no tabs exist and show welcome background if needed."""
        # If no tabs exist, show welcome background
        if self.tab_widget.count() == 0:
            self.show_welcome_background()
            return
        
        # Check if there are any notes in the database
        from core.database import DatabaseManager
        from sqlalchemy import text
        
        try:
            with DatabaseManager() as db:
                result = db.execute(text("SELECT COUNT(*) FROM notes"))
                note_count = result.scalar()
                
                # If no notes in database, close all tabs and show welcome
                if note_count == 0:
                    # Close all remaining tabs
                    while self.tab_widget.count() > 0:
                        widget = self.tab_widget.widget(0)
                        if widget:
                            widget.deleteLater()
                        self.tab_widget.removeTab(0)
                    
                    self.note_id_to_index = {}
                    self.show_welcome_background()
        except Exception as e:
            print(f"Error checking note count: {e}")
            # If error, just check tab count
            if self.tab_widget.count() == 0:
                self.show_welcome_background()
    
    def on_tab_changed(self, index: int):
        """Handle tab change - auto-save previous tab if needed."""
        # Auto-save previous tab's note if it has unsaved changes
        if index >= 0:
            widget = self.tab_widget.widget(index)
            if hasattr(widget, 'has_unsaved_changes') and widget.has_unsaved_changes():
                if hasattr(widget, 'auto_save_enabled') and widget.auto_save_enabled:
                    widget.auto_save()
    
    def on_note_open_requested(self, note_id: int):
        """Handle request to open a note by ID."""
        # Check if note is already open
        if note_id in self.note_id_to_index:
            index = self.note_id_to_index[note_id]
            self.tab_widget.setCurrentIndex(index)
            return
        
        # Load note from database to get title using raw query to avoid enum issues
        from core.database import DatabaseManager
        from sqlalchemy import text
        
        try:
            with DatabaseManager() as db:
                result = db.execute(text("SELECT title FROM notes WHERE id = :id"), {'id': note_id})
                note_data = result.fetchone()
                if note_data:
                    note_title = note_data[0]
                    self.add_note_tab(note_id=note_id, note_title=note_title)
                    # Switch to the newly opened tab
                    self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        except Exception as e:
            print(f"Error opening note: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def on_stat_block_open_requested(self, entity_id: str):
        """Handle request to open a stat block editor by entity ID."""
        # Check if stat block is already open
        if entity_id and entity_id in self.entity_id_to_index:
            index = self.entity_id_to_index[entity_id]
            self.tab_widget.setCurrentIndex(index)
            return
        
        # Load entity from database to get name
        from core.database import DatabaseManager
        from models.entity import Entity
        
        try:
            with DatabaseManager() as db:
                entity = db.query(Entity).filter(Entity.id == entity_id).first()
                if entity:
                    title = entity.name
                    index = self.add_stat_block_tab(title=title, entity_id=entity_id)
                    if entity_id:
                        self.entity_id_to_index[entity_id] = index
                    # Switch to the newly opened tab
                    self.tab_widget.setCurrentIndex(index)
                else:
                    print(f"Entity with ID {entity_id} not found")
        except Exception as e:
            print(f"Error opening stat block: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def load_existing_notes(self, limit: int = 10):
        """Load existing notes from database and add as tabs."""
        from core.database import DatabaseManager
        from sqlalchemy import text
        
        try:
            with DatabaseManager() as db:
                # Load most recently updated notes using raw query to avoid enum issues
                result = db.execute(text("""
                    SELECT id, title FROM notes 
                    ORDER BY updated_at DESC 
                    LIMIT :limit
                """), {'limit': limit})
                notes_data = result.fetchall()
                
                if len(notes_data) > 0:
                    # Switch to tab view
                    self.show_tabs()
                    
                    for note_id, note_title in notes_data:
                        self.add_note_tab(note_id=note_id, note_title=note_title)
                else:
                    # No notes found, show welcome background
                    self.show_welcome_background()
                    
        except Exception as e:
            print(f"Error loading notes: {str(e)}")

