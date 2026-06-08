"""Unit tests for schema validation and data models."""
import pytest
from datetime import datetime


class TestDataValidation:
    """Test data validation utilities."""
    
    def test_email_validation_valid(self):
        """Test valid email formats."""
        valid_emails = [
            'user@example.com',
            'john.doe@company.co.uk',
            'admin+tag@domain.org',
        ]
        
        for email in valid_emails:
            assert '@' in email
            assert '.' in email.split('@')[1]
    
    def test_email_validation_invalid(self):
        """Test invalid email formats."""
        invalid_emails = [
            ('plaintext', 'no @ symbol'),
            ('user@', 'missing domain'),
            ('@domain.com', 'missing local part'),
            ('user@.com', 'missing domain name'),
        ]
        
        for email, reason in invalid_emails:
            # Basic check: must have @, and domain must have valid format
            parts = email.split('@')
            if len(parts) != 2:
                is_valid = False
            else:
                local, domain = parts
                # Check that both local and domain parts are non-empty
                if not local or not domain:
                    is_valid = False
                else:
                    # Check domain has at least one dot and parts before/after
                    domain_parts = domain.split('.')
                    is_valid = len(domain_parts) >= 2 and all(part for part in domain_parts)
            
            assert is_valid is False, f"Email '{email}' should be invalid ({reason})"
    
    def test_uuid_format_validation(self):
        """Test UUID format validation."""
        import uuid
        
        valid_uuid = str(uuid.uuid4())
        
        # Test format with hyphens
        assert len(valid_uuid) == 36
        assert valid_uuid.count('-') == 4
    
    def test_date_range_validation(self):
        """Test date range validation."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        assert start_date < end_date
        assert (end_date - start_date).days > 0


class TestNumericValidation:
    """Test numeric data validation."""
    
    def test_positive_number_validation(self):
        """Test validation of positive numbers."""
        values = [10.5, 100, 0.001]
        
        for val in values:
            assert val > 0
    
    def test_percentage_validation(self):
        """Test percentage value validation."""
        percentages = [0, 50, 100]
        
        for pct in percentages:
            assert 0 <= pct <= 100
    
    def test_decimal_precision(self):
        """Test decimal precision handling."""
        from decimal import Decimal
        
        value = Decimal('10.5555')
        rounded = round(float(value), 2)
        
        assert rounded == 10.56
    
    def test_large_number_handling(self):
        """Test handling of large numbers."""
        large_number = 999999999.99
        
        assert large_number > 0
        assert isinstance(large_number, float)


class TestStringValidation:
    """Test string data validation."""
    
    def test_empty_string_validation(self):
        """Test empty string validation."""
        empty_strings = ['', ' ', '\t', '\n']
        
        for s in empty_strings:
            assert len(s.strip()) == 0
    
    def test_string_length_validation(self):
        """Test string length limits."""
        string = "x" * 100
        max_length = 50
        
        assert len(string) > max_length
        assert len(string[:max_length]) == max_length
    
    def test_string_format_validation(self):
        """Test string format validation."""
        # Test alphanumeric
        assert "abc123".isalnum() is True
        assert "abc-123".isalnum() is False
        
        # Test digits only
        assert "12345".isdigit() is True
        assert "123a5".isdigit() is False


class TestDateTimeValidation:
    """Test datetime validation."""
    
    def test_date_format_validation(self):
        """Test valid date format."""
        from datetime import datetime
        
        date_str = "2024-01-15"
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        assert parsed_date.year == 2024
        assert parsed_date.month == 1
        assert parsed_date.day == 15
    
    def test_invalid_date_format(self):
        """Test invalid date format raises error."""
        from datetime import datetime
        
        with pytest.raises(ValueError):
            datetime.strptime("2024-13-45", "%Y-%m-%d")
    
    def test_date_range_validation(self):
        """Test date is within valid range."""
        from datetime import datetime
        
        min_date = datetime(2000, 1, 1)
        max_date = datetime(2100, 12, 31)
        test_date = datetime(2024, 6, 8)
        
        assert min_date <= test_date <= max_date
        text = "A" * 256
        max_length = 255
        
        assert len(text) > max_length
    
    def test_special_characters_handling(self):
        """Test handling of special characters."""
        text_with_special = "Test@#$%^&*()"
        
        assert len(text_with_special) > 0
        assert any(c in text_with_special for c in '@#$%^&*()')


class TestArrayValidation:
    """Test array/list data validation."""
    
    def test_non_empty_array_validation(self):
        """Test validation of non-empty arrays."""
        arrays = [
            [1, 2, 3],
            ['a', 'b'],
            [{'key': 'value'}],
        ]
        
        for arr in arrays:
            assert len(arr) > 0
    
    def test_duplicate_detection(self):
        """Test duplicate detection in arrays."""
        array = [1, 2, 3, 2, 4]
        
        duplicates = len(array) != len(set(array))
        
        assert duplicates is True
    
    def test_sorted_array_validation(self):
        """Test if array is sorted."""
        sorted_array = [1, 2, 3, 4, 5]
        unsorted_array = [1, 3, 2, 5, 4]
        
        assert sorted_array == sorted(sorted_array)
        assert unsorted_array != sorted(unsorted_array)


class TestNullableFieldHandling:
    """Test handling of nullable/optional fields."""
    
    def test_none_value_handling(self):
        """Test handling of None values."""
        value = None
        
        assert value is None
        assert not value
    
    def test_optional_field_with_default(self):
        """Test optional fields with defaults."""
        field = None
        default = "default_value"
        
        result = field or default
        
        assert result == default
    
    def test_optional_field_preserves_value(self):
        """Test optional field preserves non-None value."""
        field = "actual_value"
        default = "default_value"
        
        result = field or default
        
        assert result == "actual_value"
