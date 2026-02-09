"""Application settings persisted via QSettings."""
from PyQt6.QtCore import QSettings

_ORG = "DmHelper"
_APP = "DM Helper"


def get_open_knowledge_base_at_startup() -> bool:
    """Return whether to open the Knowledge Base window at startup."""
    s = QSettings(_ORG, _APP)
    val = s.value("open_knowledge_base_at_startup", False)
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("1", "true", "yes")


def set_open_knowledge_base_at_startup(value: bool) -> None:
    """Set whether to open the Knowledge Base window at startup."""
    s = QSettings(_ORG, _APP)
    s.setValue("open_knowledge_base_at_startup", value)
