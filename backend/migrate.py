#!/usr/bin/env python3
"""
KVPL Database Migration Manager
Handles running SQL migrations against PostgreSQL database.
"""

import os
import sys
import psycopg
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, database_url=None):
        """Initialize migration manager with database connection."""
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL not found. Set it via environment variable or .env file"
            )
        self.migrations_dir = Path(__file__).parent / 'migrations'
    
    def get_connection(self):
        """Create and return a database connection."""
        try:
            conn = psycopg.connect(self.database_url)
            return conn
        except psycopg.OperationalError as e:
            print(f"❌ Failed to connect to database: {e}")
            sys.exit(1)
    
    def initialize_migrations_table(self, conn):
        """Create migrations tracking table if it doesn't exist."""
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_file VARCHAR(255) NOT NULL UNIQUE,
                    executed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    duration_ms INTEGER
                )
            """)
            conn.commit()
    
    def get_executed_migrations(self, conn):
        """Get list of already executed migrations."""
        with conn.cursor() as cur:
            cur.execute("SELECT migration_file FROM schema_migrations ORDER BY executed_at")
            return {row[0] for row in cur.fetchall()}
    
    def get_pending_migrations(self, conn):
        """Get list of pending migrations."""
        executed = self.get_executed_migrations(conn)
        
        # Get all SQL files in migrations directory that match migration pattern (###_*.sql)
        migration_files = sorted([
            f.name for f in self.migrations_dir.glob('*.sql')
            if f.name.endswith('.sql') and f.name[0].isdigit()
        ])
        
        return [f for f in migration_files if f not in executed]
    
    def run_migration(self, conn, migration_file):
        """Execute a single migration file."""
        migration_path = self.migrations_dir / migration_file
        
        if not migration_path.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        try:
            with open(migration_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            print(f"▶️  Running: {migration_file}")
            
            # Execute migration
            start_time = datetime.now()
            with conn.cursor() as cur:
                cur.execute(sql_content)
            conn.commit()
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Record migration
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO schema_migrations (migration_file, duration_ms) VALUES (%s, %s)",
                    (migration_file, duration_ms)
                )
            conn.commit()
            
            print(f"✅ Completed: {migration_file} ({duration_ms}ms)")
            return True
            
        except Exception as e:
            print(f"❌ Error executing {migration_file}: {e}")
            conn.rollback()
            return False
    
    def migrate(self, target_migration=None):
        """Run pending migrations."""
        conn = self.get_connection()
        try:
            self.initialize_migrations_table(conn)
            
            pending = self.get_pending_migrations(conn)
            
            if not pending:
                print("✅ Database is up to date!")
                return True
            
            print(f"📋 Found {len(pending)} pending migration(s):\n")
            for mig in pending:
                print(f"   - {mig}")
            print()
            
            success = True
            for migration_file in pending:
                if not self.run_migration(conn, migration_file):
                    success = False
                    break
                
                if target_migration and migration_file == target_migration:
                    break
            
            print()
            if success:
                print("✅ All migrations completed successfully!")
            else:
                print("❌ Migration failed!")
            
            return success
            
        finally:
            conn.close()
    
    def status(self):
        """Display migration status."""
        conn = self.get_connection()
        try:
            self.initialize_migrations_table(conn)
            
            executed = self.get_executed_migrations(conn)
            pending = self.get_pending_migrations(conn)
            
            print("\n📊 Migration Status")
            print("=" * 50)
            
            if executed:
                print(f"\n✅ Executed ({len(executed)}):")
                for mig in sorted(executed):
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT executed_at, duration_ms FROM schema_migrations WHERE migration_file = %s",
                            (mig,)
                        )
                        row = cur.fetchone()
                        if row:
                            print(f"   ✓ {mig} ({row[1]}ms at {row[0]})")
            
            if pending:
                print(f"\n⏳ Pending ({len(pending)}):")
                for mig in pending:
                    print(f"   ⋯ {mig}")
            else:
                print("\n✅ No pending migrations!")
            
            print()
            
        finally:
            conn.close()
    
    def rollback(self):
        """WARNING: Completely drop all tables (for development only)."""
        conn = self.get_connection()
        try:
            print("⚠️  WARNING: This will drop ALL tables and reset migrations!")
            response = input("Are you absolutely sure? Type 'YES' to confirm: ")
            
            if response != 'YES':
                print("Rollback cancelled.")
                return False
            
            with conn.cursor() as cur:
                # Drop all views first
                cur.execute("""
                    SELECT string_agg('DROP VIEW IF EXISTS ' || viewname || ' CASCADE', '; ')
                    FROM pg_views
                    WHERE schemaname = 'public'
                """)
                drop_views = cur.fetchone()[0]
                if drop_views:
                    cur.execute(drop_views)
                
                # Drop all tables
                cur.execute("""
                    SELECT string_agg('DROP TABLE IF EXISTS ' || tablename || ' CASCADE', '; ')
                    FROM pg_tables
                    WHERE schemaname = 'public'
                """)
                drop_tables = cur.fetchone()[0]
                if drop_tables:
                    cur.execute(drop_tables)
                
                # Reset migrations table
                cur.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")
            
            conn.commit()
            print("✅ All tables and views dropped successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Rollback error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


def main():
    """CLI entry point."""
    manager = MigrationManager()
    
    if len(sys.argv) < 2:
        print("KVPL Database Migration Manager\n")
        print("Usage:")
        print("  python migrate.py migrate [--target MIGRATION_FILE]  Run pending migrations")
        print("  python migrate.py status                            Show migration status")
        print("  python migrate.py rollback                          Drop all tables (dev only)")
        print("\nExample:")
        print("  python migrate.py migrate")
        print("  python migrate.py status")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'migrate':
        target = None
        if len(sys.argv) > 3 and sys.argv[2] == '--target':
            target = sys.argv[3]
        manager.migrate(target)
    
    elif command == 'status':
        manager.status()
    
    elif command == 'rollback':
        manager.rollback()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
