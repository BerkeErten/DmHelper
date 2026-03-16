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


_COMBAT_TRACKER_KEYS_DEFAULT = ["hp", "ac"]


def get_combat_tracker_property_keys() -> list[str]:
    """Return ordered list of property keys to show in combat tracker (e.g. hp, ac, luck, doom)."""
    s = QSettings(_ORG, _APP)
    val = s.value("combat_tracker_property_keys")
    if val is None:
        return list(_COMBAT_TRACKER_KEYS_DEFAULT)
    if isinstance(val, list):
        return [str(k).strip().lower() for k in val if str(k).strip()]
    # stored as comma-separated string
    raw = str(val).strip()
    if not raw:
        return list(_COMBAT_TRACKER_KEYS_DEFAULT)
    return [k.strip().lower() for k in raw.split(",") if k.strip()]


def set_combat_tracker_property_keys(keys: list[str]) -> None:
    """Set the ordered list of property keys to show in combat tracker."""
    s = QSettings(_ORG, _APP)
    s.setValue("combat_tracker_property_keys", ",".join(k.strip().lower() for k in keys if k.strip()))


def get_combat_tracker_show_mark_defeated() -> bool:
    """Return whether to show 'Mark as defeated' in the combat tracker context menu."""
    s = QSettings(_ORG, _APP)
    val = s.value("combat_tracker_show_mark_defeated", True)
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("1", "true", "yes")


def set_combat_tracker_show_mark_defeated(value: bool) -> None:
    """Set whether to show 'Mark as defeated' in the combat tracker context menu."""
    s = QSettings(_ORG, _APP)
    s.setValue("combat_tracker_show_mark_defeated", value)


def get_data_manager_show_hover_add_button() -> bool:
    """Return whether to show the '+' button on row hover in the Data Manager tree."""
    s = QSettings(_ORG, _APP)
    val = s.value("data_manager_show_hover_add_button", True)
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("1", "true", "yes")


def set_data_manager_show_hover_add_button(value: bool) -> None:
    """Set whether to show the '+' button on row hover in the Data Manager tree."""
    s = QSettings(_ORG, _APP)
    s.setValue("data_manager_show_hover_add_button", value)
