"""
Unit tests for labour_validators.py — no DB or Flask context needed.
"""
import os
import sys
import pytest
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')

from labour_validators import (
    LabourValidationError,
    EmployeeValidator,
    WorkerGroupValidator,
    LabourPlanValidationError,
)


# ═════════════════════════════════════════════════════════════════════════════
# EmployeeValidator
# ═════════════════════════════════════════════════════════════════════════════

class TestEmployeeCodeValidator:
    def test_valid_code(self):
        valid, err = EmployeeValidator.validate_employee_code('EMP001')
        assert valid is True
        assert err is None

    def test_valid_code_with_dashes(self):
        valid, err = EmployeeValidator.validate_employee_code('EMP-001_A')
        assert valid is True

    def test_empty_code_fails(self):
        valid, err = EmployeeValidator.validate_employee_code('')
        assert valid is False

    def test_none_code_fails(self):
        valid, err = EmployeeValidator.validate_employee_code(None)
        assert valid is False

    def test_code_too_long_fails(self):
        long_code = 'A' * 51
        valid, err = EmployeeValidator.validate_employee_code(long_code)
        assert valid is False

    def test_lowercase_fails(self):
        valid, err = EmployeeValidator.validate_employee_code('emp001')
        assert valid is False

    def test_special_chars_fail(self):
        valid, err = EmployeeValidator.validate_employee_code('EMP@001')
        assert valid is False


class TestFullNameValidator:
    def test_valid_name(self):
        valid, err = EmployeeValidator.validate_full_name('John Doe')
        assert valid is True

    def test_empty_name_fails(self):
        valid, err = EmployeeValidator.validate_full_name('')
        assert valid is False

    def test_whitespace_only_fails(self):
        valid, err = EmployeeValidator.validate_full_name('   ')
        assert valid is False

    def test_none_fails(self):
        valid, err = EmployeeValidator.validate_full_name(None)
        assert valid is False

    def test_name_too_long_fails(self):
        valid, err = EmployeeValidator.validate_full_name('A' * 151)
        assert valid is False

    def test_max_length_name_passes(self):
        valid, err = EmployeeValidator.validate_full_name('A' * 150)
        assert valid is True


class TestHireDateValidator:
    def test_valid_date_string(self):
        valid, err = EmployeeValidator.validate_hire_date('2020-01-01')
        assert valid is True

    def test_date_object(self):
        valid, err = EmployeeValidator.validate_hire_date(date(2020, 6, 15))
        assert valid is True

    def test_future_date_fails(self):
        future = (date.today() + timedelta(days=1)).isoformat()
        valid, err = EmployeeValidator.validate_hire_date(future)
        assert valid is False
        assert 'future' in err.lower()

    def test_today_passes(self):
        valid, err = EmployeeValidator.validate_hire_date(date.today().isoformat())
        assert valid is True

    def test_invalid_format_fails(self):
        valid, err = EmployeeValidator.validate_hire_date('01-01-2020')
        assert valid is False

    def test_nonsense_string_fails(self):
        valid, err = EmployeeValidator.validate_hire_date('not-a-date')
        assert valid is False


class TestEmploymentTypeValidator:
    def test_permanent_valid(self):
        valid, err = EmployeeValidator.validate_employment_type('permanent')
        assert valid is True

    def test_casual_valid(self):
        valid, err = EmployeeValidator.validate_employment_type('casual')
        assert valid is True

    def test_seasonal_valid(self):
        valid, err = EmployeeValidator.validate_employment_type('seasonal')
        assert valid is True

    def test_invalid_type_fails(self):
        valid, err = EmployeeValidator.validate_employment_type('freelance')
        assert valid is False

    def test_empty_type_fails(self):
        valid, err = EmployeeValidator.validate_employment_type('')
        assert valid is False

    def test_none_fails(self):
        valid, err = EmployeeValidator.validate_employment_type(None)
        assert valid is False


class TestSkillTypeValidator:
    def test_plucker_valid(self):
        valid, err = EmployeeValidator.validate_skill_type('plucker')
        assert valid is True

    def test_general_valid(self):
        valid, err = EmployeeValidator.validate_skill_type('general')
        assert valid is True

    def test_supervisor_valid(self):
        valid, err = EmployeeValidator.validate_skill_type('supervisor')
        assert valid is True

    def test_driver_valid(self):
        valid, err = EmployeeValidator.validate_skill_type('driver')
        assert valid is True

    def test_invalid_skill_fails(self):
        valid, err = EmployeeValidator.validate_skill_type('mechanic')
        assert valid is False


class TestGenderValidator:
    def test_male_valid(self):
        valid, err = EmployeeValidator.validate_gender('M')
        assert valid is True

    def test_female_valid(self):
        valid, err = EmployeeValidator.validate_gender('F')
        assert valid is True

    def test_other_valid(self):
        valid, err = EmployeeValidator.validate_gender('O')
        assert valid is True

    def test_none_is_valid(self):
        valid, err = EmployeeValidator.validate_gender(None)
        assert valid is True

    def test_invalid_gender_fails(self):
        valid, err = EmployeeValidator.validate_gender('X')
        assert valid is False

    def test_lowercase_fails(self):
        valid, err = EmployeeValidator.validate_gender('m')
        assert valid is False


class TestDailyWageValidator:
    def test_valid_wage(self):
        valid, err = EmployeeValidator.validate_daily_wage(1500.00)
        assert valid is True

    def test_none_is_valid(self):
        valid, err = EmployeeValidator.validate_daily_wage(None)
        assert valid is True

    def test_zero_wage_fails(self):
        valid, err = EmployeeValidator.validate_daily_wage(0)
        assert valid is False

    def test_negative_wage_fails(self):
        valid, err = EmployeeValidator.validate_daily_wage(-100)
        assert valid is False

    def test_over_max_fails(self):
        valid, err = EmployeeValidator.validate_daily_wage(1_000_000)
        assert valid is False

    def test_string_number_passes(self):
        valid, err = EmployeeValidator.validate_daily_wage('500.50')
        assert valid is True

    def test_non_numeric_string_fails(self):
        valid, err = EmployeeValidator.validate_daily_wage('abc')
        assert valid is False


class TestValidateCreateRequest:
    def _good_data(self):
        return {
            'estate_id': 'abc123',
            'employee_code': 'EMP001',
            'full_name': 'John Doe',
            'hire_date': '2020-01-01',
            'employment_type': 'permanent',
            'skill_type': 'plucker',
        }

    def test_valid_data_no_errors(self):
        errors = EmployeeValidator.validate_create_request(self._good_data())
        assert errors == {}

    def test_missing_required_field_returns_error(self):
        data = self._good_data()
        del data['employee_code']
        errors = EmployeeValidator.validate_create_request(data)
        assert 'employee_code' in errors

    def test_invalid_skill_type_returns_error(self):
        data = self._good_data()
        data['skill_type'] = 'wizard'
        errors = EmployeeValidator.validate_create_request(data)
        assert 'skill_type' in errors

    def test_invalid_hire_date_returns_error(self):
        data = self._good_data()
        data['hire_date'] = 'tomorrow'
        errors = EmployeeValidator.validate_create_request(data)
        assert 'hire_date' in errors


class TestValidateUpdateRequest:
    def test_valid_update_no_errors(self):
        errors = EmployeeValidator.validate_update_request({'full_name': 'Jane Smith'})
        assert errors == {}

    def test_unknown_field_returns_error(self):
        errors = EmployeeValidator.validate_update_request({'unknown_field': 'value'})
        assert 'unknown_field' in errors

    def test_invalid_is_active_type_fails(self):
        errors = EmployeeValidator.validate_update_request({'is_active': 'yes'})
        assert 'is_active' in errors

    def test_valid_is_active_bool_passes(self):
        errors = EmployeeValidator.validate_update_request({'is_active': False})
        assert 'is_active' not in errors


class TestEmployeeCodeUniqueness:
    def test_unique_code_passes(self):
        valid, err = EmployeeValidator.validate_employee_code_unique(
            'EMP001', 'estate-1', ['EMP002', 'EMP003']
        )
        assert valid is True

    def test_duplicate_code_fails(self):
        valid, err = EmployeeValidator.validate_employee_code_unique(
            'EMP001', 'estate-1', ['EMP001', 'EMP002']
        )
        assert valid is False
        assert 'EMP001' in err


# ═════════════════════════════════════════════════════════════════════════════
# WorkerGroupValidator (smoke tests)
# ═════════════════════════════════════════════════════════════════════════════

class TestWorkerGroupValidator:
    def test_validator_class_exists(self):
        assert WorkerGroupValidator is not None

    def test_min_capacity_constant(self):
        assert WorkerGroupValidator.MIN_CAPACITY >= 1

    def test_max_capacity_constant(self):
        assert WorkerGroupValidator.MAX_CAPACITY > WorkerGroupValidator.MIN_CAPACITY


# ═════════════════════════════════════════════════════════════════════════════
# Custom exceptions
# ═════════════════════════════════════════════════════════════════════════════

class TestCustomExceptions:
    def test_labour_validation_error_stores_field(self):
        err = LabourValidationError('my_field', 'bad value')
        assert err.field == 'my_field'
        assert err.message == 'bad value'
        assert 'my_field' in str(err)

    def test_labour_validation_error_default_code(self):
        err = LabourValidationError('f', 'm')
        assert err.code == 'VALIDATION_ERROR'

    def test_labour_validation_error_custom_code(self):
        err = LabourValidationError('f', 'm', code='REQUIRED')
        assert err.code == 'REQUIRED'

    def test_is_exception(self):
        with pytest.raises(LabourValidationError):
            raise LabourValidationError('f', 'm')
