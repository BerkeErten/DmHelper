"""Main entry point for DM Helper application."""
import sys
from PyQt6.QtCore import Qt
from core.app import create_app
from core.database import init_database
from ui.main_window import MainWindow
from core.settings import (
    get_start_fullscreen_at_startup,
    get_start_borderless_fullscreen_at_startup,
)


def main():
    """Initialize and run the application."""
    try:
        # Initialize database
        init_database()
            
        # Create application
        app = create_app()
        
        # Create and show main window
        window = MainWindow()
        if get_start_fullscreen_at_startup():
            if get_start_borderless_fullscreen_at_startup():
                window.showMaximized()
            else:
                window.showFullScreen()
        else:
            window.show()
        
        # Run event loop
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

