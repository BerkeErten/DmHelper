"""EntitySection model for storing structured stat block sections."""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class EntitySection(Base):
    """
    Structured sections for stat blocks (traits, actions, legendary actions, lair actions, description, etc.).
    
    Each section corresponds to a collapsible UI block.
    - section_type: "traits", "actions", "legendary_actions", "lair_actions", "description", etc.
    - sort_order: determines display order
    - content: markdown or JSON formatted text
    """
    __tablename__ = "entity_sections"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    section_type = Column(String(50), nullable=False)  # "traits", "actions", "legendary_actions", etc.
    sort_order = Column(Integer, default=0, nullable=False)
    content = Column(Text, nullable=True)  # Markdown or JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entity = relationship("Entity", back_populates="sections")
    
    def __repr__(self):
        return f"<EntitySection(id={self.id}, entity_id={self.entity_id}, type='{self.section_type}', order={self.sort_order})>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "section_type": self.section_type,
            "sort_order": self.sort_order,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

