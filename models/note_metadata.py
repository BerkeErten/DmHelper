"""Note metadata model for storing additional per-type fields."""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class NoteMetadata(Base):
    """Model for storing additional metadata fields for notes (future-proof)."""
    __tablename__ = "note_metadata"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    key = Column(String(100), nullable=False)  # e.g., "HP", "AC", "level", "faction"
    value = Column(Text, nullable=True)  # Flexible value storage
    
    # Relationships
    note = relationship("Note", back_populates="metadata_items")
    
    def __repr__(self):
        return f"<NoteMetadata(id={self.id}, note_id={self.note_id}, key='{self.key}')>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "note_id": self.note_id,
            "key": self.key,
            "value": self.value
        }

