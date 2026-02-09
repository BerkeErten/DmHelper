"""Note model for storing DM notes."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

# Association table for many-to-many tags relationship
note_tags = Table(
    'note_tags',
    Base.metadata,
    Column('note_id', Integer, ForeignKey('notes.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)


class Tag(Base):
    """Tag model for categorizing notes."""
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(7), nullable=True)  # Hex color code
    
    # Relationships
    notes = relationship("Note", secondary=note_tags, back_populates="tags")
    
    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"


class Note(Base):
    """OOP Note model for storing DM notes with hierarchical structure."""
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # HTML or Markdown content
    parent_id = Column(Integer, ForeignKey("notes.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="notes")
    parent = relationship("Note", remote_side=[id], back_populates="children")
    children = relationship("Note", back_populates="parent", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=note_tags, back_populates="notes")
    outgoing_relations = relationship("Relation", foreign_keys="Relation.from_note_id", back_populates="from_note", cascade="all, delete-orphan")
    incoming_relations = relationship("Relation", foreign_keys="Relation.to_note_id", back_populates="to_note", cascade="all, delete-orphan")
    metadata_items = relationship("NoteMetadata", back_populates="note", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}')>"
        
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "parent_id": self.parent_id,
            "tags": [tag.name for tag in self.tags],
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

