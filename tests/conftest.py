"""Base configuration and fixtures for all tests."""
import os
import sys
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

# Load test environment
env_file = Path(__file__).parent.parent / '.env.test'
if env_file.exists():
    load_dotenv(env_file)
else:
    # Use .env but with test database
    load_dotenv(Path(__file__).parent.parent / '.env')
    os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', '').replace('kvpl_db', 'kvpl_db_test')

os.environ.setdefault('SECRET_KEY', 'test-secret-key-do-not-use-in-production')
os.environ.setdefault('DATABASE_URL', os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost/kvpl_db_test'))

@pytest.fixture(scope='session')
def backend_path_fixture():
    """Return path to backend directory."""
    return Path(__file__).parent.parent / 'backend'


@pytest.fixture(scope='session')
def test_config():
    """Test configuration."""
    return {
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-do-not-use-in-production',
        'DATABASE_URL': os.getenv('DATABASE_URL'),
    }
