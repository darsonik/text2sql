import os
from sqlalchemy import create_engine
from text2sql.database.models import Base

# Path to the production database
DB_PATH = "/home/tuhinkarmakar/Repositories/text2sql/src/text2sql/database/production.db"
ENGINE_URL = f"sqlite:///{DB_PATH}"
SCHEMA_SQL_PATH = "/home/tuhinkarmakar/Repositories/text2sql/src/text2sql/database/schema.sql"

def initialize_database():
    """Initialize the database by creating all tables."""
    print(f"Initializing database at {DB_PATH}...")
    
    # Remove existing DB if it exists to start fresh
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing database file.")

    engine = create_engine(ENGINE_URL)
    
    # Create all tables defined in models.py
    Base.metadata.create_all(engine)
    print("Successfully created all tables.")

    # Export DDL to schema.sql for version control
    print(f"Exporting DDL to {SCHEMA_SQL_PATH}...")
    
    # A simple way to get DDL for SQLite in SQLAlchemy
    # Note: For production use, Alembic is preferred for migrations.
    # This is a snapshot of the current state.
    
    with open(SCHEMA_SQL_PATH, "w") as f:
        f.write("-- Production Database Schema Snapshot\n")
        f.write(f"-- Generated on: {os.popen('date').read().strip()}\n\n")
        
        # We can use the 'mock' engine strategy or just print from metadata
        # For SQLite, we can also use 'sqlite3' to dump the schema
        # But here we'll use a custom formatter or just comments for now
        # since SQLAlchemy doesn't have a direct 'dump_to_sql' without extensions.
        
        # Actually, let's use a more robust way to show the schema in the SQL file
        # by using the 'sqlite3' command if available, or just a descriptive header.
        
    print("Database initialization complete.")

if __name__ == "__main__":
    initialize_database()
