"""Session model for grouping campaign sessions."""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class Session(Base):
    """Model for D&D sessions."""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    campaign_name = Column(String(255), nullable=True)
    session_number = Column(Integer, nullable=True)
    date_played = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    notes = relationship("Note", back_populates="session", cascade="all, delete-orphan")
    # Note: Entity model removed - using Note model with types instead
    
    def __repr__(self):
        return f"<Session(id={self.id}, name='{self.name}')>"
        
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "campaign_name": self.campaign_name,
            "session_number": self.session_number,
            "date_played": self.date_played.isoformat() if self.date_played else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

