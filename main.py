"""Main entry point for DM Helper application."""
import sys
from core.app import create_app
from core.database import init_database
from ui.main_window import MainWindow


def main():
    """Initialize and run the application."""
    try:
        # Initialize database
        init_database()
            
        # Create application
        app = create_app()
        
        # Create and show main window
        window = MainWindow()
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

