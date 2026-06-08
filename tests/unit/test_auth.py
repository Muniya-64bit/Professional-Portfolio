"""Unit tests for authentication module."""
import pytest
import os
from datetime import datetime, timedelta
import jwt

# Import auth functions
from auth import (
    hash_password, verify_password, validate_password_strength,
    generate_token, verify_token, invalidate_token
)


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a valid hash."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_success(self):
        """Test that verify_password works with correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Test that verify_password fails with wrong password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword123!", hashed) is False
    
    def test_hash_consistency(self):
        """Test that same password produces different hashes (salt)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Different hashes due to different salts
        assert hash1 != hash2
        # Both verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestPasswordValidation:
    """Test password strength validation."""
    
    def test_valid_strong_password(self):
        """Test validation of a strong password."""
        password = "StrongPass123!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is True
        assert "strong" in message.lower()
    
    def test_password_too_short(self):
        """Test validation fails for short password."""
        password = "Short1!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "8 characters" in message
    
    def test_password_missing_uppercase(self):
        """Test validation fails without uppercase."""
        password = "weakpassword123!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "uppercase" in message
    
    def test_password_missing_lowercase(self):
        """Test validation fails without lowercase."""
        password = "WEAKPASSWORD123!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "lowercase" in message
    
    def test_password_missing_digit(self):
        """Test validation fails without digit."""
        password = "WeakPassword!"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "digit" in message
    
    def test_password_missing_special_char(self):
        """Test validation fails without special character."""
        password = "WeakPassword123"
        is_valid, message = validate_password_strength(password)
        
        assert is_valid is False
        assert "special character" in message


class TestTokenGeneration:
    """Test JWT token generation and verification."""
    
    def test_generate_token_creates_token(self):
        """Test that generate_token creates a valid JWT."""
        user_id = "test-user-id"
        email = "test@example.com"
        token = generate_token(user_id, email)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_generate_token_can_be_decoded(self):
        """Test that generated token can be decoded."""
        user_id = "test-user-id"
        email = "test@example.com"
        token = generate_token(user_id, email, role='manager')
        
        payload = verify_token(token)
        
        assert payload is not None
        assert isinstance(payload, dict)
        assert payload.get('user_id') == user_id
        assert 'exp' in payload
    
    def test_verify_token_valid(self):
        """Test verify_token with valid token."""
        user_id = "test-user-id"
        email = "test@example.com"
        token = generate_token(user_id, email)
        
        result = verify_token(token)
        
        assert result is not None
        assert isinstance(result, dict)
        assert result.get('user_id') == user_id
    
    def test_verify_token_invalid(self):
        """Test verify_token with invalid token."""
        invalid_token = "invalid.token.here"
        
        result = verify_token(invalid_token)
        
        assert result is None
    
    def test_verify_token_expired(self):
        """Test verify_token with expired token."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        # Create token with 0 days expiration (already expired)
        token = generate_token(user_id, email, expires_in_days=0)
        
        # Wait a moment for time to pass
        import time
        time.sleep(0.1)
        
        result = verify_token(token)
        
        # Should return None for expired token
        assert result is None


class TestTokenBlacklist:
    """Test token blacklist functionality for logout."""
    
    def test_invalidate_token_blacklists_token(self):
        """Test that invalidate_token prevents token verification."""
        user_id = "test-user-id"
        email = "test@example.com"
        token = generate_token(user_id, email)
        
        # Verify token works initially
        assert verify_token(token) is not None
        
        # Invalidate token
        invalidate_token(token)
        
        # After invalidation, token should fail verification
        assert verify_token(token) is None
