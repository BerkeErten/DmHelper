"""Reference model for quick reference data."""
from sqlalchemy import Column, Integer, String, Text, Enum
from datetime import datetime
from core.database import Base
import enum


class ReferenceType(enum.Enum):
    """Types of references."""
    SPELL = "spell"
    CONDITION = "condition"
    RULE = "rule"
    ITEM = "item"
    MONSTER = "monster"
    FEAT = "feat"
    CLASS_FEATURE = "class_feature"
    OTHER = "other"


class Reference(Base):
    """Model for quick reference entries."""
    __tablename__ = "references"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    type = Column(Enum(ReferenceType), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(100), nullable=True)  # e.g., "PHB", "DMG"
    tags = Column(Text, nullable=True)  # Comma-separated tags
    
    def __repr__(self):
        return f"<Reference(id={self.id}, title='{self.title}', type='{self.type}')>"
        
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value if isinstance(self.type, ReferenceType) else self.type,
            "content": self.content,
            "source": self.source,
            "tags": self.tags.split(',') if self.tags else []
        }

