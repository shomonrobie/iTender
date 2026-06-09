# fix_boq_table_direct.py
from database.db_manager import DatabaseManager
import sqlite3
from datetime import datetime

db = DatabaseManager()
conn = db.get_connection()
cursor = conn.cursor()

print("Checking boq_generation_history table...")

# Check existing columns
cursor.execute("PRAGMA table_info(boq_generation_history)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Existing columns: {columns}")

# Add missing columns (without DEFAULT)
if 'created_at' not in columns:
    print("Adding created_at column...")
    cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN created_at TIMESTAMP")
    # Update existing rows
    cursor.execute("UPDATE boq_generation_history SET created_at = generated_at WHERE created_at IS NULL")
    print("✅ Added created_at")

if 'updated_at' not in columns:
    print("Adding updated_at column...")
    cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN updated_at TIMESTAMP")
    cursor.execute("UPDATE boq_generation_history SET updated_at = generated_at WHERE updated_at IS NULL")
    print("✅ Added updated_at")

if 'is_locked' not in columns:
    print("Adding is_locked column...")
    cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN is_locked BOOLEAN DEFAULT 0")
    print("✅ Added is_locked")

if 'locked_at' not in columns:
    print("Adding locked_at column...")
    cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN locked_at TIMESTAMP")
    print("✅ Added locked_at")

if 'locked_by' not in columns:
    print("Adding locked_by column...")
    cursor.execute("ALTER TABLE boq_generation_history ADD COLUMN locked_by INTEGER")
    print("✅ Added locked_by")

conn.commit()

# Verify
cursor.execute("PRAGMA table_info(boq_generation_history)")
updated_columns = [col[1] for col in cursor.fetchall()]
print(f"\nUpdated columns: {updated_columns}")

conn.close()
print("\n✅ BOQ table schema updated successfully!")