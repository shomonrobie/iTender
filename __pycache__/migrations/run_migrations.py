# migrations/run_migrations.py

import sqlite3
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

class MigrationManager:
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()
    
    def get_applied_migrations(self):
        """Get list of already applied migrations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_migrations ORDER BY id")
        applied = [row[0] for row in cursor.fetchall()]
        conn.close()
        return set(applied)
    
    def mark_migration_applied(self, version, name, success=True):
        """Mark a migration as applied"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO schema_migrations (version, name, success)
            VALUES (?, ?, ?)
        """, (version, name, success))
        conn.commit()
        conn.close()
    
    def run_migration(self, migration_file):
        """Run a single migration"""
        try:
            print(f"Running migration: {migration_file.__name__}")
            migration_file.up(self.db_path)
            self.mark_migration_applied(migration_file.version, migration_file.__name__)
            print(f"✅ Successfully applied {migration_file.version}")
            return True
        except Exception as e:
            print(f"❌ Failed to apply {migration_file.version}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_migrations(self):
        """Run all pending migrations"""
        import v001_initial_schema
        import v002_add_subscription_permissions
        import v003_add_rate_chapters_sections
        import v004_add_company_subscriptions
        
        migrations = [
            v001_initial_schema,
            v002_add_subscription_permissions,
            v003_add_rate_chapters_sections,
            v004_add_company_subscriptions,
        ]
        
        applied = self.get_applied_migrations()
        
        for migration in migrations:
            if migration.version not in applied:
                if not self.run_migration(migration):
                    print(f"Stopping migrations due to failure at {migration.version}")
                    return False
        
        print("\n✅ All migrations completed successfully!")
        return True

if __name__ == "__main__":
    manager = MigrationManager()
    manager.run_all_migrations()