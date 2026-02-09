# DM Helper

A comprehensive Dungeon Master helper application built with PyQt6.

## Features

### Phase 1 - Foundation ✅ COMPLETE
- ✅ Multi-pane layout with splitters
- ✅ Top bar with session info and quick actions
- ✅ Tab manager for multiple notes
- ✅ Data manager for organizing NPCs, locations, items, and monsters
- ✅ Console for command input/output
- ✅ Quick Reference dock (toggle with Ctrl+R)
- ✅ Menu system with keyboard shortcuts
- ✅ Dark theme

### Phase 2 - Module Scaffolding ✅ COMPLETE
- ✅ **Dice Roller System** - Full-featured dice rolling with UI dialog
  - Standard dice notation (XdY+Z)
  - Advantage/Disadvantage rolls
  - Ability score generation (4d6 drop lowest)
  - Quick roll buttons (d4, d6, d8, d10, d12, d20, d100)
  - Roll history
- ✅ **Enhanced Console** - Functional DM commands
  - `roll XdY+Z` - Roll any dice expression
  - `adv` - Roll with advantage
  - `dis` - Roll with disadvantage
  - `stat` - Roll ability score
  - `help` - Show all commands
  - `clear` - Clear console
- ✅ **Rich Text Note Editor** - Full formatting toolbar
  - Font family and size selection
  - Bold, italic, underline formatting
  - Text alignment (left, center, right)
  - Bullet and numbered lists
  - Real-time format updates
- ✅ **Data Manager CRUD** - Complete entity management
  - Create new entities (NPCs, Locations, Items, Monsters)
  - Edit existing entities (double-click or Edit button)
  - Delete entities with confirmation
  - Right-click context menus
  - Search/filter functionality
- ✅ **Drag & Drop** - Drag entities from Data Manager into notes
- ✅ **Database Layer** - SQLAlchemy ORM with models
  - Note model (for storing notes with HTML content)
  - Session model (for campaign sessions)
  - Entity model (for NPCs, locations, items, monsters)
  - Reference model (for quick reference data)
  - Automatic table creation

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:

```bash
pip install -r requirements.txt
```

This will install:
- PyQt6 (GUI framework)
- SQLAlchemy (Database ORM)

## Running the Application

```bash
python main.py
```

## Keyboard Shortcuts

### File Operations
- `Ctrl+N` - New Session
- `Ctrl+O` - Open Session
- `Ctrl+S` - Save Session
- `Ctrl+Q` - Exit

### View Controls
- `Ctrl+R` - Toggle Quick Reference
- `Ctrl+D` - Toggle Data Manager
- `Ctrl+\`` - Toggle Console

### Tools
- `Ctrl+Shift+D` - Open Dice Roller

### Text Formatting (in notes)
- `Ctrl+B` - Bold
- `Ctrl+I` - Italic
- `Ctrl+U` - Underline

## Project Structure

```
dm_helper/
├── main.py                 # Entry point
├── core/                   # Core functionality
│   ├── app.py             # Application initialization
│   ├── config.py          # Configuration settings
│   └── events.py          # Signal hub for communication
├── ui/                    # User interface
│   ├── main_window.py     # Main window layout
│   ├── topbar/            # Top bar widget
│   ├── tabs/              # Tab manager
│   ├── console/           # Console widget
│   ├── datamanager/       # Data manager widget
│   └── quickref/          # Quick reference widget
└── assets/                # Assets (icons, styles, data)
```

## Development Roadmap

- [x] **Phase 1: Foundation** - Basic window layout ✅
- [x] **Phase 2: Module Scaffolding** - Enhanced functionality ✅
- [ ] **Phase 3: Data Persistence** - Save/load sessions and entities
- [ ] **Phase 4: Quick Reference System** - D&D rules integration
- [ ] **Phase 5: Polish & Extensibility** - Themes, plugins, advanced features

## How to Use

### Creating Notes
1. Click the **"+ New Note"** button in the top bar
2. Use the formatting toolbar to style your text
3. Drag entities from the Data Manager into your notes
4. Close tabs you don't need (except the last one)

### Managing Entities
1. Click the **"+"** button in the Data Manager to add entities
2. **Double-click** an entity to edit it
3. **Right-click** for context menu (edit/delete options)
4. Use the **Search box** to filter entities
5. **Drag** entities into your notes for quick reference

### Rolling Dice
1. Click the **"🎲 Roll Dice"** button or press `Ctrl+Shift+D`
2. Use quick buttons (d20, d6, etc.) or enter custom expressions
3. Roll with advantage/disadvantage
4. Generate ability scores (4d6 drop lowest)
5. View roll history in the dialog

### Console Commands
1. Click in the console input at the bottom
2. Type commands and press Enter
3. Use `help` to see all available commands
4. Examples:
   - `roll 2d20+5` - Roll 2d20 with +5 modifier
   - `adv` - Roll d20 with advantage
   - `stat` - Generate an ability score

## Debugging Guide

This section helps you debug the application when things go wrong.

### Running in Debug Mode

#### Basic Debug Run
```bash
python main.py
```
The application prints initialization messages to the console:
- Database initialization status
- Application creation status
- Main window creation status

#### Enable SQL Query Logging
To see all SQL queries being executed, edit `core/database.py`:
```python
_engine = create_engine(
    f'sqlite:///{DB_PATH}',
    echo=True,  # Change from False to True
    connect_args={"check_same_thread": False}
)
```

#### Python Debugger (pdb)
Add breakpoints in your code:
```python
import pdb; pdb.set_trace()
```
Or use the built-in `breakpoint()` function (Python 3.7+):
```python
breakpoint()  # Execution will pause here
```

### Database Debugging

#### Database Location
The SQLite database is stored at:
```
dm_helper.db
```
Located in the project root directory (same level as `main.py`).

#### Inspect Database
You can inspect the database using SQLite tools:
```bash
# Using sqlite3 command line
sqlite3 dm_helper.db

# Then run SQL queries:
.tables                    # List all tables
.schema notes              # Show table structure
SELECT * FROM notes;       # View all notes
SELECT * FROM entities;    # View all entities
```

#### Database Schema
Key tables:
- `notes` - Stores note content and metadata
- `sessions` - Campaign sessions
- `entities` - NPCs, locations, items, monsters
- `entity_properties` - Properties of entities
- `entity_sections` - Sections within entities
- `entity_relations` - Relationships between entities
- `tags` - Tag definitions
- `note_tags` - Note-tag associations
- `relations` - Note-to-note relationships
- `note_metadata` - Additional note metadata

#### Reset Database
⚠️ **Warning: This will delete all data!**
```bash
# Delete the database file
rm dm_helper.db  # Linux/Mac
del dm_helper.db  # Windows

# Or rename it to backup
mv dm_helper.db dm_helper.db.backup  # Linux/Mac
ren dm_helper.db dm_helper.db.backup  # Windows
```
The database will be recreated automatically on next run.

### Common Debugging Scenarios

#### 1. Application Won't Start
**Symptoms:** App crashes immediately or shows error dialog

**Debug Steps:**
1. Check console output for error messages
2. Verify Python version: `python --version` (needs 3.8+)
3. Verify dependencies: `pip install -r requirements.txt`
4. Check if database file is corrupted (try deleting `dm_helper.db`)
5. Look for import errors in the traceback

**Common Issues:**
- Missing PyQt6: `pip install PyQt6`
- Missing SQLAlchemy: `pip install SQLAlchemy`
- Database locked: Close other instances of the app

#### 2. UI Components Not Showing
**Symptoms:** Window appears but panels are missing or empty

**Debug Steps:**
1. Check console for widget initialization errors
2. Verify all UI files exist in `ui/` directory
3. Check if database has required data
4. Look for exceptions in the console output

#### 3. Database Errors
**Symptoms:** "No such table" or "Database locked" errors

**Debug Steps:**
1. Check if `dm_helper.db` exists in project root
2. Verify database schema matches models (check `models/` directory)
3. Enable SQL logging (see above) to see what queries are failing
4. Check for database migrations in `core/database.py`

#### 4. Drag & Drop Not Working
**Symptoms:** Can't drag entities from Data Manager to notes

**Debug Steps:**
1. Verify MIME types are registered correctly
2. Check console for drag/drop event errors
3. Ensure both source and target widgets are properly initialized

#### 5. Notes Not Saving
**Symptoms:** Notes disappear after closing app

**Debug Steps:**
1. Enable SQL logging to see if INSERT queries are executed
2. Check database directly with SQLite tools
3. Verify session is being committed (check `core/database.py`)
4. Look for exceptions during save operations

### IDE Debugging Setup

#### VS Code
1. Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: DM Helper",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```
2. Set breakpoints by clicking left of line numbers
3. Press F5 to start debugging

#### PyCharm
1. Right-click `main.py` → "Debug 'main'"
2. Set breakpoints by clicking left of line numbers
3. Use debug toolbar to step through code

### Testing

#### Run Structure Tests
```bash
python test_app.py
```
This verifies:
- All required files exist
- All modules can be imported
- Application structure is correct

#### Manual Testing Checklist
- [ ] Application starts without errors
- [ ] Database initializes correctly
- [ ] Main window displays all panels
- [ ] Can create new notes
- [ ] Can create/edit/delete entities
- [ ] Dice roller works
- [ ] Console commands work
- [ ] Drag & drop works
- [ ] Data persists after restart

### Logging

The application uses `print()` statements for logging. To add more detailed logging:

1. Import logging module:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. Use logger instead of print:
```python
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Enable SQL logging if database-related
3. Use Python debugger to step through code
4. Check database directly with SQLite tools
5. Review the traceback for specific error locations

### Project Structure Reference

```
DmHelper/
├── main.py                    # Entry point - start here
├── core/                      # Core functionality
│   ├── app.py                # Application initialization
│   ├── config.py             # Configuration (paths, settings)
│   ├── database.py           # Database setup & migrations
│   ├── events.py             # Signal hub for communication
│   ├── dice_roller.py        # Dice rolling logic
│   └── markdown_parser.py    # Markdown parsing
├── models/                    # Database models (SQLAlchemy)
│   ├── note.py               # Note model
│   ├── session.py            # Session model
│   ├── entity.py             # Entity model (NPCs, etc.)
│   └── ...
├── ui/                        # User interface components
│   ├── main_window.py        # Main window layout
│   ├── topbar/               # Top bar widget
│   ├── tabs/                 # Tab manager & editors
│   ├── console/              # Console widget
│   ├── datamanager/          # Data manager widget
│   ├── quickref/             # Quick reference widget
│   ├── statblock_viewer/     # Stat block viewer
│   └── dialogs/              # Dialog windows
├── assets/                    # Assets (data files, etc.)
├── scripts/                   # Utility scripts
└── dm_helper.db              # SQLite database (created on first run)
```

## License

MIT License

