"""Data manager widget for organizing entities."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QHBoxLayout, QLineEdit,
    QTreeWidgetItemIterator, QSizePolicy, QHeaderView,
    QStyle, QApplication, QStyledItemDelegate, QStyleOptionViewItem,
)
from PyQt6.QtCore import Qt, QEvent, QRect
from PyQt6.QtGui import QColor, QDropEvent, QCursor, QPainter, QPen, QBrush
from core.events import signal_hub
from core.settings import get_data_manager_show_hover_add_button


# Notion/Obsidian-style hover "+" button drawn by delegate (no overlay widget)
_BUTTON_SIZE = 22
_BUTTON_MARGIN = 6
_BUTTON_BG = QColor(0x4c, 0x4c, 0x4c)
_BUTTON_FG = QColor(0xff, 0xff, 0xff)


class TreeButtonDelegate(QStyledItemDelegate):
    """Draws a right-aligned circular '+' button when the row is hovered. No overlay widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        # Paint the row as usual first
        super().paint(painter, option, index)
        # Draw "+" button only when the row is hovered and setting is on
        if not (option.state & QStyle.StateFlag.State_MouseOver):
            return
        if not get_data_manager_show_hover_add_button():
            return
        btn_rect = self.get_button_rect(option)
        if btn_rect.isEmpty():
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(_BUTTON_BG))
        painter.drawEllipse(btn_rect)
        painter.setPen(QPen(_BUTTON_FG, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = btn_rect.center().x(), btn_rect.center().y()
        hw = 4
        painter.drawLine(cx - hw, cy, cx + hw, cy)
        painter.drawLine(cx, cy - hw, cx, cy + hw)
        painter.restore()

    @staticmethod
    def get_button_rect(option: QStyleOptionViewItem) -> QRect:
        """Return the rect of the '+' button in the same coordinates as option.rect (viewport)."""
        r = option.rect
        size = _BUTTON_SIZE
        margin = _BUTTON_MARGIN
        x = r.right() - size - margin
        y = r.y() + (r.height() - size) // 2
        return QRect(x, y, size, size)


class CategoryTreeWidget(QTreeWidget):
    """Custom tree widget that handles category drops."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_manager = None
    
    def setParentManager(self, manager):
        """Set reference to parent data manager."""
        self.parent_manager = manager
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event to change entity category."""
        # Get the item being dragged
        source_item = self.currentItem()
        if not source_item or not source_item.parent():
            # Can only drag child items (entities), not categories
            super().dropEvent(event)
            return
        
        # Get drop position
        drop_item = self.itemAt(event.position().toPoint())
        if not drop_item:
            super().dropEvent(event)
            return
        
        # Check if dropped on a category (top-level item)
        is_category = drop_item.parent() is None
        
        if is_category and self.parent_manager:
            # Get entity data from source item
            entity_data = source_item.data(0, Qt.ItemDataRole.UserRole)
            if not entity_data or entity_data.get("type") != "entity":
                super().dropEvent(event)
                return
            
            entity_id = entity_data.get("id")
            if not entity_id:
                super().dropEvent(event)
                return
            
            # Get new entity type from category
            new_type = self.parent_manager.get_entity_type_from_category(drop_item)
            if not new_type:
                super().dropEvent(event)
                return
            
            # Don't do anything if type hasn't changed
            old_category = source_item.parent()
            if old_category == drop_item:
                super().dropEvent(event)
                return
            
            # Update entity type in database
            try:
                from core.database import DatabaseManager
                from models.entity import Entity
                
                with DatabaseManager() as db:
                    entity = db.query(Entity).filter(Entity.id == entity_id).first()
                    if entity:
                        entity.type = new_type
                        db.commit()
                        
                        # Refresh the tree to show the item in its new category
                        self.parent_manager.load_entities_from_database()
                        
                        # Emit signal that entity was updated
                        signal_hub.data_saved.emit(new_type, {"id": entity.id, "name": entity.name})
                        
                        event.accept()
                        return
            except Exception as e:
                print(f"Error updating entity type: {e}")
                import traceback
                traceback.print_exc()
        
        # Default behavior for other cases
        super().dropEvent(event)


class DataManagerWidget(QWidget):
    """Data manager for organizing NPCs, locations, items, etc."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        self.load_notes_from_database()
        self.load_entities_from_database()
        
    def setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Data Manager")
        header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        # Action buttons (icon-only) at top
        style = QApplication.style()
        self.add_page_btn = QPushButton()
        self.add_page_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.add_page_btn.setToolTip("Add new page")
        self.add_page_btn.setFixedSize(28, 28)
        header_layout.addWidget(self.add_page_btn)
        
        self.edit_page_btn = QPushButton()
        self.edit_page_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.edit_page_btn.setToolTip("Edit page")
        self.edit_page_btn.setFixedSize(28, 28)
        self.edit_page_btn.setEnabled(False)
        header_layout.addWidget(self.edit_page_btn)
        
        self.add_to_viewer_btn = QPushButton()
        self.add_to_viewer_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.add_to_viewer_btn.setToolTip("Add to StatBlock Viewer")
        self.add_to_viewer_btn.setFixedSize(28, 28)
        self.add_to_viewer_btn.setEnabled(False)
        header_layout.addWidget(self.add_to_viewer_btn)
        
        self.delete_item_btn = QPushButton()
        self.delete_item_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.delete_item_btn.setToolTip("Delete item")
        self.delete_item_btn.setFixedSize(28, 28)
        self.delete_item_btn.setEnabled(False)
        header_layout.addWidget(self.delete_item_btn)
        
        layout.addLayout(header_layout)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search entities...")
        layout.addWidget(self.search_box)
        
        # Tree widget for hierarchical data (custom class for drop handling)
        self.tree_widget = CategoryTreeWidget()
        self.tree_widget.setParentManager(self)
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setColumnCount(1)
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setDropIndicatorShown(True)
        self.tree_widget.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.tree_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # Hover background for items (dark theme)
        self.tree_widget.setStyleSheet("""
            QTreeWidget { background-color: #2b2b2b; border: 1px solid #4c4c4c; border-radius: 4px; }
            QTreeWidget::item { padding: 4px 6px; color: #E2E8F0; }
            QTreeWidget::item:hover { background-color: #3c3c3c; }
        """)
        layout.addWidget(self.tree_widget)
        
        # Delegate-drawn "+" on hover (no overlay widget; works with scroll and drag & drop)
        self.tree_widget.setItemDelegate(TreeButtonDelegate(self.tree_widget))
        self.tree_widget.viewport().installEventFilter(self)
        
        # Set minimum width
        self.setMinimumWidth(250)
        
    def eventFilter(self, obj, event):
        """Detect mouse press inside the delegate-drawn '+' button and trigger action."""
        if obj is not self.tree_widget.viewport():
            return False
        if event.type() != QEvent.Type.MouseButtonPress:
            return False
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        index = self.tree_widget.indexAt(pos)
        if not index.isValid():
            return False
        option = QStyleOptionViewItem()
        option.rect = self.tree_widget.visualRect(index)
        btn_rect = TreeButtonDelegate.get_button_rect(option)
        if not btn_rect.contains(pos):
            return False
        if not get_data_manager_show_hover_add_button():
            return False
        item = self.tree_widget.itemFromIndex(index)
        if item is None:
            return False
        self._handle_plus_clicked(item)
        return True

    def _handle_plus_clicked(self, item: QTreeWidgetItem):
        """Handle click on the '+' area: category -> add under category; child -> add to viewer."""
        if item.parent() is None:
            category_type = self.get_entity_type_from_category(item)
            if category_type == "note":
                self.create_new_note_in_db()
            else:
                self.add_entity_to_category(item)
        else:
            if not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
                parent = item.parent()
                if self.get_entity_type_from_category(parent) == "note":
                    self.create_new_note_in_db()
                return
            self.tree_widget.setCurrentItem(item)
            self.add_selected_to_statblock_viewer()

    def connect_signals(self):
        """Connect signals and slots."""
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.search_box.textChanged.connect(self.on_search_changed)
        self.add_page_btn.clicked.connect(self.add_entity)
        self.edit_page_btn.clicked.connect(self.edit_selected_entity)
        self.add_to_viewer_btn.clicked.connect(self.add_selected_to_statblock_viewer)
        self.delete_item_btn.clicked.connect(self.delete_selected_entity)
        # Listen for note saves to refresh the notes list
        signal_hub.note_saved.connect(self.on_note_saved)
        # Listen for entity saves to refresh the entities list
        signal_hub.data_saved.connect(self.on_entity_saved)
        
    def load_notes_from_database(self):
        """Load notes from database and display in Data Manager."""
        from core.database import DatabaseManager
        from models.note import Note
        
        # Find or create Notes category
        notes_category = self.find_or_create_category("📝 Notes")
        
        # Clear existing note items
        notes_category.takeChildren()
        
        try:
            with DatabaseManager() as db:
                # Load all notes ordered by most recent
                from sqlalchemy import text
                result = db.execute(text("SELECT id, title FROM notes ORDER BY updated_at DESC"))
                notes_data = result.fetchall()
                
                if len(notes_data) == 0:
                    # Show default message when no notes exist
                    default_item = QTreeWidgetItem(notes_category, ["No notes yet. Create a new note to get started!"])
                    # Make it non-selectable and styled as informational text
                    default_item.setFlags(Qt.ItemFlag.NoItemFlags)
                    # Set a style to make it look like a hint/placeholder
                    default_item.setForeground(0, QColor(128, 128, 128))  # Gray color
                else:
                    # Load notes
                    for note_row in notes_data:
                        note_id, note_title = note_row
                        note_item = QTreeWidgetItem(notes_category, [note_title])
                        note_data = {"type": "note", "id": note_id, "title": note_title}
                        note_item.setData(0, Qt.ItemDataRole.UserRole, note_data)
                    
                print(f"✓ Loaded {len(notes_data)} notes into Data Manager")
                    
        except Exception as e:
            print(f"Error loading notes: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def load_entities_from_database(self):
        """Load entities from database and display in Data Manager."""
        from core.database import DatabaseManager
        from models.entity import Entity
        
        # Create categories for different entity types
        type_categories = {
            "statblock": "📊 Stat Blocks",
            "creature": "👹 Creatures",
            "npc": "📋 NPCs",
            "location": "🗺️ Locations",
            "item": "⚔️ Items",
            "spell": "✨ Spells",
            "note": "📝 Notes"
        }
        
        try:
            with DatabaseManager() as db:
                # Load all entities grouped by type
                entities = db.query(Entity).order_by(Entity.updated_at.desc()).all()
                
                # Group entities by type
                entities_by_type = {}
                for entity in entities:
                    entity_type = entity.type
                    if entity_type not in entities_by_type:
                        entities_by_type[entity_type] = []
                    entities_by_type[entity_type].append(entity)
                
                # Create category items and populate
                for entity_type, entity_list in entities_by_type.items():
                    # Sort entities alphabetically by name (case-insensitive)
                    entity_list = sorted(entity_list, key=lambda e: (e.name or "").lower())
                    # Get category name
                    category_name = type_categories.get(entity_type, f"📦 {entity_type.title()}s")
                    category_item = self.find_or_create_category(category_name)
                    
                    # Clear existing items in this category
                    category_item.takeChildren()
                    
                    # Add entities
                    for entity in entity_list:
                        entity_item = QTreeWidgetItem(category_item, [entity.name])
                        entity_data = {
                            "type": "entity",
                            "id": entity.id,
                            "name": entity.name
                        }
                        entity_item.setData(0, Qt.ItemDataRole.UserRole, entity_data)
                    
                    category_item.setExpanded(True)
                
                print(f"✓ Loaded {len(entities)} entities into Data Manager")
                    
        except Exception as e:
            print(f"Error loading entities: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def find_or_create_category(self, category_name: str):
        """Find a category item or create it if it doesn't exist."""
        root = self.tree_widget.invisibleRootItem()
        
        # Check if category already exists
        for i in range(root.childCount()):
            item = root.child(i)
            if item.text(0) == category_name:
                return item
        
        # Create new category (add at the beginning)
        category_item = QTreeWidgetItem(self.tree_widget, [category_name])
        category_item.setExpanded(True)
        # Move to top
        self.tree_widget.takeTopLevelItem(self.tree_widget.indexOfTopLevelItem(category_item))
        self.tree_widget.insertTopLevelItem(0, category_item)
        return category_item
    
    def on_note_saved(self, note_id: int, title: str):
        """Handle note saved signal - refresh notes list."""
        self.load_notes_from_database()
    
    def on_entity_saved(self, entity_type: str, entity_data: dict):
        """Handle entity saved signal - refresh entities list."""
        self.load_entities_from_database()
    
    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click."""
        # Enable/disable edit and delete buttons
        is_child = item.parent() is not None
        # Disable buttons for default message item (non-selectable items)
        is_default_message = not (item.flags() & Qt.ItemFlag.ItemIsSelectable)
        
        self.edit_page_btn.setEnabled(is_child and not is_default_message)
        self.add_to_viewer_btn.setEnabled(is_child and not is_default_message)
        self.delete_item_btn.setEnabled(is_child and not is_default_message)
        
        # Emit signal for data selection: placeholder when category or default row; entity/note when child
        if is_child and not is_default_message:
            # Get entity data from item
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data and item_data.get("type") == "entity":
                signal_hub.data_selected.emit("entity", item_data)
            else:
                signal_hub.data_selected.emit("entity", item.text(column))
        else:
            # Category or non-selectable row: show placeholder in Display Menu
            signal_hub.data_selected.emit("none", None)
            
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double click - open in editor."""
        # Skip default message items (non-selectable)
        if not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
            return
        
        if item.parent() is not None:  # Only for child items
            # Check if it's a note or entity
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data and item_data.get("type") == "note":
                self.open_note(item)
            elif item_data and item_data.get("type") == "entity":
                self.open_entity_stat_block(item)
            else:
                self.open_entity_in_note(item)
    
    def open_note(self, item: QTreeWidgetItem):
        """Open a note from the database in a tab."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or item_data.get("type") != "note":
            return
        
        note_id = item_data.get("id")
        # Emit signal to open note by ID
        signal_hub.note_open_requested.emit(note_id)
            
    def open_entity_stat_block(self, item: QTreeWidgetItem):
        """Open entity in stat block editor."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or item_data.get("type") != "entity":
            return
        
        entity_id = item_data.get("id")
        if entity_id:
            # Emit signal to open stat block editor
            signal_hub.stat_block_open_requested.emit(entity_id)
    
    def open_entity_in_note(self, item: QTreeWidgetItem):
        """Open entity information in a new note tab."""
        # Get entity data
        entity_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not entity_data:
            # Parse from text if no data stored
            text = item.text(0)
            if '(' in text and ')' in text:
                name = text[:text.index('(')].strip()
                type_str = text[text.index('(')+1:text.index(')')].strip()
            else:
                name = text
                type_str = ""
            entity_data = {"name": name, "type": type_str, "description": ""}
        
        # Get entity type from parent
        parent = item.parent()
        entity_type = self.get_entity_type_from_category(parent)
        
        # Format the note content
        html_content = self.format_entity_as_note(entity_data, entity_type)
        
        # Emit signal to create note with content
        from core.events import signal_hub
        signal_hub.tab_created.emit(entity_data.get("name", "Entity"))
        
        # Send the content to be set (we'll need to add this functionality)
        # For now, we'll use a new signal
        signal_hub.note_content_set.emit(html_content)
        
    def format_entity_as_note(self, entity_data: dict, entity_type: str) -> str:
        """Format entity data as HTML for note."""
        name = entity_data.get("name", "Unknown")
        entity_type_str = entity_data.get("type", "")
        description = entity_data.get("description", "")
        
        # Create formatted HTML
        html = f"""
        <h1>{name}</h1>
        <p><strong>Type:</strong> {entity_type}</p>
        """
        
        if entity_type_str:
            html += f"<p><strong>Category:</strong> {entity_type_str}</p>"
        
        html += "<hr>"
        
        if description:
            html += f"<h2>Description</h2><p>{description}</p><hr>"
        
        html += "<h2>Notes</h2><p><br></p>"
        
        return html
            
    def show_context_menu(self, position):
        """Show context menu for tree items."""
        from PyQt6.QtWidgets import QMenu, QInputDialog
        from PyQt6.QtGui import QAction
        
        item = self.tree_widget.itemAt(position)
        menu = QMenu(self)
        
        if item is None:
            # Right-click on empty space - show general options
            new_folder_action = QAction("📁 New Folder", self)
            new_folder_action.triggered.connect(self.create_new_folder)
            menu.addAction(new_folder_action)
            
            menu.addSeparator()
            
            refresh_action = QAction("🔄 Refresh", self)
            refresh_action.triggered.connect(self.refresh_all)
            menu.addAction(refresh_action)
            
        elif item.parent() is None:  # Root-level item (category or root-level folder)
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data and item_data.get("type") == "folder":
                # Root-level folder menu
                rename_folder_action = QAction("✏️ Rename Folder", self)
                rename_folder_action.triggered.connect(lambda: self.rename_folder(item))
                menu.addAction(rename_folder_action)
                
                menu.addSeparator()
                
                delete_folder_action = QAction("🗑️ Delete Folder", self)
                delete_folder_action.triggered.connect(lambda: self.delete_folder(item))
                menu.addAction(delete_folder_action)
            else:
                # Category-level menu
                category_name = item.text(0)
                category_type = self.get_entity_type_from_category(item)
                
                # Create new item in this category (persisted in DB)
                if category_type == "note":
                    new_note_action = QAction("➕ New Note", self)
                    new_note_action.triggered.connect(self.create_new_note_in_db)
                    menu.addAction(new_note_action)
                elif category_type:
                    pretty = category_name.replace("📊", "").replace("👹", "").replace("📋", "").replace("🗺️", "").replace("⚔️", "").replace("✨", "").strip()
                    new_entity_action = QAction(f"➕ New {pretty[:-1] if pretty.endswith('s') else pretty}", self)
                    new_entity_action.triggered.connect(lambda: self.create_new_entity_in_db(category_type))
                    menu.addAction(new_entity_action)
                
                # Legacy: add dialog-driven item (non-persisted) - keep for now if needed
                # add_action = QAction(f"➕ Add to {category_name}", self)
                # add_action.triggered.connect(lambda: self.add_entity_to_category(item))
                # menu.addAction(add_action)
                
                menu.addSeparator()
                
                # Folder operations
                new_folder_action = QAction("📁 New Folder", self)
                new_folder_action.triggered.connect(lambda: self.create_folder_in_category(item))
                menu.addAction(new_folder_action)
                
                menu.addSeparator()
                
                # Category management
                expand_all_action = QAction("📂 Expand All", self)
                expand_all_action.triggered.connect(lambda: self.expand_category(item))
                menu.addAction(expand_all_action)
                
                collapse_all_action = QAction("📁 Collapse All", self)
                collapse_all_action.triggered.connect(lambda: self.collapse_category(item))
                menu.addAction(collapse_all_action)
                
                menu.addSeparator()
                
                refresh_action = QAction("🔄 Refresh", self)
                refresh_action.triggered.connect(self.refresh_all)
                menu.addAction(refresh_action)
            
        else:  # Entity or folder item
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Check if it's a folder
            if item_data and item_data.get("type") == "folder":
                # Folder menu
                rename_folder_action = QAction("✏️ Rename Folder", self)
                rename_folder_action.triggered.connect(lambda: self.rename_folder(item))
                menu.addAction(rename_folder_action)
                
                menu.addSeparator()
                
                delete_folder_action = QAction("🗑️ Delete Folder", self)
                delete_folder_action.triggered.connect(lambda: self.delete_folder(item))
                menu.addAction(delete_folder_action)
            else:
                # Entity or note item menu
                # Add "Open Stat Block" for entities
                if item_data and item_data.get("type") == "entity":
                    open_stat_block_action = QAction("📊 Open Stat Block", self)
                    open_stat_block_action.triggered.connect(lambda: self.open_entity_stat_block(item))
                    menu.addAction(open_stat_block_action)
                    
                    add_to_list_action = QAction("➕ Add to List", self)
                    add_to_list_action.triggered.connect(lambda: self.add_entity_to_stat_block_list(item_data))
                    menu.addAction(add_to_list_action)
                    
                    menu.addSeparator()
                elif item_data and item_data.get("type") == "note":
                    # For notes, add to list option
                    add_to_list_action = QAction("➕ Add to List", self)
                    add_to_list_action.triggered.connect(lambda: self.add_entity_to_stat_block_list(item_data))
                    menu.addAction(add_to_list_action)
                    
                    menu.addSeparator()
                
                # Move to folder option (for entities only)
                if item_data and item_data.get("type") == "entity":
                    move_to_folder_action = QAction("📁 Move to Folder", self)
                    move_to_folder_action.triggered.connect(lambda: self.move_entity_to_folder(item))
                    menu.addAction(move_to_folder_action)
                    
                    menu.addSeparator()
                
                # Edit and duplicate (for entities only)
                if item_data and item_data.get("type") == "entity":
                    edit_action = QAction("✏️ Edit", self)
                    edit_action.triggered.connect(lambda: self.edit_entity(item))
                    menu.addAction(edit_action)
                    
                    duplicate_action = QAction("📋 Duplicate", self)
                    duplicate_action.triggered.connect(lambda: self.duplicate_entity(item))
                    menu.addAction(duplicate_action)
                    
                    menu.addSeparator()
                
                # Delete action
                delete_action = QAction("🗑️ Delete", self)
                delete_action.triggered.connect(lambda: self.delete_entity(item))
                menu.addAction(delete_action)
            
        menu.exec(self.tree_widget.mapToGlobal(position))
        
    def on_search_changed(self, text: str):
        """Handle search text change."""
        # Simple search implementation
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        
        while iterator.value():
            item = iterator.value()
            # Show/hide based on search (only search child items)
            if item.parent():  # Only search child items
                item.setHidden(
                    text.lower() not in item.text(0).lower() if text else False
                )
            iterator += 1
            
    def add_entity(self):
        """Show dialog to add new entity."""
        from PyQt6.QtWidgets import QInputDialog
        from ui.dialogs.entity_editor_dialog import EntityEditorDialog
        
        # Ask for entity type
        types = ["NPC", "Location", "Item", "Monster"]
        entity_type, ok = QInputDialog.getItem(
            self, "Select Entity Type", "Choose the type of entity to create:",
            types, 0, False
        )
        
        if ok and entity_type:
            dialog = EntityEditorDialog(entity_type, parent=self)
            if dialog.exec():
                data = dialog.get_data()
                self.create_entity(entity_type, data)
                
    def add_entity_to_category(self, category_item):
        """Add entity to specific category."""
        from ui.dialogs.entity_editor_dialog import EntityEditorDialog
        
        # Extract entity type from category name (remove emoji and trim)
        category_text = category_item.text(0)
        entity_type = category_text.split()[-1].rstrip('s')  # Remove trailing 's'
        
        dialog = EntityEditorDialog(entity_type, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            self.create_entity(entity_type, data, category_item)
            
    def create_entity(self, entity_type: str, data: dict, category_item=None):
        """Create a new entity in the tree."""
        # Find the appropriate category
        if category_item is None:
            category_item = self.find_category_by_type(entity_type)
            
        if category_item:
            # Format the entity name
            name = data['name']
            entity_type_str = data.get('type', '')
            if entity_type_str:
                display_text = f"{name} ({entity_type_str})"
            else:
                display_text = name
                
            # Add to tree
            new_item = QTreeWidgetItem(category_item, [display_text])
            new_item.setData(0, Qt.ItemDataRole.UserRole, data)
            category_item.setExpanded(True)
            
            # Emit signal
            signal_hub.data_saved.emit(entity_type, data)
            
    def edit_selected_entity(self):
        """Edit the currently selected entity or open the selected note."""
        item = self.tree_widget.currentItem()
        if not item or not item.parent():
            return
        if not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
            return
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data and item_data.get("type") == "note":
            self.open_note(item)
        else:
            self.edit_entity(item)

    def add_selected_to_statblock_viewer(self):
        """Add the currently selected item to the StatBlock Viewer list."""
        item = self.tree_widget.currentItem()
        if not item or not item.parent():
            return
        if not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
            return
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or item_data.get("type") not in ("entity", "note"):
            return
        payload = dict(item_data)
        if payload.get("type") == "note" and "name" not in payload:
            payload["name"] = payload.get("title", "")
        self.add_entity_to_stat_block_list(payload)
            
    def edit_entity(self, item: QTreeWidgetItem):
        """Edit an entity."""
        from ui.dialogs.entity_editor_dialog import EntityEditorDialog
        
        # Get existing data
        existing_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not existing_data:
            # Parse from text if no data stored
            text = item.text(0)
            if '(' in text and ')' in text:
                name = text[:text.index('(')].strip()
                type_str = text[text.index('(')+1:text.index(')')].strip()
            else:
                name = text
                type_str = ""
            existing_data = {"name": name, "type": type_str, "description": ""}
            
        # Determine entity type from parent
        parent = item.parent()
        entity_type = self.get_entity_type_from_category(parent)
        
        dialog = EntityEditorDialog(entity_type, existing_data, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            
            # Update item
            name = data['name']
            type_str = data.get('type', '')
            if type_str:
                display_text = f"{name} ({type_str})"
            else:
                display_text = name
                
            item.setText(0, display_text)
            item.setData(0, Qt.ItemDataRole.UserRole, data)
            
            # Emit signal
            signal_hub.data_saved.emit(entity_type, data)
            
    def delete_selected_entity(self):
        """Delete the currently selected entity."""
        item = self.tree_widget.currentItem()
        if item and item.parent():
            self.delete_entity(item)
            
    def delete_entity(self, item: QTreeWidgetItem):
        """Delete an entity or note."""
        from PyQt6.QtWidgets import QMessageBox
        from core.database import DatabaseManager
        
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        item_name = item.text(0)
        
        # Check if it's a note
        if item_data and item_data.get("type") == "note":
            note_id = item_data.get("id")
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete note '{item_name}'?\n\nThis will permanently delete it from the database.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    from models.note import Note
                    from models.relation import Relation
                    from sqlalchemy import text
                    
                    with DatabaseManager() as db:
                        # Find the note
                        note = db.query(Note).filter(Note.id == note_id).first()
                        if not note:
                            QMessageBox.warning(
                                self, "Delete Error",
                                f"Note '{item_name}' not found in database."
                            )
                            return
                        
                        # Delete all relations pointing to or from this note
                        # Relations are already set to cascade, but let's be explicit for safety
                        db.execute(text("DELETE FROM relations WHERE from_note_id = :id OR to_note_id = :id"), {"id": note_id})
                        
                        # Delete all metadata for this note
                        db.execute(text("DELETE FROM note_metadata WHERE note_id = :id"), {"id": note_id})
                        
                        # Delete note_tags associations (many-to-many relationship)
                        db.execute(text("DELETE FROM note_tags WHERE note_id = :id"), {"id": note_id})
                        
                        # Delete the note itself (cascade will handle children via parent_id relationship)
                        db.delete(note)
                        # Commit is handled by DatabaseManager context manager
                        
                        print(f"✓ Deleted note '{item_name}' (ID: {note_id}) from database")
                        
                    # Remove from tree
                    parent = item.parent()
                    if parent:
                        parent.removeChild(item)
                        # Update the tree widget
                        self.tree_widget.update()
                        
                        # If the category is now empty, optionally remove it (but keep Notes category)
                        if parent.childCount() == 0 and parent.text(0) != "📝 Notes":
                            root = self.tree_widget.invisibleRootItem()
                            root.removeChild(parent)
                    
                    # Clear selection and disable buttons
                    self.edit_page_btn.setEnabled(False)
                    self.add_to_viewer_btn.setEnabled(False)
                    self.delete_item_btn.setEnabled(False)
                    
                    # Refresh the notes list to reflect the deletion
                    self.load_notes_from_database()
                    
                    # Close the note tab if it's open
                    signal_hub.note_deleted.emit(note_id)
                    
                except Exception as e:
                    QMessageBox.critical(
                        self, "Delete Error",
                        f"Error deleting note from database:\n{str(e)}\n\nPlease check console for details."
                    )
                    import traceback
                    traceback.print_exc()
            return
        
        # Handle regular entities (not yet in DB, but prepare for future)
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{item_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            parent = item.parent()
            
            # Try to delete from database if this is a persisted entity
            try:
                entity_data = item.data(0, Qt.ItemDataRole.UserRole)
                entity_id = entity_data.get("id") if entity_data else None
                
                if entity_id:
                    from core.database import DatabaseManager
                    from models.entity import Entity
                    
                    with DatabaseManager() as db:
                        entity = db.query(Entity).filter(Entity.id == entity_id).first()
                        if entity:
                            entity_type_db = entity.type
                            db.delete(entity)
                            # Commit handled by context manager
                            
                            print(f"✓ Deleted entity '{entity.name}' (ID: {entity_id}) from database")
                            
                            # Emit deletion signal with type and id
                            signal_hub.data_deleted.emit(entity_type_db, entity_id)
                else:
                    # No id stored; fall through to just removing from tree
                    pass
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self, "Delete Error",
                    f"Error deleting entity from database:\n{str(e)}\n\nPlease check console for details."
                )
                import traceback
                traceback.print_exc()
            
            # Remove from tree UI
            if parent:
                parent.removeChild(item)
            
            # Clear selection and disable buttons
            self.edit_page_btn.setEnabled(False)
            self.add_to_viewer_btn.setEnabled(False)
            self.delete_item_btn.setEnabled(False)
            
            # Refresh entities from database to reflect deletion
            self.load_entities_from_database()
            
    def find_category_by_type(self, entity_type: str):
        """Find category item by entity type."""
        type_map = {
            "NPC": "📋 NPCs",
            "Location": "🗺️ Locations",
            "Item": "⚔️ Items",
            "Monster": "👹 Monsters"
        }
        
        category_name = type_map.get(entity_type)
        if not category_name:
            return None
            
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.text(0) == category_name:
                return item
        return None
        
    def get_entity_type_from_category(self, category_item):
        """Get entity type from category item."""
        category_text = category_item.text(0)
        # Reverse mapping from category name to entity type
        type_map = {
            "📊 Stat Blocks": "statblock",
            "👹 Creatures": "creature",
            "📋 NPCs": "npc",
            "🗺️ Locations": "location",
            "⚔️ Items": "item",
            "✨ Spells": "spell",
            "📝 Notes": "note"
        }
        return type_map.get(category_text, None)

    def create_new_entity_in_db(self, entity_type: str):
        """Create a new Entity row in the DB and open it in stat block editor."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        from core.database import DatabaseManager
        from models.entity import Entity

        default_name = f"New {entity_type.title()}"
        name, ok = QInputDialog.getText(self, "New", "Name:", text=default_name)
        if not ok:
            return
        name = (name or "").strip() or default_name

        try:
            with DatabaseManager() as db:
                entity = Entity(type=entity_type, name=name)
                db.add(entity)
                db.commit()
                db.refresh(entity)

            # Refresh list and open in editor
            self.load_entities_from_database()
            signal_hub.data_saved.emit(entity.type, {"id": entity.id, "name": entity.name})
            signal_hub.stat_block_open_requested.emit(entity.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create entity:\n{e}")
            import traceback
            traceback.print_exc()

    def create_new_note_in_db(self):
        """Create a new Note row in the DB and open it."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        from core.database import DatabaseManager
        from models.note import Note

        default_title = "New Note"
        title, ok = QInputDialog.getText(self, "New Note", "Title:", text=default_title)
        if not ok:
            return
        title = (title or "").strip() or default_title

        try:
            with DatabaseManager() as db:
                note = Note(title=title, content="")
                db.add(note)
                db.commit()
                db.refresh(note)

            # Refresh list and open
            self.load_notes_from_database()
            signal_hub.note_saved.emit(note.id, note.title)
            signal_hub.note_open_requested.emit(note.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create note:\n{e}")
            import traceback
            traceback.print_exc()
    
    def create_new_folder(self):
        """Create a new folder at root level."""
        from PyQt6.QtWidgets import QInputDialog
        
        folder_name, ok = QInputDialog.getText(
            self, "New Folder", "Folder name:",
            text="New Folder"
        )
        
        if ok and folder_name.strip():
            folder_item = QTreeWidgetItem(self.tree_widget, [f"📁 {folder_name.strip()}"])
            folder_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": folder_name.strip()})
            folder_item.setExpanded(True)
    
    def create_folder_in_category(self, category_item):
        """Create a new folder within a category."""
        from PyQt6.QtWidgets import QInputDialog
        
        folder_name, ok = QInputDialog.getText(
            self, "New Folder", "Folder name:",
            text="New Folder"
        )
        
        if ok and folder_name.strip():
            folder_item = QTreeWidgetItem(category_item, [f"📁 {folder_name.strip()}"])
            folder_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": folder_name.strip()})
            folder_item.setExpanded(True)
            category_item.setExpanded(True)
    
    def rename_folder(self, folder_item):
        """Rename a folder."""
        from PyQt6.QtWidgets import QInputDialog
        
        current_name = folder_item.text(0).replace("📁 ", "")
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", "Folder name:",
            text=current_name
        )
        
        if ok and new_name.strip():
            folder_item.setText(0, f"📁 {new_name.strip()}")
            folder_data = folder_item.data(0, Qt.ItemDataRole.UserRole)
            if folder_data:
                folder_data["name"] = new_name.strip()
                folder_item.setData(0, Qt.ItemDataRole.UserRole, folder_data)
    
    def delete_folder(self, folder_item):
        """Delete a folder and move its children to parent."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, "Delete Folder",
            f"Delete folder '{folder_item.text(0)}'?\n\nItems in this folder will be moved to the parent category.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            parent = folder_item.parent()
            if parent:
                # Move all children to parent category
                while folder_item.childCount() > 0:
                    child = folder_item.takeChild(0)
                    parent.addChild(child)
            else:
                # Root level folder - move children to root
                root = self.tree_widget.invisibleRootItem()
                while folder_item.childCount() > 0:
                    child = folder_item.takeChild(0)
                    root.addChild(child)
            
            # Remove folder
            if parent:
                parent.removeChild(folder_item)
            else:
                root.removeChild(folder_item)
    
    def move_entity_to_folder(self, entity_item):
        """Move an entity to a folder."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        # Get all folders in the same category
        parent = entity_item.parent()
        folders = []
        
        if parent:
            for i in range(parent.childCount()):
                child = parent.child(i)
                child_data = child.data(0, Qt.ItemDataRole.UserRole)
                if child_data and child_data.get("type") == "folder":
                    folders.append(child.text(0).replace("📁 ", ""))
        
        if not folders:
            QMessageBox.information(
                self, "No Folders",
                "No folders available. Create a folder first."
            )
            return
        
        folder_name, ok = QInputDialog.getItem(
            self, "Move to Folder", "Select folder:",
            folders, 0, False
        )
        
        if ok and folder_name:
            # Find the folder item
            target_folder = None
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.text(0) == f"📁 {folder_name}":
                    target_folder = child
                    break
            
            if target_folder:
                # Remove from current parent
                parent.removeChild(entity_item)
                # Add to folder
                target_folder.addChild(entity_item)
                target_folder.setExpanded(True)
    
    def duplicate_entity(self, entity_item):
        """Duplicate an entity."""
        from PyQt6.QtWidgets import QInputDialog
        
        entity_data = entity_item.data(0, Qt.ItemDataRole.UserRole)
        if not entity_data or entity_data.get("type") != "entity":
            return
        
        entity_id = entity_data.get("id")
        if not entity_id:
            # Can't duplicate entities not in database
            return
        
        try:
            from core.database import DatabaseManager
            from models.entity import Entity, EntityProperty, EntitySection
            from sqlalchemy.orm import joinedload
            
            with DatabaseManager() as db:
                # Load original entity with all relationships
                original = db.query(Entity).options(
                    joinedload(Entity.properties),
                    joinedload(Entity.sections)
                ).filter(Entity.id == entity_id).first()
                
                if not original:
                    return
                
                # Create duplicate
                new_entity = Entity(
                    type=original.type,
                    name=f"{original.name} (Copy)"
                )
                db.add(new_entity)
                db.flush()
                
                # Copy properties
                for prop in original.properties:
                    new_prop = EntityProperty(
                        entity_id=new_entity.id,
                        key=prop.key,
                        value=prop.value
                    )
                    db.add(new_prop)
                
                # Copy sections
                for section in original.sections:
                    new_section = EntitySection(
                        entity_id=new_entity.id,
                        section_type=section.section_type,
                        content=section.content,
                        sort_order=section.sort_order
                    )
                    db.add(new_section)
                
                db.commit()
                
                # Refresh the tree
                self.load_entities_from_database()
                
                # Emit signal
                signal_hub.data_saved.emit(new_entity.type, {"id": new_entity.id, "name": new_entity.name})
                
        except Exception as e:
            print(f"Error duplicating entity: {e}")
            import traceback
            traceback.print_exc()
    
    def expand_category(self, category_item):
        """Expand all items in a category."""
        category_item.setExpanded(True)
        for i in range(category_item.childCount()):
            child = category_item.child(i)
            child.setExpanded(True)
            # Recursively expand folders
            if child.childCount() > 0:
                self.expand_category(child)
    
    def collapse_category(self, category_item):
        """Collapse all items in a category."""
        for i in range(category_item.childCount()):
            child = category_item.child(i)
            child.setExpanded(False)
            # Recursively collapse folders
            if child.childCount() > 0:
                self.collapse_category(child)
        category_item.setExpanded(False)
    
    def refresh_all(self):
        """Refresh all data in the data manager."""
        self.load_notes_from_database()
        self.load_entities_from_database()
    
    def add_entity_to_stat_block_list(self, item_data: dict):
        """Add entity to stat block viewer list."""
        # Emit signal to add item to stat block viewer list
        signal_hub.add_to_stat_block_list.emit(item_data)
    

