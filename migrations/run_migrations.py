# migrations/run_migrations.py

import sys
import os
from pathlib import Path
import logging
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.crud_operations import DatabaseCRUD
from migrations.v012_update_user_profile import MigrationV012

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        self.db = DatabaseCRUD(db_path)
    
    def run_migration_v012(self) -> bool:
        """Run v012 migration"""
        migration = MigrationV012(self.db)
        return migration.up()
    
    def rollback_migration_v012(self) -> bool:
        """Rollback v012 migration"""
        migration = MigrationV012(self.db)
        return migration.down()
    
    def run_all_migrations(self) -> bool:
        """Run all migrations in order"""
        migrations = [
            self.run_migration_v012,
            # Add more migrations here as they are created
        ]
        
        success = True
        for migration in migrations:
            if not migration():
                success = False
                break
        
        if success:
            logger.info("✅ All migrations completed successfully!")
        else:
            logger.error("❌ Some migrations failed!")
        
        return success
    
    def get_migration_status(self) -> dict:
        """Get status of all migrations"""
        status = {
            'v012_update_user_profile': {
                'table_social_links': self.db.table_exists('social_links'),
                'table_activity_log': self.db.table_exists('user_activity_log'),
                'view_profile': self.db.table_exists('v_user_profile'),
                'columns_added': [
                    col for col in ['avatar_url', 'bio', 'location', 'website']
                    if self.db.column_exists('users', col)
                ]
            }
        }
        return status


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Database Migration Manager")
    parser.add_argument(
        "command",
        choices=["up", "down", "status", "all"],
        help="Migration command: up (run v012), down (rollback v012), status (check status), all (run all migrations)"
    )
    parser.add_argument(
        "--db-path",
        default="data/tender_system.db",
        help="Path to database file"
    )
    
    args = parser.parse_args()
    
    manager = MigrationManager(args.db_path)
    
    if args.command == "up":
        logger.info("▶️ Running migration v012...")
        if manager.run_migration_v012():
            logger.info("✅ Migration completed successfully!")
        else:
            logger.error("❌ Migration failed!")
            sys.exit(1)
    
    elif args.command == "down":
        logger.info("◀️ Rolling back migration v012...")
        if manager.rollback_migration_v012():
            logger.info("✅ Rollback completed successfully!")
        else:
            logger.error("❌ Rollback failed!")
            sys.exit(1)
    
    elif args.command == "status":
        status = manager.get_migration_status()
        logger.info("📊 Migration Status:")
        for name, info in status.items():
            logger.info(f"  {name}:")
            for key, value in info.items():
                logger.info(f"    - {key}: {value}")
    
    elif args.command == "all":
        logger.info("▶️ Running all migrations...")
        if manager.run_all_migrations():
            logger.info("✅ All migrations completed successfully!")
        else:
            logger.error("❌ Some migrations failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()