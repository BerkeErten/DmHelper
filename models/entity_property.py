"""EntityProperty model for storing dynamic key-value attributes."""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base
import json


class EntityProperty(Base):
    """
    Flexible key-value storage for entity attributes.
    
    Examples:
    - AC: key="ac", value="19"
    - Hit Points: key="hp", value="256 (19d12 + 133)"
    - Speed: key="speed", value='["40 ft", "fly 80 ft"]' (JSON array)
    """
    __tablename__ = "entity_properties"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)  # Can be string or JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entity = relationship("Entity", back_populates="properties")
    
    def __repr__(self):
        return f"<EntityProperty(id={self.id}, entity_id={self.entity_id}, key='{self.key}', value='{self.value[:50] if self.value else None}...')>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_value_as_json(self):
        """Parse value as JSON if possible, otherwise return as string."""
        if not self.value:
            return None
        try:
            return json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            return self.value
    
    def set_value_from_json(self, data):
        """Set value from JSON-serializable data."""
        if isinstance(data, str):
            self.value = data
        else:
            self.value = json.dumps(data)

