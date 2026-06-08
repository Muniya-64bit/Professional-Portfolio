"""Tests for remaining labour_serializers classes - BlockAssignment, EmployeeDay, RotationMatrix, Efficiency."""
import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from labour_serializers import (
    BlockAssignmentSerializer, EmployeeDayAssignmentSerializer,
    RotationMatrixSerializer, EfficiencyReportSerializer
)


class TestBlockAssignmentSerializer:
    """Test BlockAssignmentSerializer class."""

    def _row(self, expected=Decimal('1000.00'), actual=Decimal('960.00')):
        return {
            'id': UUID('12345678-1234-5678-1234-567812345678'),
            'labour_plan_id': UUID('11111111-1111-1111-1111-111111111111'),
            'block_id': UUID('22222222-2222-2222-2222-222222222222'),
            'worker_group_id': UUID('33333333-3333-3333-3333-333333333333'),
            'assignment_date': date(2024, 6, 15),
            'rotation_cycle_id': None,
            'rotation_round': 3,
            'is_manual_override': False,
            'original_group_id': None,
            'override_reason': None,
            'overridden_by': None,
            'overridden_at': None,
            'expected_yield_kg': expected,
            'actual_yield_kg': actual,
            'plucking_round_number': 1,
            'status': 'completed',
            'notes': None,
            'created_at': datetime(2024, 6, 1),
            'updated_at': datetime(2024, 6, 16),
            'block_code': 'BLK-001',
            'worker_capacity': 15,
            'group_name': 'Group A',
            'group_code': 'GRP-001',
            'group_capacity': 15,
            'original_group_name': None,
        }

    def test_serialize_assignment_basic(self):
        row = self._row()
        result = BlockAssignmentSerializer.serialize_assignment(row)

        assert result['status'] == 'completed'
        assert result['block_code'] == 'BLK-001'
        assert result['rotation_round'] == 3

    def test_serialize_assignment_efficiency_calculated(self):
        row = self._row(expected=Decimal('1000.00'), actual=Decimal('960.00'))
        result = BlockAssignmentSerializer.serialize_assignment(row)

        assert result['efficiency_pct'] == 96.0
        assert result['variance_kg'] == -40.0

    def test_serialize_assignment_over_target(self):
        row = self._row(expected=Decimal('1000.00'), actual=Decimal('1100.00'))
        result = BlockAssignmentSerializer.serialize_assignment(row)

        assert result['efficiency_pct'] == 110.0
        assert result['variance_kg'] == 100.0

    def test_serialize_assignment_no_actual(self):
        row = self._row(expected=Decimal('1000.00'), actual=None)
        result = BlockAssignmentSerializer.serialize_assignment(row)

        assert result['efficiency_pct'] is None
        assert result['variance_kg'] is None

    def test_serialize_assignment_no_expected(self):
        row = self._row(expected=None, actual=Decimal('500.00'))
        result = BlockAssignmentSerializer.serialize_assignment(row)

        assert result['efficiency_pct'] is None

    def test_serialize_assignments(self):
        rows = [self._row(), self._row()]
        result = BlockAssignmentSerializer.serialize_assignments(rows)
        assert len(result) == 2

    def test_serialize_assignment_with_capacity_check_met(self):
        row = {**self._row(), 'assigned_workers': 15}  # equals capacity
        result = BlockAssignmentSerializer.serialize_assignment_with_capacity_check(row)
        assert result['capacity_met'] is True

    def test_serialize_assignment_with_capacity_check_not_met(self):
        row = {**self._row(), 'assigned_workers': 10}  # less than capacity
        result = BlockAssignmentSerializer.serialize_assignment_with_capacity_check(row)
        assert result['capacity_met'] is False


class TestEmployeeDayAssignmentSerializer:
    """Test EmployeeDayAssignmentSerializer class."""

    def _row(self):
        return {
            'id': UUID('12345678-1234-5678-1234-567812345678'),
            'block_assignment_id': UUID('11111111-1111-1111-1111-111111111111'),
            'employee_id': UUID('22222222-2222-2222-2222-222222222222'),
            'assignment_type': 'group',
            'kg_collected': Decimal('32.5'),
            'added_by': None,
            'reason': None,
            'created_at': datetime(2024, 6, 15),
            'updated_at': datetime(2024, 6, 15),
            'employee_code': 'EMP-001',
            'full_name': 'Jane Doe',
            'skill_type': 'plucker',
        }

    def test_serialize_employee_assignment(self):
        result = EmployeeDayAssignmentSerializer.serialize_assignment(self._row())

        assert result['assignment_type'] == 'group'
        assert result['kg_collected'] == 32.5
        assert result['employee_code'] == 'EMP-001'
        assert result['full_name'] == 'Jane Doe'

    def test_serialize_employee_assignments(self):
        rows = [self._row(), self._row()]
        result = EmployeeDayAssignmentSerializer.serialize_assignments(rows)
        assert len(result) == 2


class TestRotationMatrixSerializer:
    """Test RotationMatrixSerializer class."""

    def test_build_matrix_basic(self):
        rows = [
            {'round_number': 1, 'block_code': 'BLK-001', 'group_code': 'GRP-A',
             'block_id': UUID('11111111-1111-1111-1111-111111111111'),
             'worker_group_id': UUID('22222222-2222-2222-2222-222222222222')},
            {'round_number': 1, 'block_code': 'BLK-002', 'group_code': 'GRP-B',
             'block_id': UUID('33333333-3333-3333-3333-333333333333'),
             'worker_group_id': UUID('44444444-4444-4444-4444-444444444444')},
            {'round_number': 2, 'block_code': 'BLK-001', 'group_code': 'GRP-B',
             'block_id': UUID('11111111-1111-1111-1111-111111111111'),
             'worker_group_id': UUID('44444444-4444-4444-4444-444444444444')},
        ]
        matrix = RotationMatrixSerializer.build_matrix(rows)

        assert 1 in matrix
        assert 2 in matrix
        assert len(matrix[1]) == 2
        assert len(matrix[2]) == 1

    def test_build_matrix_sorted_by_round(self):
        rows = [
            {'round_number': 3, 'block_code': 'BLK-001', 'group_code': 'GRP-A',
             'block_id': UUID('11111111-1111-1111-1111-111111111111'),
             'worker_group_id': UUID('22222222-2222-2222-2222-222222222222')},
            {'round_number': 1, 'block_code': 'BLK-001', 'group_code': 'GRP-B',
             'block_id': UUID('11111111-1111-1111-1111-111111111111'),
             'worker_group_id': UUID('44444444-4444-4444-4444-444444444444')},
        ]
        matrix = RotationMatrixSerializer.build_matrix(rows)
        assert list(matrix.keys()) == [1, 3]

    def test_build_matrix_empty(self):
        matrix = RotationMatrixSerializer.build_matrix([])
        assert matrix == {}


class TestEfficiencyReportSerializer:
    """Test EfficiencyReportSerializer class."""

    def _plan_row(self):
        return {
            'period_start': date(2024, 6, 1),
            'estate_name': 'Test Estate',
            'expected_total_kg': Decimal('5000.00'),
            'actual_total_kg': Decimal('4800.00'),
            'total_blocks': 10,
            'blocks_completed': 8,
        }

    def test_serialize_plan_efficiency(self):
        result = EfficiencyReportSerializer.serialize_plan_efficiency(self._plan_row())

        assert result['estate_name'] == 'Test Estate'
        assert result['efficiency_pct'] == pytest.approx(96.0)
        assert result['variance_kg'] == pytest.approx(-200.0)
        assert result['blocks_pending'] == 2

    def test_serialize_plan_efficiency_no_actual(self):
        row = {**self._plan_row(), 'actual_total_kg': None}
        result = EfficiencyReportSerializer.serialize_plan_efficiency(row)

        assert result['efficiency_pct'] is None
        assert result['variance_kg'] is None

    def test_serialize_block_efficiency(self):
        rows = [
            {'block_code': 'BLK-001', 'block_id': UUID('11111111-1111-1111-1111-111111111111'),
             'group_code': 'GRP-A', 'group_name': 'Group A',
             'expected_yield_kg': Decimal('500.00'), 'actual_yield_kg': Decimal('480.00'),
             'status': 'completed', 'is_manual_override': False},
            {'block_code': 'BLK-002', 'block_id': UUID('22222222-2222-2222-2222-222222222222'),
             'group_code': 'GRP-B', 'group_name': 'Group B',
             'expected_yield_kg': Decimal('500.00'), 'actual_yield_kg': None,
             'status': 'in_progress', 'is_manual_override': False},
        ]
        result = EfficiencyReportSerializer.serialize_block_efficiency(rows)

        assert len(result) == 2
        assert result[0]['efficiency_pct'] == 96.0
        assert result[1]['efficiency_pct'] is None  # no actual
