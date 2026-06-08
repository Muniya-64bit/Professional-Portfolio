"""
Integration tests for Flask app routes in app.py.
All DB calls are mocked — no real database needed.
"""
import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')

from tests.conftest import auth_header


# ═════════════════════════════════════════════════════════════════════════════
# Basic / health routes (no auth)
# ═════════════════════════════════════════════════════════════════════════════

class TestHomeRoute:
    def test_returns_200(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_response_contains_message(self, client):
        data = resp = client.get('/').get_json()
        assert 'message' in data
        assert data['message'] == 'KVPL API'

    def test_response_contains_version(self, client):
        data = client.get('/').get_json()
        assert 'version' in data


class TestHealthRoute:
    def test_returns_200(self, client):
        resp = client.get('/health')
        assert resp.status_code == 200

    def test_status_ok(self, client):
        data = client.get('/health').get_json()
        assert data['status'] == 'ok'


# ═════════════════════════════════════════════════════════════════════════════
# Public estates endpoint
# ═════════════════════════════════════════════════════════════════════════════

class TestPublicEstates:
    def test_returns_200_with_estates(self, client):
        conn = MagicMock()
        cur = MagicMock()
        import uuid
        cur.fetchall.return_value = [
            (uuid.uuid4(), 'Estate Alpha'),
            (uuid.uuid4(), 'Estate Beta'),
        ]
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)

        with patch('auth.get_db_connection', return_value=conn):
            resp = client.get('/api/estates/public')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_db_failure_returns_503(self, client):
        with patch('auth.get_db_connection', return_value=None):
            resp = client.get('/api/estates/public')
        assert resp.status_code == 503


# ═════════════════════════════════════════════════════════════════════════════
# Auth — Signup endpoint
# ═════════════════════════════════════════════════════════════════════════════

class TestSignupEndpoint:
    @pytest.fixture(autouse=True)
    def clear_rate_limits(self):
        """Reset the in-memory rate limit store before every signup test."""
        import auth
        auth._rate_limit_store.clear()
        yield
        auth._rate_limit_store.clear()

    def test_missing_body_returns_400(self, client):
        resp = client.post('/api/auth/signup', data='', content_type='application/json')
        assert resp.status_code == 400

    def test_missing_email_returns_400(self, client):
        resp = client.post('/api/auth/signup', json={
            'password': 'Secure@123',
            'full_name': 'Alice',
        })
        assert resp.status_code == 400

    def test_missing_password_returns_400(self, client):
        resp = client.post('/api/auth/signup', json={
            'email': 'alice@test.com',
            'full_name': 'Alice',
        })
        assert resp.status_code == 400

    def test_missing_full_name_returns_400(self, client):
        resp = client.post('/api/auth/signup', json={
            'email': 'alice@test.com',
            'password': 'Secure@123',
        })
        assert resp.status_code == 400

    def test_invalid_email_format_returns_400(self, client):
        resp = client.post('/api/auth/signup', json={
            'email': 'not-an-email',
            'password': 'Secure@123',
            'full_name': 'Alice',
        })
        assert resp.status_code == 400

    def test_weak_password_returns_400(self, client):
        resp = client.post('/api/auth/signup', json={
            'email': 'alice@test.com',
            'password': 'weak',
            'full_name': 'Alice',
        })
        assert resp.status_code == 400

    def test_invalid_role_returns_400(self, client):
        resp = client.post('/api/auth/signup', json={
            'email': 'alice@test.com',
            'password': 'Secure@123',
            'full_name': 'Alice',
            'role': 'superadmin',
        })
        assert resp.status_code == 400

    def test_manager_without_estate_id_returns_400(self, client):
        resp = client.post('/api/auth/signup', json={
            'email': 'alice@test.com',
            'password': 'Secure@123',
            'full_name': 'Alice',
            'role': 'manager',
        })
        assert resp.status_code == 400

    def test_successful_signup_returns_201(self, client):
        import uuid
        uid = uuid.uuid4()
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.side_effect = [
            None,  # no existing user
            (uid, 'alice@test.com', 'Alice', 'admin', None),
        ]
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            resp = client.post('/api/auth/signup', json={
                'email': 'alice@test.com',
                'password': 'Secure@123',
                'full_name': 'Alice',
                'role': 'admin',
            })
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'token' in data

    def test_existing_email_returns_400(self, client):
        import uuid
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = (uuid.uuid4(),)  # existing user
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            resp = client.post('/api/auth/signup', json={
                'email': 'existing@test.com',
                'password': 'Secure@123',
                'full_name': 'Alice',
                'role': 'admin',
            })
        assert resp.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# Auth — Login endpoint
# ═════════════════════════════════════════════════════════════════════════════

class TestLoginEndpoint:
    def test_missing_body_returns_400(self, client):
        resp = client.post('/api/auth/login', data='', content_type='application/json')
        assert resp.status_code == 400

    def test_missing_email_returns_400(self, client):
        resp = client.post('/api/auth/login', json={'password': 'pass'})
        assert resp.status_code == 400

    def test_missing_password_returns_400(self, client):
        resp = client.post('/api/auth/login', json={'email': 'x@x.com'})
        assert resp.status_code == 400

    def test_invalid_credentials_returns_401(self, client):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = None
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            resp = client.post('/api/auth/login', json={
                'email': 'ghost@test.com',
                'password': 'Pass@word1',
            })
        assert resp.status_code == 401

    def test_successful_login_returns_200(self, client):
        import uuid
        from auth import hash_password
        uid = uuid.uuid4()
        pw_hash = hash_password('Secure@123')

        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = (uid, 'user@test.com', pw_hash, 'Test User', 'admin', None)
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            resp = client.post('/api/auth/login', json={
                'email': 'user@test.com',
                'password': 'Secure@123',
            })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'token' in data
        assert data['user']['email'] == 'user@test.com'


# ═════════════════════════════════════════════════════════════════════════════
# Auth — Protected routes (token_required)
# ═════════════════════════════════════════════════════════════════════════════

class TestProtectedRoutes:
    def test_verify_without_token_returns_401(self, client):
        resp = client.post('/api/auth/verify')
        assert resp.status_code == 401

    def test_verify_with_invalid_token_returns_401(self, client):
        resp = client.post('/api/auth/verify', headers={'Authorization': 'Bearer bad.token'})
        assert resp.status_code == 401

    def test_verify_with_valid_token_returns_200(self, client, admin_token):
        import uuid
        uid = uuid.uuid4()
        conn = MagicMock()
        cur = MagicMock()
        from datetime import datetime
        cur.fetchone.return_value = (uid, 'admin@test.com', 'Admin', 'admin', None, datetime.utcnow())
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            resp = client.post('/api/auth/verify', headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['message'] == 'Token is valid'

    def test_profile_without_token_returns_401(self, client):
        resp = client.get('/api/auth/profile')
        assert resp.status_code == 401

    def test_profile_with_valid_token(self, client, admin_token):
        import uuid
        uid = uuid.uuid4()
        conn = MagicMock()
        cur = MagicMock()
        from datetime import datetime
        cur.fetchone.return_value = (uid, 'admin@test.com', 'Admin', 'admin', None, datetime.utcnow())
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            resp = client.get('/api/auth/profile', headers=auth_header(admin_token))
        assert resp.status_code == 200

    def test_refresh_returns_new_token(self, client, admin_token):
        resp = client.post('/api/auth/refresh', headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'token' in data

    def test_logout_returns_200(self, client, admin_token):
        from auth import generate_token
        # Use a fresh token so we don't invalidate the shared session fixture
        fresh = generate_token('user-logout', 'lo@test.com', role='admin')
        resp = client.post('/api/auth/logout', headers=auth_header(fresh))
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'Logged out' in data.get('message', '')

    def test_malformed_bearer_returns_401(self, client):
        resp = client.post('/api/auth/verify', headers={'Authorization': 'Bearer'})
        assert resp.status_code == 401
