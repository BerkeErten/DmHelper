"""EntityRelation model for linking entities together."""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class EntityRelation(Base):
    """
    Relationships between entities.
    
    Examples:
    - NPC → Note: relation_type="note"
    - Spell → Tag: relation_type="tag"
    - Creature → Location: relation_type="reference"
    - Parent → Child: relation_type="parent"/"child"
    """
    __tablename__ = "entity_relations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    to_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(50), nullable=False)  # "note", "tag", "reference", "parent", "child"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    from_entity = relationship("Entity", foreign_keys=[from_id], back_populates="outgoing_relations")
    to_entity = relationship("Entity", foreign_keys=[to_id], back_populates="incoming_relations")
    
    def __repr__(self):
        return f"<EntityRelation(id={self.id}, from={self.from_id}, to={self.to_id}, type='{self.relation_type}')>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "from_id": self.from_id,
            "to_id": self.to_id,
            "relation_type": self.relation_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

