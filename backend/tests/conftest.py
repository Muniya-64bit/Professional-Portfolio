"""
Pytest configuration and shared fixtures.

All database calls are mocked so tests run without a live PostgreSQL instance.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# ── Ensure the backend package is importable ──────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Provide required env vars BEFORE importing any backend module
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')


# ── App fixture ───────────────────────────────────────────────────────────────
@pytest.fixture(scope='session')
def app():
    """Create Flask test application once per session."""
    # Patch DB connection at import time to prevent real connections
    with patch('auth.get_db_connection', return_value=None):
        from app import app as flask_app

    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    with app.test_client() as c:
        yield c


# ── DB mock helpers ───────────────────────────────────────────────────────────
def make_cursor(rows=None, description=None):
    """Return a mock psycopg cursor."""
    cur = MagicMock()
    cur.fetchone.return_value = rows[0] if rows else None
    cur.fetchall.return_value = rows or []
    cur.description = description or []
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    return cur


def make_conn(cursor=None):
    """Return a mock psycopg connection with a cursor."""
    conn = MagicMock()
    cur = cursor or make_cursor()
    conn.cursor.return_value = cur
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    # context-manager style: `with conn.cursor() as cur:`
    conn.cursor.return_value.__enter__ = lambda s: s
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


# ── JWT helper ────────────────────────────────────────────────────────────────
@pytest.fixture(scope='session')
def admin_token():
    """Generate a valid admin JWT for use in protected route tests."""
    from auth import generate_token
    return generate_token(
        user_id='00000000-0000-0000-0000-000000000001',
        email='admin@test.com',
        role='admin',
        estate_id=None,
    )


@pytest.fixture(scope='session')
def manager_token():
    """Generate a valid manager JWT scoped to a fake estate."""
    from auth import generate_token
    return generate_token(
        user_id='00000000-0000-0000-0000-000000000002',
        email='manager@test.com',
        role='manager',
        estate_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    )


@pytest.fixture(scope='session')
def estate_manager_token():
    """Generate a valid estate_manager JWT."""
    from auth import generate_token
    return generate_token(
        user_id='00000000-0000-0000-0000-000000000003',
        email='em@test.com',
        role='estate_manager',
        estate_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    )


def auth_header(token):
    """Return an Authorization header dict."""
    return {'Authorization': f'Bearer {token}'}
