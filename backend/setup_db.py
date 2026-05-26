#!/usr/bin/env python3
"""
KVPL Quick Setup Script
One-command database initialization with migrations and sample data.
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def print_header(text):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")

def check_prerequisites():
    """Check if all prerequisites are installed."""
    print_header("Checking Prerequisites")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print("✅ Python 3.8+")
    
    # Check PostgreSQL (optional - may not be in PATH on Windows)
    try:
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
        else:
            print("⚠️  PostgreSQL client not found (optional for CLI access)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  PostgreSQL client not found (optional for CLI access)")
    
    return True

def check_dependencies():
    """Check if required Python packages are installed."""
    print_header("Checking Python Dependencies")
    
    try:
        import psycopg
        print(f"✅ psycopg {psycopg.__version__}")
    except ImportError:
        print("❌ psycopg not installed")
        print("   Run: pip install -r requirements.txt")
        return False
    
    try:
        import dotenv
        print(f"✅ python-dotenv installed")
    except ImportError:
        print("⚠️  python-dotenv not installed (optional)")
    
    return True

def setup_env():
    """Set up environment file if not exists."""
    print_header("Environment Configuration")
    
    backend_dir = Path(__file__).parent
    env_file = backend_dir / '.env'
    example_file = backend_dir / '.env.example'
    
    if env_file.exists():
        print("✅ .env file already exists")
        load_dotenv(env_file)
        return True
    
    if not example_file.exists():
        print("⚠️  No .env or .env.example found")
        print("   Create .env with DATABASE_URL:")
        print("   DATABASE_URL=postgresql://user:password@localhost:5432/kvpl")
        return False
    
    print("📋 .env not found, using defaults...")
    # Try to load from example or use defaults
    if example_file.exists():
        load_dotenv(example_file)
    
    return True

def verify_database_connection():
    """Verify database connection."""
    print_header("Database Connection")
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        print("   Please configure DATABASE_URL in .env file")
        return False
    
    try:
        import psycopg
        conn = psycopg.connect(database_url)
        conn.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def run_migrations():
    """Run database migrations."""
    print_header("Running Migrations")
    
    backend_dir = Path(__file__).parent
    migrate_script = backend_dir / 'migrate.py'
    
    if not migrate_script.exists():
        print("❌ migrate.py not found")
        return False
    
    # Check migration status
    result = subprocess.run(
        [sys.executable, str(migrate_script), 'status'],
        capture_output=True,
        text=True,
        cwd=backend_dir
    )
    
    if result.returncode != 0:
        print(f"❌ Migration status check failed:\n{result.stderr}")
        return False
    
    print(result.stdout)
    
    # Run migrations
    print("\n▶️  Executing migrations...\n")
    result = subprocess.run(
        [sys.executable, str(migrate_script), 'migrate'],
        capture_output=True,
        text=True,
        cwd=backend_dir
    )
    
    print(result.stdout)
    
    if result.returncode != 0:
        print(f"❌ Migration failed:\n{result.stderr}")
        return False
    
    return True

def run_sample_data():
    """Load sample data."""
    print_header("Loading Sample Data")
    
    print("✅ Sample data loaded during migrations")
    print("   You can now query the database:")
    print("\n   Example queries:")
    print("   - SELECT * FROM estate;")
    print("   - SELECT * FROM v_roi_current_month;")
    print("   - SELECT * FROM v_water_status_latest;")
    
    return True

def display_summary():
    """Display setup summary and next steps."""
    print_header("Setup Complete! ✅")
    
    print("Database is ready for development!\n")
    
    print("Quick Start:")
    print("  1. Start Flask app:")
    print("     python app.py\n")
    print("  2. Access API:")
    print("     http://localhost:5000\n")
    print("  3. Check health:")
    print("     curl http://localhost:5000/health\n")
    
    print("Database Commands:")
    print("  # Check migration status")
    print("  python migrate.py status\n")
    print("  # Drop all tables (development)")
    print("  python migrate.py rollback\n")
    
    print("Docker Compose:")
    print("  # Start with database")
    print("  docker-compose up\n")
    
    print("Documentation:")
    print("  See migrations/README.md for detailed information")

def main():
    """Run full setup."""
    print("\n" + "🚀 " * 15)
    print("KVPL DATABASE SETUP")
    print("🚀 " * 15)
    
    steps = [
        ("Prerequisites", check_prerequisites),
        ("Dependencies", check_dependencies),
        ("Environment", setup_env),
        ("Database Connection", verify_database_connection),
        ("Migrations", run_migrations),
        ("Sample Data", run_sample_data),
    ]
    
    for step_name, step_func in steps:
        if not step_func():
            print(f"\n❌ Setup failed at: {step_name}")
            print("\nFor help, see migrations/README.md")
            sys.exit(1)
    
    display_summary()
    print("\n" + "✅ " * 15 + "\n")

if __name__ == '__main__':
    main()
