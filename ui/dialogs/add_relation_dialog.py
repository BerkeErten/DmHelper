"""Add relation dialog: pick a target (entity, note, session) to link to the current note or entity."""
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QFrame, QLabel, QStyledItemDelegate, QStyleOptionViewItem, QStyle,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPalette
from sqlalchemy import or_, and_
from sqlalchemy.exc import IntegrityError
from core.database import DatabaseManager
from core.events import signal_hub
from models.entity import Entity
from models.note import Note
from models.session import Session
from models.entity_note_link import EntityNoteLink
from models.entity_session_link import EntitySessionLink
from models.entity_relation import EntityRelation
from models.relation import Relation

# Entity type order for list (no category headers, but ordered by category)
ENTITY_TYPE_ORDER = ("creature", "npc", "location", "item", "spell", "statblock", "note")


class HoverShadowDelegate(QStyledItemDelegate):
    """Paint a drop shadow behind the item when hovered (no blue/gray selection)."""
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        if opt.state & QStyle.StateFlag.State_MouseOver:
            r = opt.rect.adjusted(4, 2, -4, -2)
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            # Layered shadow for softer, more visible effect
            for dy, alpha in [(4, 35), (3, 50), (2, 70)]:
                shadow_rect = r.translated(dy, dy)
                painter.setBrush(QBrush(QColor(0, 0, 0, alpha)))
                painter.drawRoundedRect(shadow_rect, 6, 6)
            # Light raised background so the item pops
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
            painter.drawRoundedRect(r, 6, 6)
            painter.restore()
        super().paint(painter, option, index)


class PickedLinkDelegate(QStyledItemDelegate):
    """For the Linked list: shadow on hover + blue underlined text like a link."""
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        if opt.state & QStyle.StateFlag.State_MouseOver:
            r = opt.rect.adjusted(4, 2, -4, -2)
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            for dy, alpha in [(4, 35), (3, 50), (2, 70)]:
                shadow_rect = r.translated(dy, dy)
                painter.setBrush(QBrush(QColor(0, 0, 0, alpha)))
                painter.drawRoundedRect(shadow_rect, 6, 6)
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
            painter.drawRoundedRect(r, 6, 6)
            painter.restore()
            # Link style: blue and underlined
            opt.palette.setColor(QPalette.ColorRole.Text, QColor("#5DADE2"))
            opt.font.setUnderline(True)
        super().paint(painter, opt, index)


class AddRelationPopupWidget(QWidget):
    """
    Reusable widget: list of relation options above a search bar.
    Can be embedded in a QMenu (QWidgetAction) or in AddRelationDialog.
    Emits closed_requested() when a relation is created so the menu/dialog can close.
    """
    closed_requested = pyqtSignal()

    def __init__(self, source_kind: str, source_id, parent=None):
        super().__init__(parent)
        self.source_kind = source_kind
        self.source_id = source_id
        self._all_options = []
        self._setup_ui()
        self.load_picked()
        self.load_options()

    def _setup_ui(self):
        self.setMinimumSize(320, 340)
        self.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #4c4c4c;
                border-radius: 4px;
                padding: 4px;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item { padding: 6px 8px; background-color: transparent; }
            QListWidget::item:selected { background-color: transparent; }
            QLineEdit {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #4c4c4c;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #5DADE2; }
            QFrame#pickedFrame {
                background-color: #252525;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Picked section (above search bar) – visible only when there are linked items
        self.picked_frame = QFrame()
        self.picked_frame.setObjectName("pickedFrame")
        picked_layout = QVBoxLayout(self.picked_frame)
        picked_layout.setContentsMargins(6, 6, 6, 6)
        picked_layout.setSpacing(4)
        self.picked_label = QLabel("Linked")
        self.picked_label.setStyleSheet("color: #888; font-size: 11px;")
        picked_layout.addWidget(self.picked_label)
        self.picked_list = QListWidget()
        self.picked_list.setMaximumHeight(80)
        self.picked_list.setMouseTracking(True)
        self.picked_list.setItemDelegate(PickedLinkDelegate(self.picked_list))
        self.picked_list.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; color: #e0e0e0; font-size: 12px; }
            QListWidget::item { padding: 4px 4px; background-color: transparent; }
        """)
        self.picked_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.picked_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.picked_list.customContextMenuRequested.connect(self._on_picked_right_clicked)
        self.picked_list.itemDoubleClicked.connect(self._on_picked_double_clicked)
        picked_layout.addWidget(self.picked_list)
        layout.addWidget(self.picked_frame)
        self.picked_frame.setVisible(False)

        # Search bar (middle)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter options...")
        self.search_edit.textChanged.connect(self.apply_filter)
        layout.addWidget(self.search_edit)

        # Relation options list (below search bar)
        self.list_widget = QListWidget()
        self.list_widget.setMouseTracking(True)
        self.list_widget.setItemDelegate(HoverShadowDelegate(self.list_widget))
        self.list_widget.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, stretch=1)

    def _get_linked_ids(self):
        """Return set of (kind, id) for already-linked targets so we exclude them from options."""
        linked = set()
        try:
            with DatabaseManager() as db:
                if self.source_kind == "note":
                    for link in db.query(EntityNoteLink).filter(EntityNoteLink.note_id == self.source_id).all():
                        linked.add(("entity", link.entity_id))
                    for r in db.query(Relation).filter(Relation.from_note_id == self.source_id).all():
                        linked.add(("note", r.to_note_id))
                    for r in db.query(Relation).filter(Relation.to_note_id == self.source_id).all():
                        linked.add(("note", r.from_note_id))
                else:
                    for r in db.query(EntityRelation).filter(EntityRelation.from_id == self.source_id).all():
                        linked.add(("entity", r.to_id))
                    for r in db.query(EntityRelation).filter(EntityRelation.to_id == self.source_id).all():
                        linked.add(("entity", r.from_id))
                    for link in db.query(EntityNoteLink).filter(EntityNoteLink.entity_id == self.source_id).all():
                        linked.add(("note", link.note_id))
                    for link in db.query(EntitySessionLink).filter(EntitySessionLink.entity_id == self.source_id).all():
                        linked.add(("session", link.session_id))
        except Exception:
            pass
        return linked

    def load_options(self):
        """Load entities, notes, sessions ordered by category. Exclude source and already-linked."""
        self._all_options = []
        linked = self._get_linked_ids()
        try:
            with DatabaseManager() as db:
                entities = db.query(Entity).order_by(Entity.name).all()
                by_type = {}
                for e in entities:
                    if e.type not in by_type:
                        by_type[e.type] = []
                    by_type[e.type].append(e)
                for entity_type in ENTITY_TYPE_ORDER:
                    for e in by_type.get(entity_type, []):
                        if self.source_kind == "entity" and e.id == self.source_id:
                            continue
                        if ("entity", e.id) in linked:
                            continue
                        self._all_options.append({"kind": "entity", "id": e.id, "name": e.name or "(unnamed)"})
                for entity_type, entity_list in sorted(by_type.items()):
                    if entity_type in ENTITY_TYPE_ORDER:
                        continue
                    for e in entity_list:
                        if self.source_kind == "entity" and e.id == self.source_id:
                            continue
                        if ("entity", e.id) in linked:
                            continue
                        self._all_options.append({"kind": "entity", "id": e.id, "name": e.name or "(unnamed)"})
                notes = db.query(Note).order_by(Note.title).all()
                for n in notes:
                    if self.source_kind == "note" and n.id == self.source_id:
                        continue
                    if ("note", n.id) in linked:
                        continue
                    self._all_options.append({"kind": "note", "id": n.id, "name": n.title or "(untitled)"})
                if self.source_kind == "entity":
                    sessions = db.query(Session).order_by(Session.name).all()
                    for s in sessions:
                        if ("session", s.id) in linked:
                            continue
                        self._all_options.append({"kind": "session", "id": s.id, "name": s.name or "(unnamed)"})
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load options: {e}")
            return
        self.apply_filter()

    def load_picked(self):
        """Load already-linked items with type labels and (kind, id) for remove; show only if any exist."""
        entries = []  # list of (type_label, name, kind, target_id)
        try:
            with DatabaseManager() as db:
                if self.source_kind == "note":
                    links = db.query(EntityNoteLink).filter(EntityNoteLink.note_id == self.source_id).all()
                    for link in links:
                        e = db.query(Entity).filter(Entity.id == link.entity_id).first()
                        if e:
                            entries.append(("Entity", e.name or "(unnamed)", "entity", link.entity_id))
                    out = db.query(Relation).filter(Relation.from_note_id == self.source_id).all()
                    for r in out:
                        n = db.query(Note).filter(Note.id == r.to_note_id).first()
                        if n:
                            entries.append(("Note", n.title or "(untitled)", "note", r.to_note_id))
                    inc = db.query(Relation).filter(Relation.to_note_id == self.source_id).all()
                    for r in inc:
                        n = db.query(Note).filter(Note.id == r.from_note_id).first()
                        if n:
                            entries.append(("Note", n.title or "(untitled)", "note", r.from_note_id))
                else:
                    out = db.query(EntityRelation).filter(EntityRelation.from_id == self.source_id).all()
                    for r in out:
                        e = db.query(Entity).filter(Entity.id == r.to_id).first()
                        if e:
                            entries.append(("Entity", e.name or "(unnamed)", "entity", r.to_id))
                    inc = db.query(EntityRelation).filter(EntityRelation.to_id == self.source_id).all()
                    for r in inc:
                        e = db.query(Entity).filter(Entity.id == r.from_id).first()
                        if e:
                            entries.append(("Entity", e.name or "(unnamed)", "entity", r.from_id))
                    links = db.query(EntityNoteLink).filter(EntityNoteLink.entity_id == self.source_id).all()
                    for link in links:
                        n = db.query(Note).filter(Note.id == link.note_id).first()
                        if n:
                            entries.append(("Note", n.title or "(untitled)", "note", link.note_id))
                    sess_links = db.query(EntitySessionLink).filter(EntitySessionLink.entity_id == self.source_id).all()
                    for link in sess_links:
                        s = db.query(Session).filter(Session.id == link.session_id).first()
                        if s:
                            entries.append(("Session", s.name or "(unnamed)", "session", link.session_id))
        except Exception:
            pass
        if entries:
            self.picked_list.clear()
            for type_label, name, kind, target_id in entries:
                item = QListWidgetItem(f"{type_label}: {name}")
                item.setData(Qt.ItemDataRole.UserRole, {"kind": kind, "id": target_id})
                self.picked_list.addItem(item)
            self.picked_frame.setVisible(True)
        else:
            self.picked_list.clear()
            self.picked_frame.setVisible(False)

    def apply_filter(self):
        search = self.search_edit.text().strip().lower()
        linked = self._get_linked_ids()
        self.list_widget.clear()
        for opt in self._all_options:
            if (opt["kind"], opt["id"]) in linked:
                continue
            if search and search not in (opt["name"] or "").lower():
                continue
            item = QListWidgetItem(opt["name"])
            item.setData(Qt.ItemDataRole.UserRole, opt)
            self.list_widget.addItem(item)

    def _on_picked_right_clicked(self, pos: QPoint):
        """Right-click: remove the linked item under the cursor."""
        item = self.picked_list.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data or "kind" not in data or "id" not in data:
            return
        if self._remove_relation(data["kind"], data["id"]):
            self.load_picked()
            self.load_options()

    def _on_picked_double_clicked(self, item: QListWidgetItem):
        """Double-click: open the related tab (note or entity; session has no tab)."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data or "kind" not in data or "id" not in data:
            return
        kind, target_id = data["kind"], data["id"]
        if kind == "note":
            signal_hub.note_open_requested.emit(int(target_id))
        elif kind == "entity":
            signal_hub.stat_block_open_requested.emit(str(target_id))
        # Session has no tab to open; double-click does nothing for sessions

    def _on_item_clicked(self, item: QListWidgetItem):
        opt = item.data(Qt.ItemDataRole.UserRole)
        if not opt:
            return
        if self._create_relation(opt["kind"], opt["id"]):
            self.load_picked()
            self.load_options()

    def _remove_relation(self, target_kind: str, target_id) -> bool:
        """Remove the link to the given target. Returns True if removed."""
        try:
            with DatabaseManager() as db:
                if self.source_kind == "note" and target_kind == "entity":
                    db.query(EntityNoteLink).filter(
                        EntityNoteLink.note_id == self.source_id,
                        EntityNoteLink.entity_id == target_id,
                    ).delete()
                elif self.source_kind == "note" and target_kind == "note":
                    db.query(Relation).filter(
                        or_(
                            and_(Relation.from_note_id == self.source_id, Relation.to_note_id == target_id),
                            and_(Relation.from_note_id == target_id, Relation.to_note_id == self.source_id),
                        )
                    ).delete(synchronize_session=False)
                elif self.source_kind == "entity" and target_kind == "entity":
                    db.query(EntityRelation).filter(
                        or_(
                            and_(EntityRelation.from_id == self.source_id, EntityRelation.to_id == target_id),
                            and_(EntityRelation.from_id == target_id, EntityRelation.to_id == self.source_id),
                        )
                    ).delete(synchronize_session=False)
                elif self.source_kind == "entity" and target_kind == "note":
                    db.query(EntityNoteLink).filter(
                        EntityNoteLink.entity_id == self.source_id,
                        EntityNoteLink.note_id == target_id,
                    ).delete()
                elif self.source_kind == "entity" and target_kind == "session":
                    db.query(EntitySessionLink).filter(
                        EntitySessionLink.entity_id == self.source_id,
                        EntitySessionLink.session_id == target_id,
                    ).delete()
                else:
                    return False
                db.commit()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not remove relation: {e}")
            return False

    def _create_relation(self, target_kind: str, target_id) -> bool:
        try:
            with DatabaseManager() as db:
                if self.source_kind == "note" and target_kind == "entity":
                    db.add(EntityNoteLink(entity_id=target_id, note_id=self.source_id))
                elif self.source_kind == "note" and target_kind == "note":
                    db.add(Relation(from_note_id=self.source_id, to_note_id=target_id, relation_type="reference"))
                elif self.source_kind == "entity" and target_kind == "entity":
                    if target_id != self.source_id:
                        db.add(EntityRelation(from_id=self.source_id, to_id=target_id, relation_type="reference"))
                elif self.source_kind == "entity" and target_kind == "note":
                    db.add(EntityNoteLink(entity_id=self.source_id, note_id=target_id))
                elif self.source_kind == "entity" and target_kind == "session":
                    db.add(EntitySessionLink(entity_id=self.source_id, session_id=target_id))
                else:
                    return False
                db.commit()
            return True
        except IntegrityError:
            QMessageBox.information(self, "Already linked", "This relation already exists.")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create relation: {e}")
            return False


class AddRelationDialog(QDialog):
    """Dialog to pick a target and create a relation (uses AddRelationPopupWidget)."""

    def __init__(self, source_kind: str, source_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add relation")
        self.setMinimumSize(360, 400)
        self.setStyleSheet("QDialog { background-color: #2b2b2b; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._content = AddRelationPopupWidget(source_kind, source_id, self)
        layout.addWidget(self._content)
        self._content.closed_requested.connect(self.accept)
