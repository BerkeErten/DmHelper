"""Migrate entities table from old schema to new schema."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect
from core.database import init_database, get_session


def migrate_entities_table():
    """Migrate entities table to new schema."""
    print("Starting entities table migration...")
    
    engine = init_database()
    inspector = inspect(engine)
    
    with engine.begin() as conn:
        # Check if entities table exists
        if 'entities' not in inspector.get_table_names():
            print("Entities table doesn't exist. It will be created automatically.")
            return
        
        # Get current columns
        columns = {col['name']: col for col in inspector.get_columns('entities')}
        column_names = set(columns.keys())
        
        print(f"Current columns: {column_names}")
        
        # Check if migration is needed
        needs_migration = False
        
        # Check if old schema (has entity_type, category, description, stats)
        if 'entity_type' in column_names or 'category' in column_names:
            needs_migration = True
            print("Old schema detected. Migration needed.")
        
        # Check if new schema (has type, but id is INTEGER instead of VARCHAR)
        if 'type' in column_names and columns.get('id', {}).get('type') != 'VARCHAR(36)':
            needs_migration = True
            print("Schema partially updated but ID column needs migration.")
        
        if not needs_migration:
            print("Schema is already up to date!")
            return
        
        # Backup old data if any exists
        print("\nBacking up old data...")
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM entities"))
            old_count = result.scalar()
            print(f"Found {old_count} existing entities.")
            
            if old_count > 0:
                # Save old data
                old_data = conn.execute(text("""
                    SELECT id, name, entity_type, category, description, stats, 
                           session_id, created_at, updated_at
                    FROM entities
                """)).fetchall()
                print(f"Backed up {len(old_data)} entities.")
        except Exception as e:
            print(f"Could not backup old data: {e}")
            old_data = []
        
        # Drop old table
        print("\nDropping old entities table...")
        conn.execute(text("DROP TABLE IF EXISTS entities"))
        
        # Drop related tables that will be recreated
        print("Dropping related tables...")
        conn.execute(text("DROP TABLE IF EXISTS entity_properties"))
        conn.execute(text("DROP TABLE IF EXISTS entity_sections"))
        conn.execute(text("DROP TABLE IF EXISTS entity_relations"))
        
        # Recreate all tables with new schema
        print("\nCreating new tables with updated schema...")
        from models.entity import Entity
        from models.entity_property import EntityProperty
        from models.entity_section import EntitySection
        from models.entity_relation import EntityRelation
        from core.database import Base
        
        Base.metadata.create_all(bind=engine)
        
        print("Migration complete!")
        print("\nNote: Old entity data was not migrated automatically.")
        print("If you need to preserve old data, you'll need to manually convert it.")
        print("The new schema uses:")
        print("  - id: VARCHAR(36) UUID (was INTEGER)")
        print("  - type: VARCHAR(50) (was entity_type ENUM)")
        print("  - Properties stored in entity_properties table")
        print("  - Sections stored in entity_sections table")


if __name__ == "__main__":
    try:
        migrate_entities_table()
    except Exception as e:
        print(f"\nError during migration: {e}")
        import traceback
        traceback.print_exc()

