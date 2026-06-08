"""Tests for schemas module - imports real enums and classes."""
import pytest
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

# Import actual schemas and enums
from schemas import (
    EmploymentType, SkillType, PlanStatus, AssignmentStatus,
    AssignmentType, Gender, EmployeeSchema, WorkerGroupSchema,
    LabourPlanSchema, BlockAssignmentSchema, RotationCycleSchema
)


class TestEmploymentTypeEnum:
    """Test EmploymentType enum."""

    def test_permanent_value(self):
        """Test PERMANENT employment type."""
        assert EmploymentType.PERMANENT == "permanent"
        assert EmploymentType.PERMANENT.value == "permanent"

    def test_casual_value(self):
        """Test CASUAL employment type."""
        assert EmploymentType.CASUAL == "casual"
        assert EmploymentType.CASUAL.value == "casual"

    def test_seasonal_value(self):
        """Test SEASONAL employment type."""
        assert EmploymentType.SEASONAL == "seasonal"
        assert EmploymentType.SEASONAL.value == "seasonal"

    def test_all_employment_types(self):
        """Test all employment types are available."""
        types = [e.value for e in EmploymentType]
        assert 'permanent' in types
        assert 'casual' in types
        assert 'seasonal' in types


class TestSkillTypeEnum:
    """Test SkillType enum."""

    def test_plucker_value(self):
        """Test PLUCKER skill type."""
        assert SkillType.PLUCKER == "plucker"

    def test_general_value(self):
        """Test GENERAL skill type."""
        assert SkillType.GENERAL == "general"

    def test_supervisor_value(self):
        """Test SUPERVISOR skill type."""
        assert SkillType.SUPERVISOR == "supervisor"

    def test_driver_value(self):
        """Test DRIVER skill type."""
        assert SkillType.DRIVER == "driver"

    def test_all_skill_types(self):
        """Test all skill types are available."""
        types = [s.value for s in SkillType]
        assert 'plucker' in types
        assert 'general' in types
        assert 'supervisor' in types
        assert 'driver' in types


class TestPlanStatusEnum:
    """Test PlanStatus enum."""

    def test_draft_status(self):
        """Test DRAFT status."""
        assert PlanStatus.DRAFT == "draft"

    def test_published_status(self):
        """Test PUBLISHED status."""
        assert PlanStatus.PUBLISHED == "published"

    def test_in_progress_status(self):
        """Test IN_PROGRESS status."""
        assert PlanStatus.IN_PROGRESS == "in_progress"

    def test_completed_status(self):
        """Test COMPLETED status."""
        assert PlanStatus.COMPLETED == "completed"

    def test_archived_status(self):
        """Test ARCHIVED status."""
        assert PlanStatus.ARCHIVED == "archived"


class TestAssignmentStatusEnum:
    """Test AssignmentStatus enum."""

    def test_scheduled_status(self):
        """Test SCHEDULED status."""
        assert AssignmentStatus.SCHEDULED == "scheduled"

    def test_in_progress_status(self):
        """Test IN_PROGRESS status."""
        assert AssignmentStatus.IN_PROGRESS == "in_progress"

    def test_completed_status(self):
        """Test COMPLETED status."""
        assert AssignmentStatus.COMPLETED == "completed"

    def test_cancelled_status(self):
        """Test CANCELLED status."""
        assert AssignmentStatus.CANCELLED == "cancelled"


class TestAssignmentTypeEnum:
    """Test AssignmentType enum."""

    def test_group_type(self):
        """Test GROUP assignment type."""
        assert AssignmentType.GROUP == "group"

    def test_manual_add_type(self):
        """Test MANUAL_ADD assignment type."""
        assert AssignmentType.MANUAL_ADD == "manual_add"

    def test_manual_remove_type(self):
        """Test MANUAL_REMOVE assignment type."""
        assert AssignmentType.MANUAL_REMOVE == "manual_remove"


class TestGenderEnum:
    """Test Gender enum."""

    def test_male_value(self):
        """Test MALE gender."""
        assert Gender.MALE == "M"

    def test_female_value(self):
        """Test FEMALE gender."""
        assert Gender.FEMALE == "F"

    def test_other_value(self):
        """Test OTHER gender."""
        assert Gender.OTHER == "O"


class TestEmployeeSchema:
    """Test EmployeeSchema class."""

    def test_employee_schema_exists(self):
        """Test that EmployeeSchema is available."""
        assert EmployeeSchema is not None


class TestWorkerGroupSchema:
    """Test WorkerGroupSchema class."""

    def test_worker_group_schema_exists(self):
        """Test that WorkerGroupSchema is available."""
        assert WorkerGroupSchema is not None


class TestLabourPlanSchema:
    """Test LabourPlanSchema class."""

    def test_labour_plan_schema_exists(self):
        """Test that LabourPlanSchema is available."""
        assert LabourPlanSchema is not None


class TestBlockAssignmentSchema:
    """Test BlockAssignmentSchema class."""

    def test_block_assignment_schema_exists(self):
        """Test that BlockAssignmentSchema is available."""
        assert BlockAssignmentSchema is not None


class TestRotationCycleSchema:
    """Test RotationCycleSchema class."""

    def test_rotation_cycle_schema_exists(self):
        """Test that RotationCycleSchema is available."""
        assert RotationCycleSchema is not None
