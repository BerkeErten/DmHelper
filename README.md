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

## Acknowledgments

- **Jump calculator** (method, UI, and logic) – based on [Fexlabs](https://fexlabs.com).

## License

MIT License

