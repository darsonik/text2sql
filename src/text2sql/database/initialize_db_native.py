import sqlite3
import os

DB_PATH = "/home/tuhinkarmakar/Repositories/text2sql/src/text2sql/database/production.db"
SCHEMA_PATH = "/home/tuhinkarmakar/Repositories/text2sql/src/text2sql/database/schema.sql"
SEED_PATH = "/home/tuhinkarmakar/Repositories/text2sql/src/text2sql/database/seed_data.sql"

def initialize_native():
    """Initialize and seed the database using only the standard library."""
    print(f"Initializing database at {DB_PATH} using native sqlite3...")
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing database.")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Read and execute schema
        print(f"Executing {SCHEMA_PATH}...")
        with open(SCHEMA_PATH, 'r') as f:
            schema_sql = f.read()
            cursor.executescript(schema_sql)

        # Read and execute seed data
        print(f"Executing {SEED_PATH}...")
        with open(SEED_PATH, 'r') as f:
            seed_sql = f.read()
            cursor.executescript(seed_sql)

        conn.commit()
        print("Database initialized and seeded successfully.")
        
        # Verify a table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Created tables: {[t[0] for t in tables]}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    initialize_native()
