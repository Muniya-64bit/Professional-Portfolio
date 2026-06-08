"""Tests for auth module - calls actual functions."""
import pytest
import os
from datetime import datetime, timedelta

# Import actual auth functions
from auth import (
    hash_password, verify_password, validate_password_strength,
    generate_token, verify_token, invalidate_token
)


class TestPasswordHashing:
    """Test password hashing and verification functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert password not in hashed

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        result = verify_password(password, hashed)
        
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        result = verify_password("WrongPassword123!", hashed)
        
        assert result is False

    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        result = verify_password("", hashed)
        
        assert result is False

    def test_hash_unique_salts(self):
        """Test that two hashes of the same password are different (salted)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestPasswordValidation:
    """Test password strength validation."""

    def test_validate_strong_password(self):
        """Test strong password validation."""
        password = "StrongPass123!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is True
        assert message == "Password is strong"

    def test_validate_password_too_short(self):
        """Test password that's too short."""
        password = "Short1!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "8 characters" in message

    def test_validate_password_no_uppercase(self):
        """Test password without uppercase letter."""
        password = "lowercase123!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "uppercase" in message.lower()

    def test_validate_password_no_lowercase(self):
        """Test password without lowercase letter."""
        password = "UPPERCASE123!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "lowercase" in message.lower()

    def test_validate_password_no_digit(self):
        """Test password without digit."""
        password = "NoDigitHere!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "digit" in message.lower()

    def test_validate_password_no_special(self):
        """Test password without special character."""
        password = "NoSpecial123"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "special" in message.lower()

    def test_validate_password_exactly_8_chars(self):
        """Test password with exactly 8 characters."""
        password = "Valid1!A"  # exactly 8 chars with all requirements
        is_valid, message = validate_password_strength(password)
        assert is_valid is True

    def test_validate_password_long(self):
        """Test a very long strong password."""
        password = "VeryLongStrongPassword123!@#"
        is_valid, message = validate_password_strength(password)
        assert is_valid is True


class TestTokenGeneration:
    """Test JWT token generation and verification."""

    def test_generate_token(self):
        """Test token generation."""
        token = generate_token("user-123", "test@example.com")
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count('.') == 2  # JWT has 3 parts

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        token = generate_token("user-123", "test@example.com")
        
        result = verify_token(token)
        
        assert isinstance(result, dict)
        assert result['user_id'] == "user-123"
        assert result['email'] == "test@example.com"

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        result = verify_token("invalid.token.here")
        
        assert result is None or result is False

    def test_verify_token_empty(self):
        """Test token verification with empty string."""
        result = verify_token("")
        
        assert result is None or result is False

    def test_generate_token_different_users(self):
        """Test tokens for different users are different."""
        token1 = generate_token("user1", "user1@test.com")
        token2 = generate_token("user2", "user2@test.com")
        
        assert token1 != token2

    def test_generate_token_contains_role(self):
        """Test token contains role when provided."""
        token = generate_token("user-123", "test@example.com", role="admin")
        payload = verify_token(token)
        
        assert payload['role'] == 'admin'

    def test_generate_token_contains_estate_id(self):
        """Test token contains estate_id when provided."""
        token = generate_token("user-123", "test@example.com", estate_id="estate-456")
        payload = verify_token(token)
        
        assert payload['estate_id'] == 'estate-456'

    def test_invalidate_token(self):
        """Test token invalidation."""
        token = generate_token("user-123", "test@example.com")
        
        # Before invalidation, token is valid
        assert verify_token(token) is not None
        
        # Invalidate the token
        invalidate_token(token)
        
        # After invalidation, token should be invalid
        result = verify_token(token)
        assert result is None or result is False
