"""Tests for labour_serializers module - imports real functions."""
import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

# Import actual serializer functions
from labour_serializers import (
    serialize_uuid, serialize_date, serialize_decimal, 
    serialize_int, serialize_bool, serialize_string,
    EmployeeSerializer, WorkerGroupSerializer
)


class TestSerializerHelpers:
    """Test actual serializer helper functions."""

    def test_serialize_uuid(self):
        """Test UUID serialization."""
        test_uuid = UUID('12345678-1234-5678-1234-567812345678')
        result = serialize_uuid(test_uuid)
        
        assert result == '12345678-1234-5678-1234-567812345678'
        assert isinstance(result, str)

    def test_serialize_uuid_none(self):
        """Test UUID serialization with None."""
        result = serialize_uuid(None)
        assert result is None

    def test_serialize_date(self):
        """Test date serialization."""
        test_date = date(2024, 6, 15)
        result = serialize_date(test_date)
        
        assert result == '2024-06-15'
        assert isinstance(result, str)

    def test_serialize_datetime(self):
        """Test datetime serialization."""
        test_datetime = datetime(2024, 6, 15, 10, 30, 45)
        result = serialize_date(test_datetime)
        
        assert '2024-06-15T10:30:45' in result
        assert isinstance(result, str)

    def test_serialize_date_none(self):
        """Test date serialization with None."""
        result = serialize_date(None)
        assert result is None

    def test_serialize_decimal(self):
        """Test Decimal serialization."""
        test_decimal = Decimal('1234.56')
        result = serialize_decimal(test_decimal)
        
        assert result == 1234.56
        assert isinstance(result, float)

    def test_serialize_decimal_none(self):
        """Test Decimal serialization with None."""
        result = serialize_decimal(None)
        assert result is None

    def test_serialize_int(self):
        """Test int serialization."""
        result = serialize_int(42)
        
        assert result == 42
        assert isinstance(result, int)

    def test_serialize_int_from_string(self):
        """Test int serialization from string."""
        result = serialize_int('123')
        
        assert result == 123
        assert isinstance(result, int)

    def test_serialize_int_none(self):
        """Test int serialization with None."""
        result = serialize_int(None)
        assert result is None

    def test_serialize_bool_true(self):
        """Test bool serialization with True."""
        result = serialize_bool(True)
        
        assert result is True
        assert isinstance(result, bool)

    def test_serialize_bool_false(self):
        """Test bool serialization with False."""
        result = serialize_bool(False)
        
        assert result is False
        assert isinstance(result, bool)

    def test_serialize_bool_none(self):
        """Test bool serialization with None."""
        result = serialize_bool(None)
        assert result is False

    def test_serialize_string(self):
        """Test string serialization."""
        result = serialize_string('  test string  ')
        
        assert result == 'test string'
        assert isinstance(result, str)

    def test_serialize_string_none(self):
        """Test string serialization with None."""
        result = serialize_string(None)
        assert result is None


class TestEmployeeSerializer:
    """Test EmployeeSerializer class."""

    def test_serialize_employee(self):
        """Test serializing employee row."""
        employee_row = {
            'id': UUID('12345678-1234-5678-1234-567812345678'),
            'estate_id': UUID('87654321-4321-8765-4321-876543218765'),
            'employee_code': 'EMP001',
            'full_name': 'John Doe',
            'gender': 'Male',
            'national_id': '123456789V',
            'hire_date': date(2023, 6, 15),
            'employment_type': 'Full-time',
            'skill_type': 'Pruning',
            'daily_wage_lkr': Decimal('1500.00'),
            'is_active': True,
            'notes': 'Test employee',
            'created_at': datetime(2023, 6, 15, 10, 0, 0),
            'updated_at': datetime(2024, 6, 15, 10, 0, 0),
        }
        
        result = EmployeeSerializer.serialize_employee(employee_row)
        
        assert result['employee_code'] == 'EMP001'
        assert result['full_name'] == 'John Doe'
        assert result['daily_wage_lkr'] == 1500.0
        assert result['is_active'] is True

    def test_serialize_employees(self):
        """Test serializing multiple employees."""
        employees = [
            {
                'id': UUID('12345678-1234-5678-1234-567812345678'),
                'estate_id': UUID('87654321-4321-8765-4321-876543218765'),
                'employee_code': 'EMP001',
                'full_name': 'John Doe',
                'gender': 'Male',
                'national_id': '123456789V',
                'hire_date': date(2023, 6, 15),
                'employment_type': 'Full-time',
                'skill_type': 'Pruning',
                'daily_wage_lkr': Decimal('1500.00'),
                'is_active': True,
                'notes': None,
                'created_at': datetime(2023, 6, 15),
                'updated_at': datetime(2024, 6, 15),
            },
            {
                'id': UUID('11111111-1111-1111-1111-111111111111'),
                'estate_id': UUID('87654321-4321-8765-4321-876543218765'),
                'employee_code': 'EMP002',
                'full_name': 'Jane Smith',
                'gender': 'Female',
                'national_id': '987654321V',
                'hire_date': date(2023, 7, 20),
                'employment_type': 'Full-time',
                'skill_type': 'Harvesting',
                'daily_wage_lkr': Decimal('1600.00'),
                'is_active': True,
                'notes': None,
                'created_at': datetime(2023, 7, 20),
                'updated_at': datetime(2024, 6, 15),
            }
        ]
        
        result = EmployeeSerializer.serialize_employees(employees)
        
        assert len(result) == 2
        assert result[0]['full_name'] == 'John Doe'
        assert result[1]['full_name'] == 'Jane Smith'
        assert result[0]['daily_wage_lkr'] == 1500.0
        assert result[1]['daily_wage_lkr'] == 1600.0


class TestWorkerGroupSerializer:
    """Test WorkerGroupSerializer class."""

    def test_worker_group_serializer_exists(self):
        """Test that WorkerGroupSerializer is available."""
        assert WorkerGroupSerializer is not None
        # The real method is serialize_group / serialize_groups
        assert hasattr(WorkerGroupSerializer, 'serialize_group') or hasattr(WorkerGroupSerializer, 'serialize_groups')
