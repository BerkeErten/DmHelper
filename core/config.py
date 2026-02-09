"""Configuration settings for DM Helper."""
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
STYLES_DIR = ASSETS_DIR / "styles"
DATA_DIR = ASSETS_DIR / "data"

# Database settings
DB_PATH = PROJECT_ROOT / "dm_helper.db"

# Application settings
APP_NAME = "DM Helper"
APP_VERSION = "0.1.0"
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800

# UI Layout settings
TOPBAR_HEIGHT = 60
CONSOLE_MIN_HEIGHT = 150
DATAMANAGER_MIN_WIDTH = 250
QUICKREF_MIN_WIDTH = 300

# Theme settings
DEFAULT_THEME = "dark"

