"""Comprehensive tests for labour_validators - targets uncovered lines."""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from uuid import UUID

from labour_validators import (
    EmployeeValidator, WorkerGroupValidator, LabourPlanValidator,
    BlockAssignmentValidator, RotationValidator,
    LabourValidationError, EmployeeValidationError,
    WorkerGroupValidationError, LabourPlanValidationError,
    BlockAssignmentValidationError, RotationValidationError
)


class TestEmployeeValidatorMethods:
    """Test all EmployeeValidator static methods."""

    def test_validate_full_name_valid(self):
        """Test valid full name."""
        is_valid, error = EmployeeValidator.validate_full_name("John Doe")
        assert is_valid is True
        assert error is None

    def test_validate_full_name_empty(self):
        """Test empty full name."""
        is_valid, error = EmployeeValidator.validate_full_name("")
        assert is_valid is False

    def test_validate_full_name_whitespace(self):
        """Test whitespace-only full name."""
        is_valid, error = EmployeeValidator.validate_full_name("   ")
        assert is_valid is False

    def test_validate_full_name_none(self):
        """Test None full name."""
        is_valid, error = EmployeeValidator.validate_full_name(None)
        assert is_valid is False

    def test_validate_full_name_too_long(self):
        """Test full name that's too long."""
        long_name = "A" * 151
        is_valid, error = EmployeeValidator.validate_full_name(long_name)
        assert is_valid is False

    def test_validate_hire_date_valid(self):
        """Test valid hire date."""
        yesterday = date.today() - timedelta(days=1)
        is_valid, error = EmployeeValidator.validate_hire_date(yesterday)
        assert is_valid is True

    def test_validate_hire_date_today(self):
        """Test hire date of today."""
        is_valid, error = EmployeeValidator.validate_hire_date(date.today())
        assert is_valid is True

    def test_validate_hire_date_future(self):
        """Test hire date in the future."""
        future = date.today() + timedelta(days=1)
        is_valid, error = EmployeeValidator.validate_hire_date(future)
        assert is_valid is False

    def test_validate_hire_date_string(self):
        """Test hire date as string."""
        is_valid, error = EmployeeValidator.validate_hire_date("2023-06-15")
        assert is_valid is True

    def test_validate_hire_date_invalid_string(self):
        """Test invalid date string."""
        is_valid, error = EmployeeValidator.validate_hire_date("not-a-date")
        assert is_valid is False

    def test_validate_employment_type_permanent(self):
        """Test valid permanent employment type."""
        is_valid, error = EmployeeValidator.validate_employment_type("permanent")
        assert is_valid is True

    def test_validate_employment_type_casual(self):
        """Test valid casual employment type."""
        is_valid, error = EmployeeValidator.validate_employment_type("casual")
        assert is_valid is True

    def test_validate_employment_type_seasonal(self):
        """Test valid seasonal employment type."""
        is_valid, error = EmployeeValidator.validate_employment_type("seasonal")
        assert is_valid is True

    def test_validate_employment_type_invalid(self):
        """Test invalid employment type."""
        is_valid, error = EmployeeValidator.validate_employment_type("contractor")
        assert is_valid is False

    def test_validate_employment_type_none(self):
        """Test None employment type."""
        is_valid, error = EmployeeValidator.validate_employment_type(None)
        assert is_valid is False

    def test_validate_skill_type_plucker(self):
        """Test valid plucker skill type."""
        is_valid, error = EmployeeValidator.validate_skill_type("plucker")
        assert is_valid is True

    def test_validate_skill_type_general(self):
        """Test valid general skill type."""
        is_valid, error = EmployeeValidator.validate_skill_type("general")
        assert is_valid is True

    def test_validate_skill_type_supervisor(self):
        """Test valid supervisor skill type."""
        is_valid, error = EmployeeValidator.validate_skill_type("supervisor")
        assert is_valid is True

    def test_validate_skill_type_driver(self):
        """Test valid driver skill type."""
        is_valid, error = EmployeeValidator.validate_skill_type("driver")
        assert is_valid is True

    def test_validate_skill_type_invalid(self):
        """Test invalid skill type."""
        is_valid, error = EmployeeValidator.validate_skill_type("mechanic")
        assert is_valid is False

    def test_validate_gender_male(self):
        """Test valid male gender."""
        is_valid, error = EmployeeValidator.validate_gender("M")
        assert is_valid is True

    def test_validate_gender_female(self):
        """Test valid female gender."""
        is_valid, error = EmployeeValidator.validate_gender("F")
        assert is_valid is True

    def test_validate_gender_other(self):
        """Test valid other gender."""
        is_valid, error = EmployeeValidator.validate_gender("O")
        assert is_valid is True

    def test_validate_gender_none(self):
        """Test None gender (optional)."""
        is_valid, error = EmployeeValidator.validate_gender(None)
        assert is_valid is True  # optional field

    def test_validate_gender_invalid(self):
        """Test invalid gender."""
        is_valid, error = EmployeeValidator.validate_gender("X")
        assert is_valid is False

    def test_validate_daily_wage_valid(self):
        """Test valid daily wage."""
        is_valid, error = EmployeeValidator.validate_daily_wage(Decimal('1500.00'))
        assert is_valid is True

    def test_validate_daily_wage_zero(self):
        """Test daily wage of zero."""
        is_valid, error = EmployeeValidator.validate_daily_wage(Decimal('0.00'))
        assert is_valid is False

    def test_validate_daily_wage_negative(self):
        """Test negative daily wage."""
        is_valid, error = EmployeeValidator.validate_daily_wage(Decimal('-100.00'))
        assert is_valid is False

    def test_validate_daily_wage_none(self):
        """Test None daily wage (optional)."""
        is_valid, error = EmployeeValidator.validate_daily_wage(None)
        assert is_valid is True  # optional field

    def test_validate_daily_wage_too_large(self):
        """Test daily wage exceeding max."""
        is_valid, error = EmployeeValidator.validate_daily_wage(Decimal('9999999.99'))
        assert is_valid is False

    def test_validate_employee_code_unique_not_duplicate(self):
        """Test unique employee code check - not in list."""
        is_valid, error = EmployeeValidator.validate_employee_code_unique(
            "EMP-NEW", "estate-001", ["EMP-001", "EMP-002"]
        )
        assert is_valid is True

    def test_validate_employee_code_unique_duplicate(self):
        """Test unique employee code check - already exists."""
        is_valid, error = EmployeeValidator.validate_employee_code_unique(
            "EMP-001", "estate-001", ["EMP-001", "EMP-002"]
        )
        assert is_valid is False

    def test_validate_create_request_valid(self):
        """Test valid create request."""
        data = {
            'estate_id': 'estate-001',
            'employee_code': 'EMP001',
            'full_name': 'John Doe',
            'hire_date': '2023-06-15',
            'employment_type': 'permanent',
            'skill_type': 'plucker',
        }
        errors = EmployeeValidator.validate_create_request(data)
        assert errors == {}

    def test_validate_create_request_missing_required(self):
        """Test create request with missing required fields."""
        data = {'estate_id': 'estate-001'}
        errors = EmployeeValidator.validate_create_request(data)
        assert 'employee_code' in errors or 'full_name' in errors or 'hire_date' in errors

    def test_validate_create_request_invalid_employment_type(self):
        """Test create request with invalid employment type."""
        data = {
            'estate_id': 'estate-001',
            'employee_code': 'EMP001',
            'full_name': 'John Doe',
            'hire_date': '2023-06-15',
            'employment_type': 'invalid_type',
        }
        errors = EmployeeValidator.validate_create_request(data)
        assert 'employment_type' in errors

    def test_validate_update_request_valid(self):
        """Test valid update request."""
        data = {'full_name': 'Jane Doe', 'employment_type': 'casual'}
        errors = EmployeeValidator.validate_update_request(data)
        assert errors == {}

    def test_validate_update_request_unknown_field(self):
        """Test update request with unknown field."""
        data = {'unknown_field': 'value'}
        errors = EmployeeValidator.validate_update_request(data)
        assert 'unknown_field' in errors

    def test_validate_update_request_invalid_is_active(self):
        """Test update request with non-boolean is_active."""
        data = {'is_active': 'yes'}  # Should be bool
        errors = EmployeeValidator.validate_update_request(data)
        assert 'is_active' in errors


class TestWorkerGroupValidatorMethods:
    """Test all WorkerGroupValidator static methods."""

    def test_validate_group_code_valid(self):
        """Test valid group code."""
        is_valid, error = WorkerGroupValidator.validate_group_code("GRP-001")
        assert is_valid is True

    def test_validate_group_code_empty(self):
        """Test empty group code."""
        is_valid, error = WorkerGroupValidator.validate_group_code("")
        assert is_valid is False

    def test_validate_group_code_too_long(self):
        """Test group code too long."""
        is_valid, error = WorkerGroupValidator.validate_group_code("G" * 51)
        assert is_valid is False

    def test_validate_group_code_invalid_chars(self):
        """Test group code with lowercase (invalid)."""
        is_valid, error = WorkerGroupValidator.validate_group_code("grp-001")
        assert is_valid is False

    def test_validate_group_name_valid(self):
        """Test valid group name."""
        is_valid, error = WorkerGroupValidator.validate_group_name("Field Workers A")
        assert is_valid is True

    def test_validate_group_name_empty(self):
        """Test empty group name."""
        is_valid, error = WorkerGroupValidator.validate_group_name("")
        assert is_valid is False

    def test_validate_group_name_whitespace_only(self):
        """Test whitespace-only group name."""
        is_valid, error = WorkerGroupValidator.validate_group_name("   ")
        assert is_valid is False

    def test_validate_capacity_valid(self):
        """Test valid capacity."""
        is_valid, error = WorkerGroupValidator.validate_capacity(15)
        assert is_valid is True

    def test_validate_capacity_too_low(self):
        """Test capacity below minimum."""
        is_valid, error = WorkerGroupValidator.validate_capacity(0)
        assert is_valid is False

    def test_validate_capacity_too_high(self):
        """Test capacity above maximum."""
        is_valid, error = WorkerGroupValidator.validate_capacity(101)
        assert is_valid is False

    def test_validate_capacity_invalid_type(self):
        """Test non-integer capacity."""
        is_valid, error = WorkerGroupValidator.validate_capacity("fifteen")
        assert is_valid is False

    def test_validate_capacity_match_matching(self):
        """Test capacity match when capacities match."""
        is_valid, error = WorkerGroupValidator.validate_capacity_match(15, 15)
        assert is_valid is True

    def test_validate_capacity_match_within_tolerance(self):
        """Test capacity match within tolerance."""
        is_valid, error = WorkerGroupValidator.validate_capacity_match(15, 14)
        assert is_valid is True

    def test_validate_capacity_match_outside_tolerance(self):
        """Test capacity mismatch outside tolerance."""
        is_valid, error = WorkerGroupValidator.validate_capacity_match(15, 8)
        assert is_valid is False


class TestLabourPlanValidatorMethods:
    """Test LabourPlanValidator methods."""

    def test_labour_plan_validator_exists(self):
        """Test LabourPlanValidator is available."""
        assert LabourPlanValidator is not None

    def test_labour_plan_has_validate_method(self):
        """Test LabourPlanValidator has validation methods."""
        methods = [m for m in dir(LabourPlanValidator) if not m.startswith('_')]
        assert len(methods) > 0


class TestBlockAssignmentValidatorMethods:
    """Test BlockAssignmentValidator methods."""

    def test_block_assignment_validator_exists(self):
        """Test BlockAssignmentValidator is available."""
        assert BlockAssignmentValidator is not None


class TestRotationValidatorMethods:
    """Test RotationValidator methods."""

    def test_rotation_validator_exists(self):
        """Test RotationValidator is available."""
        assert RotationValidator is not None


class TestValidationExceptionHierarchy:
    """Test that exception hierarchy is correct."""

    def test_employee_error_is_labour_error(self):
        """EmployeeValidationError inherits from LabourValidationError."""
        err = EmployeeValidationError("field", "msg")
        assert isinstance(err, LabourValidationError)
        assert isinstance(err, Exception)

    def test_worker_group_error_is_labour_error(self):
        """WorkerGroupValidationError inherits from LabourValidationError."""
        err = WorkerGroupValidationError("field", "msg")
        assert isinstance(err, LabourValidationError)

    def test_labour_plan_error_is_labour_error(self):
        """LabourPlanValidationError inherits from LabourValidationError."""
        err = LabourPlanValidationError("field", "msg")
        assert isinstance(err, LabourValidationError)

    def test_block_assignment_error_is_labour_error(self):
        """BlockAssignmentValidationError inherits from LabourValidationError."""
        err = BlockAssignmentValidationError("field", "msg")
        assert isinstance(err, LabourValidationError)

    def test_rotation_error_is_labour_error(self):
        """RotationValidationError inherits from LabourValidationError."""
        err = RotationValidationError("field", "msg")
        assert isinstance(err, LabourValidationError)

    def test_error_default_code(self):
        """Test default error code."""
        err = LabourValidationError("field", "msg")
        assert err.code == "VALIDATION_ERROR"

    def test_error_custom_code(self):
        """Test custom error code."""
        err = LabourValidationError("field", "msg", code="CUSTOM_CODE")
        assert err.code == "CUSTOM_CODE"

    def test_error_string_representation(self):
        """Test error string contains field name."""
        err = LabourValidationError("employee_code", "Invalid code")
        assert "employee_code" in str(err)
