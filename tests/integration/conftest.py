"""Integration test configuration and fixtures."""
import pytest
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / 'backend'
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Load test environment
env_file = Path(__file__).parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

# Set test database URL
os.environ['TESTING'] = 'True'


@pytest.fixture(scope='session')
def app():
    """Create Flask app for integration tests (required by pytest-flask)."""
    from app import app as flask_app
    
    flask_app.config['TESTING'] = True
    
    return flask_app


@pytest.fixture(scope='session')
def app_context():
    """Create Flask app context for integration tests."""
    from app import app
    
    app.config['TESTING'] = True
    
    return app


@pytest.fixture
def test_client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def client(app):
    """Create Flask test client (alias for test_client)."""
    return app.test_client()


@pytest.fixture
def app_runner(app):
    """Create Flask CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json',
    }


@pytest.fixture
def sample_estate_id():
    """Sample estate ID for testing."""
    return 'test-estate-12345678-1234-1234-1234-123456789012'


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return 'test-user-12345678-1234-1234-1234-123456789012'
