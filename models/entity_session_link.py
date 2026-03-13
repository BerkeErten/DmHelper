"""EntitySessionLink model for linking entities to sessions (cross-domain references)."""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class EntitySessionLink(Base):
    """
    Many-to-many link between Entity and Session.
    e.g. creatures/entities that appear in or are referenced by a session.
    """
    __tablename__ = "entity_session_links"
    __table_args__ = (UniqueConstraint("entity_id", "session_id", name="uq_entity_session_link"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="entity_session_links")
    session = relationship("Session", back_populates="entity_session_links")

    def __repr__(self):
        return f"<EntitySessionLink(id={self.id}, entity_id={self.entity_id}, session_id={self.session_id}, type='{self.relation_type}')>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "session_id": self.session_id,
            "relation_type": self.relation_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
