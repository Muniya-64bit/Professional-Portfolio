"""
Unit tests for labour_serializers.py — pure Python, no DB or Flask needed.
"""
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')

from labour_serializers import (
    serialize_uuid, serialize_date, serialize_decimal,
    serialize_int, serialize_bool, serialize_string,
    EmployeeSerializer, WorkerGroupSerializer,
)


# ═════════════════════════════════════════════════════════════════════════════
# Primitive serializers
# ═════════════════════════════════════════════════════════════════════════════

class TestSerializeUuid:
    def test_uuid_to_string(self):
        uid = UUID('12345678-1234-5678-1234-567812345678')
        assert serialize_uuid(uid) == '12345678-1234-5678-1234-567812345678'

    def test_none_returns_none(self):
        assert serialize_uuid(None) is None

    def test_string_passthrough(self):
        s = str(uuid4())
        assert serialize_uuid(s) == s


class TestSerializeDate:
    def test_date_to_iso(self):
        d = date(2024, 6, 15)
        assert serialize_date(d) == '2024-06-15'

    def test_datetime_to_iso(self):
        dt = datetime(2024, 6, 15, 10, 30, 0)
        result = serialize_date(dt)
        assert '2024-06-15' in result

    def test_none_returns_none(self):
        assert serialize_date(None) is None

    def test_string_passthrough(self):
        assert serialize_date('2024-01-01') == '2024-01-01'


class TestSerializeDecimal:
    def test_decimal_to_float(self):
        assert serialize_decimal(Decimal('123.45')) == 123.45

    def test_none_returns_none(self):
        assert serialize_decimal(None) is None

    def test_integer_decimal(self):
        assert serialize_decimal(Decimal('100')) == 100.0
        assert isinstance(serialize_decimal(Decimal('100')), float)


class TestSerializeInt:
    def test_int_passthrough(self):
        assert serialize_int(42) == 42

    def test_none_returns_none(self):
        assert serialize_int(None) is None

    def test_float_truncated(self):
        assert serialize_int(3.9) == 3


class TestSerializeBool:
    def test_true_returns_true(self):
        assert serialize_bool(True) is True

    def test_false_returns_false(self):
        assert serialize_bool(False) is False

    def test_none_returns_false(self):
        assert serialize_bool(None) is False

    def test_truthy_int(self):
        assert serialize_bool(1) is True

    def test_zero_is_false(self):
        assert serialize_bool(0) is False


class TestSerializeString:
    def test_string_passthrough(self):
        assert serialize_string('hello') == 'hello'

    def test_strips_whitespace(self):
        assert serialize_string('  hello  ') == 'hello'

    def test_none_returns_none(self):
        assert serialize_string(None) is None

    def test_int_to_string(self):
        assert serialize_string(42) == '42'


# ═════════════════════════════════════════════════════════════════════════════
# EmployeeSerializer
# ═════════════════════════════════════════════════════════════════════════════

class TestEmployeeSerializer:
    def _sample_row(self):
        uid = uuid4()
        estate_uid = uuid4()
        return {
            'id': uid,
            'estate_id': estate_uid,
            'employee_code': 'EMP001',
            'full_name': 'John Doe',
            'gender': 'M',
            'national_id': 'NID001',
            'hire_date': date(2020, 1, 1),
            'employment_type': 'permanent',
            'skill_type': 'plucker',
            'daily_wage_lkr': Decimal('1500.00'),
            'is_active': True,
            'notes': None,
            'created_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 6, 1),
        }

    def test_returns_dict(self):
        row = self._sample_row()
        result = EmployeeSerializer.serialize_employee(row)
        assert isinstance(result, dict)

    def test_id_is_string(self):
        row = self._sample_row()
        result = EmployeeSerializer.serialize_employee(row)
        assert isinstance(result['id'], str)

    def test_hire_date_is_iso_string(self):
        row = self._sample_row()
        result = EmployeeSerializer.serialize_employee(row)
        assert result['hire_date'] == '2020-01-01'

    def test_wage_is_float(self):
        row = self._sample_row()
        result = EmployeeSerializer.serialize_employee(row)
        assert isinstance(result['daily_wage_lkr'], float)

    def test_none_notes_stays_none(self):
        row = self._sample_row()
        result = EmployeeSerializer.serialize_employee(row)
        assert result['notes'] is None

    def test_is_active_is_bool(self):
        row = self._sample_row()
        result = EmployeeSerializer.serialize_employee(row)
        assert result['is_active'] is True

    def test_serialize_employees_returns_list(self):
        rows = [self._sample_row(), self._sample_row()]
        result = EmployeeSerializer.serialize_employees(rows)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_serialize_empty_list(self):
        result = EmployeeSerializer.serialize_employees([])
        assert result == []

    def test_missing_optional_field_defaults_to_none(self):
        row = {
            'id': uuid4(),
            'estate_id': uuid4(),
            'employee_code': 'EMP002',
            'full_name': 'Jane',
            'hire_date': date(2021, 3, 1),
        }
        result = EmployeeSerializer.serialize_employee(row)
        assert result['gender'] is None
        assert result['notes'] is None


# ═════════════════════════════════════════════════════════════════════════════
# WorkerGroupSerializer (smoke tests)
# ═════════════════════════════════════════════════════════════════════════════

class TestWorkerGroupSerializer:
    def test_class_has_serialize_method(self):
        assert hasattr(WorkerGroupSerializer, 'serialize_group')

    def test_serialize_basic_row(self):
        row = {
            'id': uuid4(),
            'estate_id': uuid4(),
            'group_code': 'GRP001',
            'group_name': 'Team Alpha',
            'capacity': 15,
            'is_active': True,
            'created_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 6, 1),
        }
        result = WorkerGroupSerializer.serialize_group(row)
        assert isinstance(result, dict)
        assert result['group_name'] == 'Team Alpha'

    def test_serialize_groups_returns_list(self):
        rows = [
            {'id': uuid4(), 'estate_id': uuid4(), 'group_code': 'G1', 'group_name': 'G1', 'capacity': 10},
            {'id': uuid4(), 'estate_id': uuid4(), 'group_code': 'G2', 'group_name': 'G2', 'capacity': 12},
        ]
        result = WorkerGroupSerializer.serialize_groups(rows)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_serialize_group_with_metrics_fill_rate(self):
        row = {
            'id': uuid4(),
            'estate_id': uuid4(),
            'group_code': 'G3',
            'group_name': 'Team C',
            'capacity': 10,
            'headcount': 8,
            'is_active': True,
        }
        result = WorkerGroupSerializer.serialize_group_with_metrics(row)
        assert result['fill_rate_pct'] == 80.0
        assert result['vacancy'] == 2
