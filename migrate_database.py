#!/usr/bin/env python3
"""
Manual database migration script to add snapshot column to existing SQLite database.
"""

import sqlite3
import os
from datetime import datetime

def get_current_snapshot() -> str:
    """Get the current snapshot in YYYYH1 or YYYYH2 format."""
    now = datetime.now()
    year = now.year
    # H1 is first half (Jan-Jun), H2 is second half (Jul-Dec)
    half = "H1" if now.month <= 6 else "H2"
    return f"{year}{half}"

def migrate_database(db_path: str = "ranking.db"):
    """Add snapshot column to existing database."""
    print(f"Looking for database at: {os.path.abspath(db_path)}")
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Nothing to migrate.")
        print("Available files:")
        for file in os.listdir("."):
            if file.endswith(".db"):
                print(f"  - {file}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if snapshot column already exists
        cursor.execute("PRAGMA table_info(scores)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'snapshot' in columns:
            print("Snapshot column already exists. No migration needed.")
            conn.close()
            return
        
        print("Adding snapshot column to scores table...")
        
        # Add snapshot column with default value
        current_snapshot = get_current_snapshot()
        cursor.execute(f"ALTER TABLE scores ADD COLUMN snapshot VARCHAR(10) DEFAULT '{current_snapshot}'")
        
        # Update all existing records with the current snapshot
        cursor.execute(f"UPDATE scores SET snapshot = '{current_snapshot}' WHERE snapshot IS NULL")
        
        conn.commit()
        print(f"Migration completed successfully. All existing records set to snapshot: {current_snapshot}")
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM scores WHERE snapshot IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"Verified: {count} records have snapshot values")
        
        conn.close()
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_database()
