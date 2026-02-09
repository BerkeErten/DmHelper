"""Relation model for linking notes together."""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class Relation(Base):
    """Model for linking notes together with relation types."""
    __tablename__ = "relations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    to_note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    relation_type = Column(String(50), nullable=False)  # e.g., "lives_in", "member_of", "found_at", "appears_in"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    from_note = relationship("Note", foreign_keys=[from_note_id], back_populates="outgoing_relations")
    to_note = relationship("Note", foreign_keys=[to_note_id], back_populates="incoming_relations")
    
    def __repr__(self):
        return f"<Relation(id={self.id}, from={self.from_note_id}, to={self.to_note_id}, type='{self.relation_type}')>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "from_note_id": self.from_note_id,
            "to_note_id": self.to_note_id,
            "relation_type": self.relation_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

