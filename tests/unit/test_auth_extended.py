"""Extended auth module tests - covers signup/login/profile with mocked DB."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from auth import (
    hash_password, verify_password, validate_password_strength,
    generate_token, verify_token, invalidate_token,
    signup_user, login_user, get_user_profile,
    is_full_access, effective_estate_id, FULL_ACCESS_ROLES
)


# ────────────────────────────────────────────────────────────────────────────
# Helper to build a fake DB connection/cursor
# ────────────────────────────────────────────────────────────────────────────

def _mock_conn(rows=None, fetchone_value=None):
    """Return a MagicMock connection whose cursor() returns fetchone_value."""
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_value
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


# ────────────────────────────────────────────────────────────────────────────
# signup_user
# ────────────────────────────────────────────────────────────────────────────

class TestSignupUser:
    """Test signup_user with mocked DB."""

    @patch('auth.get_db_connection')
    def test_signup_no_db(self, mock_get_db):
        """signup fails gracefully when DB is unavailable."""
        mock_get_db.return_value = None
        result, status = signup_user('a@b.com', 'Pass1!aA', 'Alice')
        assert status == 500
        assert 'error' in result

    @patch('auth.get_db_connection')
    def test_signup_email_already_exists(self, mock_get_db):
        """signup returns 400 when email is taken."""
        conn, cur = _mock_conn(fetchone_value=('existing-id',))
        mock_get_db.return_value = conn
        result, status = signup_user('taken@b.com', 'Pass1!aA', 'Bob')
        assert status == 400
        assert 'error' in result

    @patch('auth.get_db_connection')
    def test_signup_success(self, mock_get_db):
        """signup creates user and returns token."""
        import uuid
        user_id = uuid.uuid4()

        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        # First fetchone (check email) returns None (user doesn't exist)
        # Second fetchone (INSERT RETURNING) returns new user
        cur.fetchone.side_effect = [
            None,  # no existing user
            (user_id, 'new@b.com', 'New User', 'manager', None),
        ]
        mock_get_db.return_value = conn

        result, status = signup_user('new@b.com', 'Pass1!aA', 'New User')
        assert status == 201
        assert 'token' in result
        assert result['user']['email'] == 'new@b.com'

    @patch('auth.get_db_connection')
    def test_signup_db_exception(self, mock_get_db):
        """signup handles DB exception."""
        conn = MagicMock()
        conn.cursor.side_effect = Exception("DB error")
        mock_get_db.return_value = conn

        result, status = signup_user('err@b.com', 'Pass1!aA', 'Error')
        assert status == 500


# ────────────────────────────────────────────────────────────────────────────
# login_user
# ────────────────────────────────────────────────────────────────────────────

class TestLoginUser:
    """Test login_user with mocked DB."""

    @patch('auth.get_db_connection')
    def test_login_no_db(self, mock_get_db):
        """login fails gracefully when DB is unavailable."""
        mock_get_db.return_value = None
        result, status = login_user('a@b.com', 'Pass1!aA')
        assert status == 500

    @patch('auth.get_db_connection')
    def test_login_user_not_found(self, mock_get_db):
        """login returns 401 when user not found."""
        conn, cur = _mock_conn(fetchone_value=None)
        mock_get_db.return_value = conn
        result, status = login_user('nobody@b.com', 'Pass1!aA')
        assert status == 401
        assert 'error' in result

    @patch('auth.get_db_connection')
    def test_login_wrong_password(self, mock_get_db):
        """login returns 401 on wrong password."""
        import uuid
        real_hash = hash_password('CorrectPass1!')
        user_row = (uuid.uuid4(), 'user@b.com', real_hash, 'User', 'manager', None)
        conn, cur = _mock_conn(fetchone_value=user_row)
        mock_get_db.return_value = conn

        result, status = login_user('user@b.com', 'WrongPass1!')
        assert status == 401

    @patch('auth.get_db_connection')
    def test_login_success(self, mock_get_db):
        """login returns token on success."""
        import uuid
        real_hash = hash_password('CorrectPass1!')
        user_id = uuid.uuid4()
        user_row = (user_id, 'user@b.com', real_hash, 'User', 'manager', None)
        conn, cur = _mock_conn(fetchone_value=user_row)
        mock_get_db.return_value = conn

        result, status = login_user('user@b.com', 'CorrectPass1!')
        assert status == 200
        assert 'token' in result
        assert result['user']['email'] == 'user@b.com'


# ────────────────────────────────────────────────────────────────────────────
# get_user_profile
# ────────────────────────────────────────────────────────────────────────────

class TestGetUserProfile:
    """Test get_user_profile with mocked DB."""

    @patch('auth.get_db_connection')
    def test_profile_no_db(self, mock_get_db):
        """profile fails gracefully when DB is unavailable."""
        mock_get_db.return_value = None
        result, status = get_user_profile('some-uuid')
        assert status == 500

    @patch('auth.get_db_connection')
    def test_profile_user_not_found(self, mock_get_db):
        """profile returns 404 when user not found."""
        conn, cur = _mock_conn(fetchone_value=None)
        mock_get_db.return_value = conn
        result, status = get_user_profile('missing-uuid')
        assert status == 404

    @patch('auth.get_db_connection')
    def test_profile_success(self, mock_get_db):
        """profile returns user data on success."""
        import uuid
        user_id = uuid.uuid4()
        user_row = (user_id, 'user@b.com', 'Test User', 'manager', None, datetime(2024, 1, 1))
        conn, cur = _mock_conn(fetchone_value=user_row)
        mock_get_db.return_value = conn

        result, status = get_user_profile(str(user_id))
        assert status == 200
        assert result['user']['email'] == 'user@b.com'


# ────────────────────────────────────────────────────────────────────────────
# FULL_ACCESS_ROLES constant
# ────────────────────────────────────────────────────────────────────────────

class TestFullAccessRoles:
    """Test FULL_ACCESS_ROLES constant."""

    def test_admin_is_full_access(self):
        assert 'admin' in FULL_ACCESS_ROLES

    def test_estate_manager_is_full_access(self):
        assert 'estate_manager' in FULL_ACCESS_ROLES

    def test_manager_is_not_full_access(self):
        assert 'manager' not in FULL_ACCESS_ROLES
