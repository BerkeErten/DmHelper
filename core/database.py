"""Database management with SQLAlchemy."""
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
from core.config import DB_PATH

# Create base class for ORM models
Base = declarative_base()

# Global engine and session maker
_engine = None
_SessionLocal = None


def init_database():
    """Initialize the database connection and create tables."""
    global _engine, _SessionLocal
    
    # Ensure database directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Create engine
    _engine = create_engine(
        f'sqlite:///{DB_PATH}',
        echo=False,  # Set to True for SQL debugging
        connect_args={"check_same_thread": False}  # Needed for SQLite
    )
    
    # Create session factory
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # Import models to register them
    from models import note, session, relation, note_metadata, entity, entity_property, entity_section, entity_relation
    
    # Create all tables (including note_tags association table)
    Base.metadata.create_all(bind=_engine)
    
    # Migrate existing database schema if needed
    migrate_database(_engine)
    
    return _engine


def migrate_database(engine):
    """Migrate existing database schema to ideal schema."""
    inspector = inspect(engine)
    
    # Check if notes table exists
    if 'notes' not in inspector.get_table_names():
        return
    
    existing_columns = {col['name'] for col in inspector.get_columns('notes')}
    
    with engine.begin() as conn:
        # Ensure parent_id exists
        if 'parent_id' not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE notes ADD COLUMN parent_id INTEGER"))
                print("✓ Added 'parent_id' column to notes table")
            except Exception as e:
                print(f"Warning: Could not add 'parent_id' column: {e}")
        
        # Ensure session_id exists
        if 'session_id' not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE notes ADD COLUMN session_id INTEGER"))
                print("✓ Added 'session_id' column to notes table")
            except Exception as e:
                print(f"Warning: Could not add 'session_id' column: {e}")
        
        # Create tags table if it doesn't exist
        if 'tags' not in inspector.get_table_names():
            conn.execute(text("""
                CREATE TABLE tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    color VARCHAR(7)
                )
            """))
            print("✓ Created 'tags' table")
        
        # Create note_tags table if it doesn't exist
        if 'note_tags' not in inspector.get_table_names():
            conn.execute(text("""
                CREATE TABLE note_tags (
                    note_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (note_id, tag_id),
                    FOREIGN KEY (note_id) REFERENCES notes(id),
                    FOREIGN KEY (tag_id) REFERENCES tags(id)
                )
            """))
            print("✓ Created 'note_tags' association table")
        
        # Create relations table (replaces references table)
        if 'relations' not in inspector.get_table_names():
            conn.execute(text("""
                CREATE TABLE relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_note_id INTEGER NOT NULL,
                    to_note_id INTEGER NOT NULL,
                    relation_type VARCHAR(50) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (from_note_id) REFERENCES notes(id),
                    FOREIGN KEY (to_note_id) REFERENCES notes(id)
                )
            """))
            print("✓ Created 'relations' table")
        
        # Create note_metadata table (optional, future-proof)
        if 'note_metadata' not in inspector.get_table_names():
            conn.execute(text("""
                CREATE TABLE note_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id INTEGER NOT NULL,
                    key VARCHAR(100) NOT NULL,
                    value TEXT,
                    FOREIGN KEY (note_id) REFERENCES notes(id)
                )
            """))
            print("✓ Created 'note_metadata' table")


def get_session():
    """Get a database session."""
    if _SessionLocal is None:
        init_database()
    return _SessionLocal()


def close_database():
    """Close the database connection."""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None


class DatabaseManager:
    """Context manager for database sessions."""
    
    def __enter__(self):
        """Enter context - create session."""
        self.session = get_session()
        return self.session
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - close session."""
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
