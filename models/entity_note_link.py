"""EntityNoteLink model for linking entities to notes (cross-domain references)."""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class EntityNoteLink(Base):
    """
    Many-to-many link between Entity and Note.
    Allows statblocks/entities to be linked to notes and vice versa.
    """
    __tablename__ = "entity_note_links"
    __table_args__ = (UniqueConstraint("entity_id", "note_id", name="uq_entity_note_link"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(50), nullable=True, default="reference")  # e.g. "references", "appears_in"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="entity_note_links")
    note = relationship("Note", back_populates="entity_note_links")

    def __repr__(self):
        return f"<EntityNoteLink(id={self.id}, entity_id={self.entity_id}, note_id={self.note_id}, type='{self.relation_type}')>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "note_id": self.note_id,
            "relation_type": self.relation_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
