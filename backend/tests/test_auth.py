"""
Unit tests for auth.py — pure-Python helpers that don't need a DB.
"""
import os
import sys
import time
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')

import jwt as pyjwt
from auth import (
    hash_password, verify_password, validate_password_strength,
    generate_token, verify_token, invalidate_token, _token_blacklist,
    SECRET_KEY,
)


# ═════════════════════════════════════════════════════════════════════════════
# PASSWORD HASHING
# ═════════════════════════════════════════════════════════════════════════════

class TestHashPassword:
    def test_hash_is_not_plaintext(self):
        h = hash_password('Passw0rd!')
        assert h != 'Passw0rd!'

    def test_hash_is_bcrypt_string(self):
        h = hash_password('Passw0rd!')
        assert h.startswith('$2b$')

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password('Passw0rd!')
        h2 = hash_password('Passw0rd!')
        assert h1 != h2  # bcrypt uses random salt


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        h = hash_password('Secure#1')
        assert verify_password('Secure#1', h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password('Secure#1')
        assert verify_password('WrongPass#1', h) is False

    def test_empty_password_returns_false(self):
        h = hash_password('Secure#1')
        assert verify_password('', h) is False


# ═════════════════════════════════════════════════════════════════════════════
# PASSWORD STRENGTH VALIDATION
# ═════════════════════════════════════════════════════════════════════════════

class TestValidatePasswordStrength:
    def test_strong_password_passes(self):
        valid, msg = validate_password_strength('Secure@123')
        assert valid is True

    def test_too_short(self):
        valid, msg = validate_password_strength('Ab1!')
        assert valid is False
        assert '8' in msg

    def test_no_uppercase(self):
        valid, msg = validate_password_strength('secure@123')
        assert valid is False
        assert 'uppercase' in msg.lower()

    def test_no_lowercase(self):
        valid, msg = validate_password_strength('SECURE@123')
        assert valid is False
        assert 'lowercase' in msg.lower()

    def test_no_digit(self):
        valid, msg = validate_password_strength('Secure@abc')
        assert valid is False
        assert 'digit' in msg.lower()

    def test_no_special_char(self):
        valid, msg = validate_password_strength('Secure123')
        assert valid is False
        assert 'special' in msg.lower()

    def test_exact_8_chars_with_all_requirements(self):
        valid, msg = validate_password_strength('Abc1@xyz')
        assert valid is True

    def test_very_long_strong_password(self):
        valid, msg = validate_password_strength('This_Is_A_Very_L0ng_P@ssword_That_Should_Pass!')
        assert valid is True


# ═════════════════════════════════════════════════════════════════════════════
# JWT TOKEN GENERATION & VERIFICATION
# ═════════════════════════════════════════════════════════════════════════════

class TestGenerateToken:
    def test_returns_string(self):
        token = generate_token('user-1', 'test@test.com')
        assert isinstance(token, str)

    def test_payload_contains_user_id(self):
        token = generate_token('user-1', 'test@test.com', role='admin')
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        assert payload['user_id'] == 'user-1'

    def test_payload_contains_email(self):
        token = generate_token('user-1', 'test@test.com')
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        assert payload['email'] == 'test@test.com'

    def test_payload_contains_role(self):
        token = generate_token('user-1', 'a@b.com', role='admin')
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        assert payload['role'] == 'admin'

    def test_estate_id_serialised_as_string(self):
        import uuid
        eid = uuid.uuid4()
        token = generate_token('user-1', 'a@b.com', estate_id=eid)
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        assert payload['estate_id'] == str(eid)

    def test_none_estate_id_stays_none(self):
        token = generate_token('user-1', 'a@b.com', estate_id=None)
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        assert payload['estate_id'] is None

    def test_token_expires_after_7_days_by_default(self):
        before = datetime.utcnow()
        token = generate_token('user-1', 'a@b.com')
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        exp = datetime.utcfromtimestamp(payload['exp'])
        diff = exp - before
        assert timedelta(days=6, hours=23) < diff <= timedelta(days=7, seconds=5)

    def test_custom_expiry(self):
        token = generate_token('user-1', 'a@b.com', expires_in_days=1)
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        exp = datetime.utcfromtimestamp(payload['exp'])
        diff = exp - datetime.utcnow()
        assert diff < timedelta(days=2)


class TestVerifyToken:
    def test_valid_token_returns_payload(self):
        token = generate_token('user-1', 'a@b.com', role='admin')
        payload = verify_token(token)
        assert payload is not None
        assert payload['email'] == 'a@b.com'

    def test_invalid_token_returns_none(self):
        assert verify_token('not.a.real.token') is None

    def test_expired_token_returns_none(self):
        # Craft an already-expired token
        payload = {
            'user_id': 'u1',
            'email': 'x@x.com',
            'role': None,
            'estate_id': None,
            'iat': datetime.utcnow() - timedelta(days=10),
            'exp': datetime.utcnow() - timedelta(days=3),
        }
        expired = pyjwt.encode(payload, SECRET_KEY, algorithm='HS256')
        assert verify_token(expired) is None

    def test_blacklisted_token_returns_none(self):
        token = generate_token('user-x', 'x@x.com')
        invalidate_token(token)
        assert verify_token(token) is None
        # Clean up blacklist for other tests
        _token_blacklist.discard(token)

    def test_wrong_secret_returns_none(self):
        bad_token = pyjwt.encode(
            {'user_id': '1', 'email': 'x@x.com', 'exp': datetime.utcnow() + timedelta(days=1)},
            'wrong-secret', algorithm='HS256'
        )
        assert verify_token(bad_token) is None


class TestInvalidateToken:
    def test_token_added_to_blacklist(self):
        token = generate_token('user-z', 'z@z.com')
        assert token not in _token_blacklist
        invalidate_token(token)
        assert token in _token_blacklist
        _token_blacklist.discard(token)


# ═════════════════════════════════════════════════════════════════════════════
# SIGNUP / LOGIN (mocked DB)
# ═════════════════════════════════════════════════════════════════════════════

class TestSignupUser:
    def test_db_failure_returns_500(self):
        from auth import signup_user
        with patch('auth.get_db_connection', return_value=None):
            result, status = signup_user('a@b.com', 'Pass@123', 'Alice')
            assert status == 500

    def test_existing_email_returns_400(self):
        from auth import signup_user
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = ('existing-id',)
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)

        with patch('auth.get_db_connection', return_value=conn):
            result, status = signup_user('existing@test.com', 'Pass@123', 'Alice')
            assert status == 400
            assert 'already registered' in result.get('error', '')

    def test_successful_signup_returns_201(self):
        from auth import signup_user
        import uuid
        user_id = uuid.uuid4()

        conn = MagicMock()
        cur = MagicMock()
        # First fetchone: no existing user
        # Second fetchone: inserted user
        cur.fetchone.side_effect = [
            None,
            (user_id, 'new@test.com', 'New User', 'manager', None),
        ]
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            result, status = signup_user('new@test.com', 'Pass@123', 'New User')
            assert status == 201
            assert 'token' in result


class TestLoginUser:
    def test_db_failure_returns_500(self):
        from auth import login_user
        with patch('auth.get_db_connection', return_value=None):
            result, status = login_user('a@b.com', 'pass')
            assert status == 500

    def test_user_not_found_returns_401(self):
        from auth import login_user
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = None
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            result, status = login_user('notfound@test.com', 'pass')
            assert status == 401

    def test_wrong_password_returns_401(self):
        from auth import login_user
        pw_hash = hash_password('Correct@1')
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = (
            'uid', 'test@test.com', pw_hash, 'Test User', 'manager', None
        )
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            result, status = login_user('test@test.com', 'Wrong@pass1')
            assert status == 401

    def test_successful_login_returns_200_with_token(self):
        from auth import login_user
        import uuid
        uid = uuid.uuid4()
        pw_hash = hash_password('Correct@1')
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = (uid, 'test@test.com', pw_hash, 'Test User', 'admin', None)
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        with patch('auth.get_db_connection', return_value=conn):
            result, status = login_user('test@test.com', 'Correct@1')
            assert status == 200
            assert 'token' in result
            assert result['user']['role'] == 'admin'
