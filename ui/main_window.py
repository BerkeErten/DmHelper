"""Main window with grid-based layout."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSplitter, QMenuBar, QMenu, QDockWidget, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from core.config import WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, APP_NAME
from core.events import signal_hub


class MainWindow(QMainWindow):
    """Main application window with layout manager."""
    
    def __init__(self):
        super().__init__()
        try:
            self.setup_window()
            self.setup_menu()
            self.setup_layout()
            self.connect_signals()
        except Exception as e:
            print(f"Error in MainWindow.__init__: {e}")
            import traceback
            traceback.print_exc()
            raise
        
    def setup_window(self):
        """Configure main window properties."""
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1400, 900)
        
    def setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_session_action = QAction("&New Session", self)
        new_session_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_session_action)
        
        open_session_action = QAction("&Open Session", self)
        open_session_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_session_action)
        
        save_session_action = QAction("&Save Session", self)
        save_session_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_session_action)
        
        file_menu.addSeparator()
        
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        toggle_console_action = QAction("Toggle &Console", self)
        toggle_console_action.setShortcut("Ctrl+`")
        toggle_console_action.triggered.connect(self.toggle_console)
        view_menu.addAction(toggle_console_action)
        
        toggle_quickref_action = QAction("Toggle &Quick Reference", self)
        toggle_quickref_action.setShortcut("Ctrl+R")
        toggle_quickref_action.triggered.connect(self.toggle_quickref)
        view_menu.addAction(toggle_quickref_action)
        
        toggle_datamanager_action = QAction("Toggle &Data Manager", self)
        toggle_datamanager_action.setShortcut("Ctrl+D")
        toggle_datamanager_action.triggered.connect(self.toggle_datamanager)
        view_menu.addAction(toggle_datamanager_action)
        
        toggle_statblock_viewer_action = QAction("Toggle &StatBlock Viewer", self)
        toggle_statblock_viewer_action.setShortcut("Ctrl+B")
        toggle_statblock_viewer_action.triggered.connect(self.toggle_statblock_viewer)
        view_menu.addAction(toggle_statblock_viewer_action)
        
        knowledge_base_action = QAction("Knowledge &Base", self)
        knowledge_base_action.setShortcut("Ctrl+K")
        knowledge_base_action.triggered.connect(self.open_knowledge_base)
        view_menu.addAction(knowledge_base_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        dice_roller_action = QAction("&Dice Roller", self)
        dice_roller_action.setShortcut("Ctrl+Shift+D")
        dice_roller_action.triggered.connect(self.open_dice_roller)
        tools_menu.addAction(dice_roller_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        help_menu.addAction(about_action)
        
    def setup_layout(self):
        """Setup the main layout using grid for clear positioning."""
        try:
            # Create central widget
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # GRID LAYOUT - Makes positioning crystal clear!
            # Row 0: Top Bar (fixed 42px)
            # Row 1: Tab Bar Container (fixed 60px)
            # Row 2: Content Area (expandable - tabs + data manager)
            # Row 3: Console (expandable)
            main_layout = QGridLayout(central_widget)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            
            # Import widgets
            from ui.topbar.topbar_widget import TopBarWidget
            from ui.tabs.tab_manager import TabManagerWidget
            from ui.datamanager.datamanager_widget import DataManagerWidget
            from ui.console.console_widget import ConsoleWidget
            
            # ROW 0: Top bar (spans all columns)
            self.topbar = TopBarWidget()
            self.topbar.setFixedHeight(42)
            main_layout.addWidget(self.topbar, 0, 0, 1, 2)  # row=0, col=0, rowspan=1, colspan=2
            
            # ROW 1: Tab bar container (spans all columns) - taller for border
            tab_bar_container = QWidget()
            tab_bar_container.setStyleSheet("background-color: #2b2b2b;")
            
            tab_bar_layout = QVBoxLayout(tab_bar_container)
            tab_bar_layout.setContentsMargins(10, 5, 10, 0)
            tab_bar_layout.setSpacing(0)
            
            # Create a separate QTabBar widget and sync it with the tab widget
            from PyQt6.QtWidgets import QTabBar
            from ui.themes.tab_styles import TAB_BAR_STYLESHEET
            
            self.tab_bar = QTabBar()
            self.tab_bar.setTabsClosable(True)
            self.tab_bar.setMovable(True)
            self.tab_bar.setExpanding(False)
            self.tab_bar.setDrawBase(False)
            self.tab_bar.setDocumentMode(True)
            
            # Apply shared tab styling
            self.tab_bar.setStyleSheet(TAB_BAR_STYLESHEET)
            self.tab_bar.raise_()  # Ensure tab bar is on top
            
            # Add tab bar and separator
            tab_bar_layout.addWidget(self.tab_bar)
            
            # Separator line below tabs
            separator_line = QWidget()
            separator_line.setFixedHeight(1)
            separator_line.setStyleSheet("background-color: #3c3c3c;")
            tab_bar_layout.addWidget(separator_line)
            
            self.tab_bar_container = tab_bar_container
            main_layout.addWidget(tab_bar_container, 1, 0, 1, 2)  # row=1, col=0, rowspan=1, colspan=2
            
            # ROW 2: Content area with horizontal splitter
            self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Tab manager (left side)
            self.tab_manager = TabManagerWidget()
            self.tab_manager.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.content_splitter.addWidget(self.tab_manager)
            
            # Data manager (right side)
            self.data_manager = DataManagerWidget()
            self.data_manager.setMinimumWidth(250)
            self.data_manager.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.content_splitter.addWidget(self.data_manager)
            
            # Set splitter proportions (70% tabs, 30% data manager)
            self.content_splitter.setStretchFactor(0, 7)
            self.content_splitter.setStretchFactor(1, 3)
            
            # ROW 2-3: Create vertical splitter for content and console
            self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
            
            # Add content splitter to vertical splitter
            self.vertical_splitter.addWidget(self.content_splitter)
            
            # Add console to vertical splitter
            self.console = ConsoleWidget()
            self.console.setMinimumHeight(150)
            self.vertical_splitter.addWidget(self.console)
            
            # Set splitter proportions (75% content, 25% console)
            self.vertical_splitter.setStretchFactor(0, 3)
            self.vertical_splitter.setStretchFactor(1, 1)
            
            # Add vertical splitter to grid (row 2, spans both columns, takes rows 2-3)
            main_layout.addWidget(self.vertical_splitter, 2, 0, 1, 2)  # row=2, col=0, rowspan=1, colspan=2
            
            # Set row stretch factors for vertical sizing
            main_layout.setRowStretch(0, 0)  # Top bar: no stretch (fixed)
            main_layout.setRowStretch(1, 0)  # Tab bar: no stretch (fixed)
            main_layout.setRowStretch(2, 1)  # Vertical splitter: takes all expandable space
            
            # Setup Quick Reference as a dock widget
            self.setup_quickref_dock()
            
            # Setup StatBlock Viewer as a dock widget
            self.setup_statblock_viewer_dock()
        except Exception as e:
            print(f"Error in setup_layout: {e}")
            import traceback
            traceback.print_exc()
            raise
        
    def setup_quickref_dock(self):
        """Setup quick reference dock widget."""
        from ui.quickref.quickref_widget import QuickRefWidget
        
        self.quickref_dock = QDockWidget("Quick Reference", self)
        self.quickref_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        self.quickref_widget = QuickRefWidget()
        self.quickref_dock.setWidget(self.quickref_widget)
        
        # Add dock to right side by default
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.quickref_dock)
        
        # Hide by default
        self.quickref_dock.hide()
    
    def setup_statblock_viewer_dock(self):
        """Setup statblock viewer dock widget."""
        from ui.statblock_viewer.statblock_viewer_widget import StatBlockViewerWidget
        
        self.statblock_viewer_dock = QDockWidget("StatBlock Viewer", self)
        self.statblock_viewer_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        self.statblock_viewer_widget = StatBlockViewerWidget()
        self.statblock_viewer_dock.setWidget(self.statblock_viewer_widget)
        
        # Add dock to right side by default (can be tabbed with quickref)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.statblock_viewer_dock)
        
        # Hide by default
        self.statblock_viewer_dock.hide()
        
    def connect_signals(self):
        """Connect signals and slots."""
        # Connect signal hub to toggle actions
        signal_hub.quickref_toggle.connect(self.on_quickref_toggle)
        
        # Connect tab widget signals to sync tab bars
        if hasattr(self, 'tab_manager') and hasattr(self, 'tab_bar'):
            # Connect the separate tab bar to the tab widget
            self.tab_manager.tab_widget.currentChanged.connect(self._on_tab_changed)
            self.tab_bar.currentChanged.connect(self._on_separate_tab_changed)
            self.tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
            
            # Connect to note signals to sync when tabs are added/removed
            signal_hub.note_saved.connect(self._on_note_saved_sync)
            signal_hub.note_deleted.connect(self._on_note_deleted_sync)
            
            # Use a timer to sync after tab operations (since tab operations might be async)
            from PyQt6.QtCore import QTimer
            self.sync_timer = QTimer()
            self.sync_timer.setSingleShot(True)
            self.sync_timer.timeout.connect(self._sync_tab_bars)
            
            # Monitor tab widget for changes - use a timer to periodically check
            # since QTabWidget doesn't emit signals when tabs are added
            self.tab_sync_timer = QTimer()
            self.tab_sync_timer.timeout.connect(self._check_and_sync_tabs)
            self.tab_sync_timer.start(100)  # Check every 100ms
            
            # Initial sync
            self._sync_tab_bars()

        # Open Knowledge Base at startup if preference is set
        from core.settings import get_open_knowledge_base_at_startup
        if get_open_knowledge_base_at_startup():
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(300, self.open_knowledge_base)
    
    def _check_and_sync_tabs(self):
        """Check if tabs have changed and sync if needed."""
        if hasattr(self, 'tab_manager') and hasattr(self, 'tab_bar'):
            tab_widget = self.tab_manager.tab_widget
            # Check if tab count changed or visibility needs updating
            if self.tab_bar.count() != tab_widget.count() or \
               (tab_widget.count() == 0 and self.tab_bar.isVisible()) or \
               (tab_widget.count() > 0 and not self.tab_bar.isVisible()):
                self._sync_tab_bars()
            elif tab_widget.count() > 0 and self.tab_bar.currentIndex() != tab_widget.currentIndex():
                # Just sync the current index, not full sync
                self.tab_bar.setCurrentIndex(tab_widget.currentIndex())
        
    def toggle_console(self):
        """Toggle console visibility."""
        if self.console.isVisible():
            self.console.hide()
        else:
            self.console.show()
            
    def toggle_quickref(self):
        """Toggle quick reference visibility."""
        visible = not self.quickref_dock.isVisible()
        self.quickref_dock.setVisible(visible)
        signal_hub.quickref_toggle.emit(visible)
        
    def toggle_datamanager(self):
        """Toggle data manager visibility."""
        if self.data_manager.isVisible():
            self.data_manager.hide()
        else:
            self.data_manager.show()
    
    def toggle_statblock_viewer(self):
        """Toggle statblock viewer visibility."""
        visible = not self.statblock_viewer_dock.isVisible()
        self.statblock_viewer_dock.setVisible(visible)
            
    def on_quickref_toggle(self, visible: bool):
        """Handle quick reference toggle signal."""
        self.quickref_dock.setVisible(visible)
        
    def open_dice_roller(self):
        """Open the dice roller dialog."""
        from ui.dialogs.dice_roller_dialog import DiceRollerDialog
        dialog = DiceRollerDialog(self)
        dialog.exec()

    def open_settings(self):
        """Open the settings dialog."""
        from ui.settings.settings import open_settings_dialog
        open_settings_dialog(self)

    def open_knowledge_base(self):
        """Open or show the Knowledge Base window."""
        from ui.knowledgebase.knowledgebase_window import KnowledgeBaseWindow
        from PyQt6.QtCore import Qt
        if not hasattr(self, "kb_window") or self.kb_window is None:
            self.kb_window = KnowledgeBaseWindow(self)
            self.kb_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.kb_window.show()
        self.kb_window.raise_()
        self.kb_window.activateWindow()
    
    def _sync_tab_bars(self):
        """Sync the separate tab bar with the tab widget's tab bar."""
        if not hasattr(self, 'tab_bar') or not hasattr(self, 'tab_manager'):
            return
        
        tab_widget = self.tab_manager.tab_widget
        
        # Hide tab bar if no tabs (welcome screen is showing)  
        if tab_widget.count() == 0:
            self.tab_bar.setVisible(False)
            self.tab_bar_container.setVisible(False)  # Hide container too
            return
        
        # Show tab bar if tabs exist
        self.tab_bar.setVisible(True)
        self.tab_bar_container.setVisible(True)  # Show container too
        
        # Check if tab counts match
        if self.tab_bar.count() != tab_widget.count():
            # Clear the separate tab bar
            while self.tab_bar.count() > 0:
                self.tab_bar.removeTab(0)
            
            # Copy all tabs from the tab widget
            for i in range(tab_widget.count()):
                text = tab_widget.tabText(i)
                self.tab_bar.addTab(text)
        
        # Update tab texts in case they changed
        for i in range(min(self.tab_bar.count(), tab_widget.count())):
            if self.tab_bar.tabText(i) != tab_widget.tabText(i):
                self.tab_bar.setTabText(i, tab_widget.tabText(i))
        
        # Set current tab (only if it changed to avoid recursion)
        tab_widget_index = tab_widget.currentIndex()
        if tab_widget_index >= 0 and self.tab_bar.currentIndex() != tab_widget_index:
            self.tab_bar.setCurrentIndex(tab_widget_index)
    
    def _on_tab_changed(self, index: int):
        """Handle tab change in the tab widget."""
        if hasattr(self, 'tab_bar') and self.tab_bar.count() > index:
            self.tab_bar.setCurrentIndex(index)
    
    def _on_separate_tab_changed(self, index: int):
        """Handle tab change in the separate tab bar."""
        if hasattr(self, 'tab_manager'):
            self.tab_manager.tab_widget.setCurrentIndex(index)
    
    
    def _on_tab_close_requested(self, index: int):
        """Handle tab close request from separate tab bar."""
        if hasattr(self, 'tab_manager'):
            self.tab_manager.tab_widget.tabCloseRequested.emit(index)
    
    def _on_note_saved_sync(self, note_id: int, title: str):
        """Sync tab bars when a note is saved (title might have changed)."""
        self._sync_tab_bars()
    
    def _on_note_deleted_sync(self, note_id: int):
        """Sync tab bars when a note is deleted."""
        self._sync_tab_bars()

