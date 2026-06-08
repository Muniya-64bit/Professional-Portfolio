"""Tests for LabourPlanValidator, BlockAssignmentValidator, RotationValidator."""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from labour_validators import (
    LabourPlanValidator, BlockAssignmentValidator, RotationValidator
)


class TestLabourPlanValidatorMethods:
    """Test LabourPlanValidator static methods."""

    # --- validate_period_start ---

    def test_validate_period_start_valid(self):
        is_valid, err = LabourPlanValidator.validate_period_start("2024-06-01")
        assert is_valid is True and err is None

    def test_validate_period_start_date_object(self):
        is_valid, err = LabourPlanValidator.validate_period_start(date(2024, 6, 1))
        assert is_valid is True

    def test_validate_period_start_not_first_of_month(self):
        is_valid, err = LabourPlanValidator.validate_period_start("2024-06-15")
        assert is_valid is False
        assert "1st of month" in err

    def test_validate_period_start_invalid_string(self):
        is_valid, err = LabourPlanValidator.validate_period_start("not-a-date")
        assert is_valid is False

    def test_validate_period_start_wrong_type(self):
        is_valid, err = LabourPlanValidator.validate_period_start(12345)
        assert is_valid is False

    # --- validate_status ---

    def test_validate_status_draft(self):
        is_valid, err = LabourPlanValidator.validate_status("draft")
        assert is_valid is True

    def test_validate_status_published(self):
        is_valid, err = LabourPlanValidator.validate_status("published")
        assert is_valid is True

    def test_validate_status_in_progress(self):
        is_valid, err = LabourPlanValidator.validate_status("in_progress")
        assert is_valid is True

    def test_validate_status_completed(self):
        is_valid, err = LabourPlanValidator.validate_status("completed")
        assert is_valid is True

    def test_validate_status_archived(self):
        is_valid, err = LabourPlanValidator.validate_status("archived")
        assert is_valid is True

    def test_validate_status_invalid(self):
        is_valid, err = LabourPlanValidator.validate_status("pending")
        assert is_valid is False

    def test_validate_status_none(self):
        is_valid, err = LabourPlanValidator.validate_status(None)
        assert is_valid is False

    # --- validate_status_transition ---

    def test_valid_transition_draft_to_published(self):
        is_valid, err = LabourPlanValidator.validate_status_transition("draft", "published")
        assert is_valid is True

    def test_valid_transition_published_to_in_progress(self):
        is_valid, err = LabourPlanValidator.validate_status_transition("published", "in_progress")
        assert is_valid is True

    def test_valid_transition_in_progress_to_completed(self):
        is_valid, err = LabourPlanValidator.validate_status_transition("in_progress", "completed")
        assert is_valid is True

    def test_valid_transition_completed_to_archived(self):
        is_valid, err = LabourPlanValidator.validate_status_transition("completed", "archived")
        assert is_valid is True

    def test_invalid_transition_draft_to_completed(self):
        is_valid, err = LabourPlanValidator.validate_status_transition("draft", "completed")
        assert is_valid is False

    def test_invalid_transition_archived_to_draft(self):
        is_valid, err = LabourPlanValidator.validate_status_transition("archived", "draft")
        assert is_valid is False

    def test_invalid_transition_unknown_status(self):
        is_valid, err = LabourPlanValidator.validate_status_transition("unknown", "draft")
        assert is_valid is False

    # --- validate_total_workers ---

    def test_validate_total_workers_valid(self):
        is_valid, err = LabourPlanValidator.validate_total_workers(50)
        assert is_valid is True

    def test_validate_total_workers_zero(self):
        is_valid, err = LabourPlanValidator.validate_total_workers(0)
        assert is_valid is True  # min is 0

    def test_validate_total_workers_negative(self):
        is_valid, err = LabourPlanValidator.validate_total_workers(-1)
        assert is_valid is False

    def test_validate_total_workers_invalid_type(self):
        is_valid, err = LabourPlanValidator.validate_total_workers("fifty")
        assert is_valid is False

    # --- validate_target_kg ---

    def test_validate_target_kg_valid(self):
        is_valid, err = LabourPlanValidator.validate_target_kg(Decimal("5000"))
        assert is_valid is True

    def test_validate_target_kg_zero(self):
        is_valid, err = LabourPlanValidator.validate_target_kg(0)
        assert is_valid is True

    def test_validate_target_kg_negative(self):
        is_valid, err = LabourPlanValidator.validate_target_kg(-100)
        assert is_valid is False

    def test_validate_target_kg_invalid(self):
        is_valid, err = LabourPlanValidator.validate_target_kg("five thousand")
        assert is_valid is False

    # --- validate_create_request ---

    def test_validate_create_request_valid(self):
        data = {'estate_id': 'some-uuid', 'period_start': '2024-06-01'}
        errors = LabourPlanValidator.validate_create_request(data)
        assert errors == {}

    def test_validate_create_request_missing_estate_id(self):
        data = {'period_start': '2024-06-01'}
        errors = LabourPlanValidator.validate_create_request(data)
        assert 'estate_id' in errors

    def test_validate_create_request_missing_period_start(self):
        data = {'estate_id': 'some-uuid'}
        errors = LabourPlanValidator.validate_create_request(data)
        assert 'period_start' in errors

    def test_validate_create_request_invalid_period(self):
        data = {'estate_id': 'some-uuid', 'period_start': '2024-06-15'}
        errors = LabourPlanValidator.validate_create_request(data)
        assert 'period_start' in errors

    def test_validate_create_request_with_valid_status(self):
        data = {'estate_id': 'some-uuid', 'period_start': '2024-06-01', 'status': 'draft'}
        errors = LabourPlanValidator.validate_create_request(data)
        assert errors == {}

    def test_validate_create_request_with_invalid_status(self):
        data = {'estate_id': 'some-uuid', 'period_start': '2024-06-01', 'status': 'bad'}
        errors = LabourPlanValidator.validate_create_request(data)
        assert 'status' in errors

    # --- validate_update_request ---

    def test_validate_update_request_valid(self):
        data = {'status': 'published', 'total_workers': 50}
        errors = LabourPlanValidator.validate_update_request(data)
        assert errors == {}

    def test_validate_update_request_unknown_field(self):
        data = {'unknown': 'value'}
        errors = LabourPlanValidator.validate_update_request(data)
        assert 'unknown' in errors

    def test_validate_update_request_invalid_total_workers(self):
        data = {'total_workers': -5}
        errors = LabourPlanValidator.validate_update_request(data)
        assert 'total_workers' in errors

    def test_validate_update_request_invalid_target_kg(self):
        data = {'target_kg': -100}
        errors = LabourPlanValidator.validate_update_request(data)
        assert 'target_kg' in errors


class TestBlockAssignmentValidatorMethods:
    """Test BlockAssignmentValidator static methods."""

    def test_validate_assignment_date_valid(self):
        is_valid, err = BlockAssignmentValidator.validate_assignment_date("2024-06-15")
        assert is_valid is True

    def test_validate_assignment_date_object(self):
        is_valid, err = BlockAssignmentValidator.validate_assignment_date(date(2024, 6, 15))
        assert is_valid is True

    def test_validate_assignment_date_invalid(self):
        is_valid, err = BlockAssignmentValidator.validate_assignment_date("not-a-date")
        assert is_valid is False

    def test_validate_assignment_date_wrong_type(self):
        is_valid, err = BlockAssignmentValidator.validate_assignment_date(123)
        assert is_valid is False

    def test_validate_status_scheduled(self):
        is_valid, err = BlockAssignmentValidator.validate_status("scheduled")
        assert is_valid is True

    def test_validate_status_in_progress(self):
        is_valid, err = BlockAssignmentValidator.validate_status("in_progress")
        assert is_valid is True

    def test_validate_status_completed(self):
        is_valid, err = BlockAssignmentValidator.validate_status("completed")
        assert is_valid is True

    def test_validate_status_cancelled(self):
        is_valid, err = BlockAssignmentValidator.validate_status("cancelled")
        assert is_valid is True

    def test_validate_status_invalid(self):
        is_valid, err = BlockAssignmentValidator.validate_status("done")
        assert is_valid is False

    def test_validate_status_none(self):
        is_valid, err = BlockAssignmentValidator.validate_status(None)
        assert is_valid is False

    def test_valid_transition_scheduled_to_in_progress(self):
        is_valid, err = BlockAssignmentValidator.validate_status_transition("scheduled", "in_progress")
        assert is_valid is True

    def test_valid_transition_in_progress_to_completed(self):
        is_valid, err = BlockAssignmentValidator.validate_status_transition("in_progress", "completed")
        assert is_valid is True

    def test_valid_transition_scheduled_to_cancelled(self):
        is_valid, err = BlockAssignmentValidator.validate_status_transition("scheduled", "cancelled")
        assert is_valid is True

    def test_invalid_transition_completed_to_scheduled(self):
        is_valid, err = BlockAssignmentValidator.validate_status_transition("completed", "scheduled")
        assert is_valid is False

    def test_invalid_transition_unknown_status(self):
        is_valid, err = BlockAssignmentValidator.validate_status_transition("unknown", "scheduled")
        assert is_valid is False

    def test_validate_yield_kg_valid(self):
        is_valid, err = BlockAssignmentValidator.validate_yield_kg(Decimal("500.5"))
        assert is_valid is True

    def test_validate_yield_kg_zero(self):
        is_valid, err = BlockAssignmentValidator.validate_yield_kg(0)
        assert is_valid is True

    def test_validate_yield_kg_negative(self):
        is_valid, err = BlockAssignmentValidator.validate_yield_kg(-1)
        assert is_valid is False

    def test_validate_yield_kg_too_large(self):
        is_valid, err = BlockAssignmentValidator.validate_yield_kg(Decimal("9999999.999"))
        assert is_valid is False

    def test_validate_yield_kg_invalid(self):
        is_valid, err = BlockAssignmentValidator.validate_yield_kg("five hundred")
        assert is_valid is False

    def test_calculate_efficiency_normal(self):
        eff, warning = BlockAssignmentValidator.calculate_efficiency(1000.0, 960.0)
        assert eff == 96.0
        assert warning is None

    def test_calculate_efficiency_low(self):
        eff, warning = BlockAssignmentValidator.calculate_efficiency(1000.0, 500.0)
        assert eff == 50.0
        assert warning is not None
        assert "below" in warning.lower()

    def test_calculate_efficiency_high(self):
        eff, warning = BlockAssignmentValidator.calculate_efficiency(1000.0, 2500.0)
        assert eff == 250.0
        assert warning is not None
        assert "exceeds" in warning.lower()

    def test_calculate_efficiency_none_actual(self):
        eff, warning = BlockAssignmentValidator.calculate_efficiency(1000.0, None)
        assert eff is None and warning is None

    def test_calculate_efficiency_zero_expected(self):
        # 0.0 is falsy - treated same as None, returns (None, None)
        eff, warning = BlockAssignmentValidator.calculate_efficiency(0.0, 500.0)
        assert eff is None


class TestRotationValidatorMethods:
    """Test RotationValidator static methods."""

    def test_validate_total_rounds_valid(self):
        is_valid, err = RotationValidator.validate_total_rounds(12)
        assert is_valid is True

    def test_validate_total_rounds_minimum(self):
        is_valid, err = RotationValidator.validate_total_rounds(1)
        assert is_valid is True

    def test_validate_total_rounds_zero(self):
        is_valid, err = RotationValidator.validate_total_rounds(0)
        assert is_valid is False

    def test_validate_total_rounds_too_large(self):
        is_valid, err = RotationValidator.validate_total_rounds(101)
        assert is_valid is False

    def test_validate_total_rounds_invalid_type(self):
        is_valid, err = RotationValidator.validate_total_rounds("twelve")
        assert is_valid is False

    def test_validate_current_round_valid(self):
        is_valid, err = RotationValidator.validate_current_round(3, 12)
        assert is_valid is True

    def test_validate_current_round_at_total(self):
        is_valid, err = RotationValidator.validate_current_round(12, 12)
        assert is_valid is True

    def test_validate_current_round_zero(self):
        is_valid, err = RotationValidator.validate_current_round(0, 12)
        assert is_valid is False

    def test_validate_current_round_exceeds_total(self):
        is_valid, err = RotationValidator.validate_current_round(13, 12)
        assert is_valid is False

    def test_validate_current_round_invalid_type(self):
        is_valid, err = RotationValidator.validate_current_round("three", 12)
        assert is_valid is False

    def test_validate_round_number_valid(self):
        is_valid, err = RotationValidator.validate_round_number(5, 12)
        assert is_valid is True

    def test_validate_round_number_boundary_low(self):
        is_valid, err = RotationValidator.validate_round_number(1, 12)
        assert is_valid is True

    def test_validate_round_number_boundary_high(self):
        is_valid, err = RotationValidator.validate_round_number(12, 12)
        assert is_valid is True

    def test_validate_round_number_zero(self):
        is_valid, err = RotationValidator.validate_round_number(0, 12)
        assert is_valid is False

    def test_validate_round_number_exceeds_total(self):
        is_valid, err = RotationValidator.validate_round_number(13, 12)
        assert is_valid is False

    def test_validate_rotation_matrix_valid(self):
        matrix = {
            1: [{'block_id': 'b1', 'group_id': 'g1'}, {'block_id': 'b2', 'group_id': 'g2'}],
            2: [{'block_id': 'b1', 'group_id': 'g2'}, {'block_id': 'b2', 'group_id': 'g1'}],
        }
        is_valid, errors = RotationValidator.validate_rotation_matrix(matrix, 2, 2)
        assert is_valid is True
        assert errors == []

    def test_validate_rotation_matrix_wrong_block_count(self):
        matrix = {
            1: [{'block_id': 'b1', 'group_id': 'g1'}],  # only 1 block, expected 2
        }
        is_valid, errors = RotationValidator.validate_rotation_matrix(matrix, 2, 1)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_rotation_matrix_duplicate_groups(self):
        matrix = {
            1: [{'block_id': 'b1', 'group_id': 'g1'}, {'block_id': 'b2', 'group_id': 'g1'}],
        }
        is_valid, errors = RotationValidator.validate_rotation_matrix(matrix, 2, 2)
        assert is_valid is False
