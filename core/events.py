"""Custom signals and event hub for decoupled communication."""
from PyQt6.QtCore import QObject, pyqtSignal


class SignalHub(QObject):
    """Central signal hub for application-wide communication."""
    
    # Tab management signals
    tab_created = pyqtSignal(str)  # tab_id
    tab_closed = pyqtSignal(str)   # tab_id
    tab_switched = pyqtSignal(str)  # tab_id
    note_content_set = pyqtSignal(str)  # html_content for newly created note
    note_saved = pyqtSignal(int, str)  # note_id, note_title
    note_open_requested = pyqtSignal(int)  # note_id - request to open note by ID
    note_deleted = pyqtSignal(int)  # note_id - note was deleted from database
    
    # Console signals
    console_command = pyqtSignal(str)  # command text
    console_output = pyqtSignal(str)   # output text
    
    # Data manager signals
    data_selected = pyqtSignal(str, object)  # data_type, data_object
    data_dragged = pyqtSignal(object)        # data_object
    
    # Quick reference signals
    quickref_toggle = pyqtSignal(bool)  # show/hide
    quickref_search = pyqtSignal(str)   # search query
    
    # Database signals
    data_saved = pyqtSignal(str, object)    # entity_type, entity
    data_deleted = pyqtSignal(str, str)     # entity_type, entity_id
    
    # Stat block editor signals
    stat_block_open_requested = pyqtSignal(str)
    
    # Stat block viewer signals
    add_to_stat_block_list = pyqtSignal(dict)  # item_data: {"type": "entity"/"note", "id": "...", "name": "..."}  # entity_id - request to open stat block editor
    
    # Theme signals
    theme_changed = pyqtSignal(str)  # theme_name


# Global signal hub instance
signal_hub = SignalHub()

