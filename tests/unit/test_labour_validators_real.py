"""Tests for labour_validators module - imports real functions."""
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta

# Import actual validators
from labour_validators import (
    EmployeeValidator, WorkerGroupValidator, LabourPlanValidator,
    BlockAssignmentValidator, RotationValidator,
    LabourValidationError, EmployeeValidationError
)


class TestEmployeeValidator:
    """Test EmployeeValidator class with actual functions."""

    def test_validate_employee_code_valid(self):
        """Test valid employee code."""
        is_valid, error = EmployeeValidator.validate_employee_code('EMP-001')
        assert is_valid is True
        assert error is None

    def test_validate_employee_code_invalid_empty(self):
        """Test invalid empty employee code."""
        is_valid, error = EmployeeValidator.validate_employee_code('')
        assert is_valid is False
        assert error is not None

    def test_validate_employee_code_invalid_too_long(self):
        """Test employee code that's too long."""
        long_code = 'A' * 51
        is_valid, error = EmployeeValidator.validate_employee_code(long_code)
        assert is_valid is False

    def test_validate_employee_code_invalid_type(self):
        """Test employee code with invalid type."""
        is_valid, error = EmployeeValidator.validate_employee_code(None)
        assert is_valid is False

    def test_validate_employee_code_with_underscore(self):
        """Test employee code with underscore."""
        is_valid, error = EmployeeValidator.validate_employee_code('EMP_001')
        assert is_valid is True

    def test_validate_employee_code_with_dash(self):
        """Test employee code with dash."""
        is_valid, error = EmployeeValidator.validate_employee_code('EMP-001')
        assert is_valid is True

    def test_valid_employment_types(self):
        """Test valid employment types are defined."""
        assert 'permanent' in EmployeeValidator.VALID_EMPLOYMENT_TYPES
        assert 'casual' in EmployeeValidator.VALID_EMPLOYMENT_TYPES
        assert 'seasonal' in EmployeeValidator.VALID_EMPLOYMENT_TYPES

    def test_valid_skill_types(self):
        """Test valid skill types are defined."""
        assert 'plucker' in EmployeeValidator.VALID_SKILL_TYPES
        assert 'general' in EmployeeValidator.VALID_SKILL_TYPES
        assert 'supervisor' in EmployeeValidator.VALID_SKILL_TYPES
        assert 'driver' in EmployeeValidator.VALID_SKILL_TYPES

    def test_valid_genders(self):
        """Test valid gender values are defined."""
        assert 'M' in EmployeeValidator.VALID_GENDERS
        assert 'F' in EmployeeValidator.VALID_GENDERS
        assert 'O' in EmployeeValidator.VALID_GENDERS


class TestWorkerGroupValidator:
    """Test WorkerGroupValidator class."""

    def test_worker_group_validator_exists(self):
        """Test that WorkerGroupValidator is available."""
        assert WorkerGroupValidator is not None


class TestLabourPlanValidator:
    """Test LabourPlanValidator class."""

    def test_labour_plan_validator_exists(self):
        """Test that LabourPlanValidator is available."""
        assert LabourPlanValidator is not None


class TestBlockAssignmentValidator:
    """Test BlockAssignmentValidator class."""

    def test_block_assignment_validator_exists(self):
        """Test that BlockAssignmentValidator is available."""
        assert BlockAssignmentValidator is not None


class TestRotationValidator:
    """Test RotationValidator class."""

    def test_rotation_validator_exists(self):
        """Test that RotationValidator is available."""
        assert RotationValidator is not None


class TestValidationExceptions:
    """Test validation exception classes."""

    def test_labour_validation_error(self):
        """Test LabourValidationError."""
        error = LabourValidationError('field_name', 'Error message')
        assert error.field == 'field_name'
        assert error.message == 'Error message'

    def test_employee_validation_error(self):
        """Test EmployeeValidationError."""
        error = EmployeeValidationError('employee_code', 'Invalid code')
        assert error.field == 'employee_code'
        assert 'employee_code' in str(error)
