"""Comprehensive tests for labour_serializers - targets uncovered lines."""
import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from labour_serializers import (
    serialize_uuid, serialize_date, serialize_decimal,
    serialize_int, serialize_bool, serialize_string,
    EmployeeSerializer, WorkerGroupSerializer, WorkerGroupMemberSerializer,
    RotationCycleSerializer, LabourPlanSerializer
)


class TestWorkerGroupSerializerMethods:
    """Test WorkerGroupSerializer class."""

    def _group_row(self):
        return {
            'id': UUID('12345678-1234-5678-1234-567812345678'),
            'estate_id': UUID('87654321-4321-8765-4321-876543218765'),
            'group_code': 'GRP-001',
            'group_name': 'Field Workers A',
            'supervisor_id': None,
            'capacity': 15,
            'is_active': True,
            'created_at': datetime(2023, 6, 15),
            'updated_at': datetime(2024, 6, 15),
        }

    def test_serialize_group(self):
        """Test serializing a single worker group."""
        row = self._group_row()
        result = WorkerGroupSerializer.serialize_group(row)

        assert result['group_code'] == 'GRP-001'
        assert result['group_name'] == 'Field Workers A'
        assert result['capacity'] == 15
        assert result['is_active'] is True

    def test_serialize_group_with_metrics(self):
        """Test serializing group with headcount and fill metrics."""
        row = {**self._group_row(), 'headcount': 10, 'supervisor_name': 'Alice'}
        result = WorkerGroupSerializer.serialize_group_with_metrics(row)

        assert result['headcount'] == 10
        assert result['vacancy'] == 5  # 15 - 10
        assert result['fill_rate_pct'] == pytest.approx(66.7, rel=0.01)

    def test_serialize_group_with_metrics_full(self):
        """Test group with full capacity."""
        row = {**self._group_row(), 'headcount': 15}
        result = WorkerGroupSerializer.serialize_group_with_metrics(row)

        assert result['fill_rate_pct'] == 100.0
        assert result['vacancy'] == 0

    def test_serialize_group_with_metrics_empty(self):
        """Test group with zero capacity."""
        row = {**self._group_row(), 'capacity': 0, 'headcount': 0}
        result = WorkerGroupSerializer.serialize_group_with_metrics(row)

        assert result['fill_rate_pct'] == 0

    def test_serialize_groups(self):
        """Test serializing multiple groups."""
        rows = [self._group_row(), self._group_row()]
        result = WorkerGroupSerializer.serialize_groups(rows)

        assert len(result) == 2


class TestWorkerGroupMemberSerializer:
    """Test WorkerGroupMemberSerializer class."""

    def _member_row(self):
        return {
            'id': UUID('12345678-1234-5678-1234-567812345678'),
            'group_id': UUID('11111111-1111-1111-1111-111111111111'),
            'employee_id': UUID('22222222-2222-2222-2222-222222222222'),
            'joined_date': date(2023, 6, 15),
            'left_date': None,
            'is_active': True,
            'created_at': datetime(2023, 6, 15),
            'updated_at': datetime(2024, 6, 15),
            'employee_code': 'EMP-001',
            'full_name': 'John Doe',
            'skill_type': 'plucker',
        }

    def test_serialize_member(self):
        """Test serializing a single group member."""
        result = WorkerGroupMemberSerializer.serialize_member(self._member_row())

        assert result['employee_code'] == 'EMP-001'
        assert result['full_name'] == 'John Doe'
        assert result['skill_type'] == 'plucker'
        assert result['is_active'] is True
        assert result['left_date'] is None

    def test_serialize_members(self):
        """Test serializing multiple group members."""
        rows = [self._member_row(), self._member_row()]
        result = WorkerGroupMemberSerializer.serialize_members(rows)

        assert len(result) == 2


class TestRotationCycleSerializer:
    """Test RotationCycleSerializer class."""

    def _cycle_row(self):
        return {
            'id': UUID('12345678-1234-5678-1234-567812345678'),
            'estate_id': UUID('87654321-4321-8765-4321-876543218765'),
            'cycle_name': 'Cycle A',
            'total_rounds': 12,
            'current_round': 6,
            'is_active': True,
            'created_by': None,
            'created_at': datetime(2023, 6, 15),
            'updated_at': datetime(2024, 6, 15),
        }

    def test_serialize_cycle(self):
        """Test serializing a single rotation cycle."""
        result = RotationCycleSerializer.serialize_cycle(self._cycle_row())

        assert result['cycle_name'] == 'Cycle A'
        assert result['total_rounds'] == 12
        assert result['current_round'] == 6
        assert result['is_active'] is True

    def test_serialize_cycle_with_matrix(self):
        """Test serializing cycle with rotation matrix."""
        matrix = {1: [{'block_id': 'b1', 'group_id': 'g1'}]}
        result = RotationCycleSerializer.serialize_cycle_with_matrix(self._cycle_row(), matrix)

        assert result['cycle_name'] == 'Cycle A'
        assert result['matrix'] == matrix
        assert result['completion_pct'] == 50.0  # 6/12 * 100
        assert result['rounds_remaining'] == 6   # 12 - 6

    def test_serialize_cycle_with_matrix_zero_rounds(self):
        """Test cycle with zero total rounds."""
        row = {**self._cycle_row(), 'total_rounds': 0, 'current_round': 0}
        result = RotationCycleSerializer.serialize_cycle_with_matrix(row, {})

        assert result['completion_pct'] == 0
        assert result['rounds_remaining'] == 0


class TestLabourPlanSerializer:
    """Test LabourPlanSerializer class."""

    def _plan_row(self):
        return {
            'id': UUID('12345678-1234-5678-1234-567812345678'),
            'estate_id': UUID('87654321-4321-8765-4321-876543218765'),
            'period_start': date(2024, 6, 1),
            'total_workers': 50,
            'target_kg': Decimal('5000.00'),
            'status': 'published',
            'notes': None,
            'created_by': None,
            'created_at': datetime(2024, 5, 15),
            'updated_at': datetime(2024, 6, 1),
            'estate_name': 'Test Estate',
            'cycle_name': 'Cycle A',
            'current_round': 3,
            'total_rounds': 12,
            'blocks_assigned': 5,
            'expected_total_kg': Decimal('5000.00'),
            'actual_total_kg': Decimal('4800.00'),
        }

    def test_serialize_plan(self):
        """Test serializing a single labour plan."""
        result = LabourPlanSerializer.serialize_plan(self._plan_row())

        assert result['total_workers'] == 50
        assert result['target_kg'] == 5000.0
        assert result['status'] == 'published'
        assert result['estate_name'] == 'Test Estate'

    def test_serialize_plan_with_assignments(self):
        """Test serializing plan with assignments."""
        assignments = [
            {'status': 'completed', 'block_id': 'b1'},
            {'status': 'in_progress', 'block_id': 'b2'},
        ]
        result = LabourPlanSerializer.serialize_plan_with_assignments(
            self._plan_row(), assignments
        )

        assert len(result['assignments']) == 2
        assert result['overall_efficiency_pct'] == pytest.approx(96.0)
        assert result['completion_status'] == 50.0  # 1/2 completed

    def test_serialize_plan_with_assignments_no_actual(self):
        """Test plan efficiency when no actual kg recorded."""
        row = {**self._plan_row(), 'actual_total_kg': None}
        result = LabourPlanSerializer.serialize_plan_with_assignments(row, [])

        assert result['overall_efficiency_pct'] is None
        assert result['completion_status'] == 0

    def test_serialize_plans(self):
        """Test serializing multiple plans."""
        rows = [self._plan_row(), self._plan_row()]
        result = LabourPlanSerializer.serialize_plans(rows)

        assert len(result) == 2


class TestHelperEdgeCases:
    """Test edge cases in helper functions."""

    def test_serialize_decimal_from_float(self):
        """Test Decimal serialization from float."""
        result = serialize_decimal(100.5)
        assert result == 100.5
        assert isinstance(result, float)

    def test_serialize_string_non_string(self):
        """Test string serialization from non-string."""
        result = serialize_string(12345)
        assert result == '12345'

    def test_serialize_int_from_float(self):
        """Test int serialization from float."""
        result = serialize_int(100.9)
        assert result == 100

    def test_serialize_uuid_from_string(self):
        """Test UUID serialization from string UUID."""
        uuid_str = '12345678-1234-5678-1234-567812345678'
        result = serialize_uuid(uuid_str)
        assert result == uuid_str
