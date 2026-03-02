"""Entity model - Generic base for all game objects."""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base
import uuid


class Entity(Base):
    """
    Generic entity model for all game objects (Creature, Item, Spell, Note, NPC, Location, etc.).
    
    All game objects are stored as entities with:
    - id: unique identifier (UUID as string)
    - type: entity type (e.g., "creature", "item", "note", "spell", "npc", "location")
    - name: entity name
    - created_at: creation timestamp
    - updated_at: last update timestamp
    
    Additional attributes are stored via EntityProperty (key-value pairs).
    Structured content (traits, actions, etc.) is stored via EntitySection.
    Relationships are stored via EntityRelation.
    """
    __tablename__ = "entities"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(50), nullable=False)  # "creature", "item", "note", "spell", "npc", "location", etc.
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    properties = relationship("EntityProperty", back_populates="entity", cascade="all, delete-orphan")
    sections = relationship("EntitySection", back_populates="entity", cascade="all, delete-orphan", order_by="EntitySection.sort_order")
    outgoing_relations = relationship("EntityRelation", foreign_keys="[EntityRelation.from_id]", back_populates="from_entity", cascade="all, delete-orphan")
    incoming_relations = relationship("EntityRelation", foreign_keys="[EntityRelation.to_id]", back_populates="to_entity", cascade="all, delete-orphan")
    entity_note_links = relationship("EntityNoteLink", back_populates="entity", cascade="all, delete-orphan")
    entity_session_links = relationship("EntitySessionLink", back_populates="entity", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Entity(id={self.id}, name='{self.name}', type='{self.type}')>"
        
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_property(self, key: str, default=None):
        """Get a property value by key."""
        for prop in self.properties:
            if prop.key == key:
                return prop.value
        return default
    
    def set_property(self, key: str, value: str, session=None):
        """Set a property value. If session is provided, commits to DB."""
        # Find existing property
        for prop in self.properties:
            if prop.key == key:
                prop.value = value
                if session:
                    session.add(prop)
                return prop
        
        # Create new property (import here to avoid circular import)
        from models.entity_property import EntityProperty
        new_prop = EntityProperty(entity_id=self.id, key=key, value=value)
        self.properties.append(new_prop)
        if session:
            session.add(new_prop)
        return new_prop
    
    def get_section(self, section_type: str):
        """Get a section by type."""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None
    
    def get_sections_by_type(self, section_type: str):
        """Get all sections of a given type."""
        return [s for s in self.sections if s.section_type == section_type]

