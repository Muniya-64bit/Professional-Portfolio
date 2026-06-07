"""
Labour Planning Schemas & Validation
Defines all data structures for labour planning module.
"""

from enum import Enum
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal


# ═════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═════════════════════════════════════════════════════════════════════════════

class EmploymentType(str, Enum):
    """Employment contract type."""
    PERMANENT = "permanent"
    CASUAL = "casual"
    SEASONAL = "seasonal"


class SkillType(str, Enum):
    """Worker skill classification."""
    PLUCKER = "plucker"
    GENERAL = "general"
    SUPERVISOR = "supervisor"
    DRIVER = "driver"


class PlanStatus(str, Enum):
    """Labour plan workflow state."""
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class AssignmentStatus(str, Enum):
    """Block assignment state."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AssignmentType(str, Enum):
    """Individual assignment override type."""
    GROUP = "group"  # Employee was in the assigned group
    MANUAL_ADD = "manual_add"  # Manager explicitly added
    MANUAL_REMOVE = "manual_remove"  # Manager explicitly removed (leave/absence)


class Gender(str, Enum):
    """Employee gender."""
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


# ═════════════════════════════════════════════════════════════════════════════
# CORE SCHEMAS
# ═════════════════════════════════════════════════════════════════════════════

class EmployeeSchema:
    """
    Field-level worker (not a system user).

    Fields:
        id: UUID primary key
        estate_id: UUID foreign key to estate
        employee_code: unique code per estate (e.g., "EMP001")
        full_name: full name (max 150 chars)
        gender: M/F/O or None
        national_id: national ID (optional, max 50 chars)
        hire_date: when employee joined
        employment_type: permanent | casual | seasonal
        skill_type: plucker | general | supervisor | driver
        daily_wage_lkr: daily wage in LKR (optional, max 999999.99)
        is_active: soft delete flag
        notes: optional notes (max 1000 chars)
        created_at: timestamp
        updated_at: timestamp

    Constraints:
        - UNIQUE (estate_id, employee_code)
        - gender IN ('M', 'F', 'O') or NULL
        - employment_type IN ('permanent', 'casual', 'seasonal')
        - skill_type IN ('plucker', 'general', 'supervisor', 'driver')
        - daily_wage_lkr > 0 or NULL
    """
    pass


class WorkerGroupSchema:
    """
    Team/gang of workers (e.g., "Plucking Team A").
    Sized to match block worker_capacity (typically 15 workers per group).

    Fields:
        id: UUID primary key
        estate_id: UUID foreign key to estate
        group_code: unique code per estate (e.g., "G01", "G02")
        group_name: display name (e.g., "Morning Shift Team A")
        supervisor_id: UUID FK to employee (skill_type = supervisor) or NULL
        capacity: target headcount (e.g., 15 workers)
        is_active: soft delete flag
        created_at: timestamp
        updated_at: timestamp

    Constraints:
        - UNIQUE (estate_id, group_code)
        - capacity > 0
        - supervisor_id must reference employee with skill_type='supervisor' (application logic)
    """
    pass


class WorkerGroupMemberSchema:
    """
    Membership record linking employee → worker_group with effective dates.
    One employee can only be in ONE active group at a time.

    Fields:
        id: UUID primary key
        group_id: UUID FK to worker_group
        employee_id: UUID FK to employee
        joined_date: when employee joined the group
        left_date: when employee left (NULL = still active)
        is_active: soft delete flag; also checked with left_date
        created_at: timestamp
        updated_at: timestamp

    Constraints:
        - UNIQUE (employee_id) WHERE is_active = TRUE
        - left_date > joined_date (if left_date is set)
        - Only ONE active membership per employee (enforced by unique index)
    """
    pass


class RotationCycleSchema:
    """
    Rotation pattern for an estate (e.g., 4-block rotation).
    Defines how many rounds (weeks) before every group visits every block.

    Fields:
        id: UUID primary key
        estate_id: UUID FK to estate
        cycle_name: display name (e.g., "4-Block Rotation")
        total_rounds: number of blocks (every group visits every block once per cycle)
        current_round: current round (1 to total_rounds), incremented monthly
        is_active: only one active per estate
        created_by: UUID FK to "user" (who created it)
        created_at: timestamp
        updated_at: timestamp

    Constraints:
        - UNIQUE (estate_id) WHERE is_active = TRUE
        - current_round BETWEEN 1 AND total_rounds
        - total_rounds > 0

    Example:
        4 blocks → total_rounds = 4
        Round 1: G1→A, G2→B, G3→C, G4→D
        Round 2: G1→B, G2→C, G3→D, G4→A
        Round 3: G1→C, G2→D, G3→A, G4→B
        Round 4: G1→D, G2→A, G3→B, G4→C
    """
    pass


class RotationRoundBlockSchema:
    """
    Lookup table: for a given round, which group covers which block.
    Defines the full rotation matrix.

    Fields:
        id: UUID primary key
        rotation_cycle_id: UUID FK to rotation_cycle
        round_number: round (1 to total_rounds)
        block_id: UUID FK to block
        worker_group_id: UUID FK to worker_group
        created_at: timestamp

    Constraints:
        - UNIQUE (rotation_cycle_id, round_number, block_id)
        - UNIQUE (rotation_cycle_id, round_number, worker_group_id)
        - round_number > 0
    """
    pass


class LabourPlanSchema:
    """
    Monthly labour plan for one estate.
    Groups all block assignments for a month under one plan header.

    Fields:
        id: UUID primary key
        estate_id: UUID FK to estate
        period_start: first day of month (YYYY-MM-01)
        total_workers: headcount allocated to this month
        target_kg: target harvest (kg) for this month
        status: draft | published | in_progress | completed | archived
        notes: optional plan notes
        created_by: UUID FK to "user" (who created the plan)
        created_at: timestamp
        updated_at: timestamp

    Constraints:
        - UNIQUE (estate_id, period_start)
        - period_start is always 1st of month
        - status IN ('draft', 'published', 'in_progress', 'completed', 'archived')
        - total_workers >= 0
        - target_kg >= 0

    Lifecycle:
        draft → published (manager approves plan)
        published → in_progress (work starts)
        in_progress → completed (month ends)
        completed → archived (optional, after retention period)
    """
    pass


class BlockAssignmentSchema:
    """
    Daily block assignment generated from rotation (or manual override).
    One row per (block, assignment_date) pair.

    Fields:
        id: UUID primary key
        labour_plan_id: UUID FK to labour_plan
        block_id: UUID FK to block
        worker_group_id: UUID FK to worker_group (or NULL if unassigned)
        assignment_date: date of assignment

        rotation_cycle_id: UUID FK to rotation_cycle (null if manual)
        rotation_round: which round number (1 to total_rounds)

        is_manual_override: TRUE if manager changed rotation
        original_group_id: group the rotation would have assigned (if override)
        override_reason: why manager overrode (text)
        overridden_by: UUID FK to "user" (who made override)
        overridden_at: timestamp when override was made

        expected_yield_kg: predicted yield (from ML model)
        actual_yield_kg: recorded yield (NULL until recorded)
        plucking_round_number: which plucking round for this block in month

        status: scheduled | in_progress | completed | cancelled
        notes: assignment notes
        created_at: timestamp
        updated_at: timestamp

    Constraints:
        - UNIQUE (block_id, assignment_date)
        - status IN ('scheduled', 'in_progress', 'completed', 'cancelled')
        - expected_yield_kg >= 0
        - actual_yield_kg >= 0 (if set)
        - If is_manual_override=TRUE: original_group_id must be set

    Key Logic:
        - When created from rotation: rotation_cycle_id + rotation_round set, is_manual_override=FALSE
        - When manually overridden: is_manual_override=TRUE, original_group_id saved
        - expected_yield_kg comes from ML predictions
        - actual_yield_kg is filled in when work is recorded
        - Efficiency = (actual_yield_kg / expected_yield_kg) * 100 (calculated, not stored)
    """
    pass


class EmployeeDayAssignmentSchema:
    """
    Individual-level assignment on top of group assignment.
    Allows manager to add/remove specific employees for a day.

    Fields:
        id: UUID primary key
        block_assignment_id: UUID FK to block_assignment
        employee_id: UUID FK to employee
        assignment_type: group | manual_add | manual_remove

        kg_collected: individual yield (kg) if recorded (NULL until recorded)
        added_by: UUID FK to "user" (who made manual change)
        reason: why removed (e.g., "sick leave", "training")

        created_at: timestamp
        updated_at: timestamp

    Constraints:
        - UNIQUE (block_assignment_id, employee_id)
        - assignment_type IN ('group', 'manual_add', 'manual_remove')
        - kg_collected >= 0 (if set)

    Assignment Types:
        group: Employee was in the worker_group assigned to this block
        manual_add: Manager explicitly added (e.g., extra support from another group)
        manual_remove: Manager explicitly removed (e.g., leave, sick day)

    Note:
        If assignment_type='group', employee's presence is implicit from worker_group membership.
        manual_add/manual_remove are explicit overrides on top of group assignment.
    """
    pass


# ═════════════════════════════════════════════════════════════════════════════
# COMPUTED / DERIVED FIELDS
# ═════════════════════════════════════════════════════════════════════════════

class BlockAssignmentWithMetricsSchema:
    """
    BlockAssignment + calculated metrics (read-only).

    Extends BlockAssignmentSchema with:
        - efficiency_pct: (actual_yield_kg / expected_yield_kg) * 100 or NULL
        - variance_kg: actual_yield_kg - expected_yield_kg or NULL
        - capacity_met: actual assigned workers >= block.worker_capacity
        - is_overdue: assignment_date < today AND status != 'completed'
    """
    pass


class WorkerGroupWithMembersSchema:
    """
    WorkerGroup + its members and metrics.

    Extends WorkerGroupSchema with:
        - members: List[WorkerGroupMemberSchema with employee details]
        - headcount: current active member count
        - vacancy: capacity - headcount
        - fill_rate_pct: (headcount / capacity) * 100
        - supervisor_name: supervisor's full_name
    """
    pass


class RotationCycleWithMatrixSchema:
    """
    RotationCycle + full rotation matrix.

    Extends RotationCycleSchema with:
        - matrix: Dict[round_number: List[block_code → group_code]]
        - completion_pct: (current_round / total_rounds) * 100
        - rounds_remaining: total_rounds - current_round

    Example matrix:
        {
            1: [{'block': 'A1', 'group': 'G1'}, {'block': 'A2', 'group': 'G2'}, ...],
            2: [{'block': 'A1', 'group': 'G2'}, {'block': 'A2', 'group': 'G3'}, ...],
            ...
        }
    """
    pass


class LabourPlanDetailSchema:
    """
    Complete labour plan with all details (read-heavy endpoint).

    Extends LabourPlanSchema with:
        - assignments: List[BlockAssignmentWithMetricsSchema]
        - rotation: RotationCycleWithMatrixSchema
        - estate_name: estate name
        - blocks_assigned: count of assignments
        - expected_total_kg: sum of expected_yield_kg
        - actual_total_kg: sum of actual_yield_kg
        - overall_efficiency_pct: (actual_total_kg / expected_total_kg) * 100
        - completion_status: % assignments completed
    """
    pass


# ═════════════════════════════════════════════════════════════════════════════
# API RESPONSE SCHEMAS
# ═════════════════════════════════════════════════════════════════════════════

class PaginatedListResponse:
    """
    Paginated list response (if implemented).

    Fields:
        data: List[Item]
        pagination: {total, page, limit, pages}
    """
    pass


class LabourPlanListItemSchema:
    """
    Item returned by GET /api/labour/plans (list view).

    Contains plan header + aggregated metrics (no detailed assignments).
    """
    pass


class CreateLabourPlanRequestSchema:
    """
    Request body for POST /api/labour/plans.

    Fields:
        estate_id: UUID (required)
        period_start: date string YYYY-MM-DD (required, will be normalized to 1st of month)
        status: draft | published (optional, default=draft)
        notes: string (optional)
    """
    pass


class UpdateLabourPlanRequestSchema:
    """
    Request body for PUT /api/labour/plans/<id>.

    Fields (all optional, updates only provided fields):
        status: draft | published | in_progress | completed | archived
        notes: string
        total_workers: int >= 0
        target_kg: decimal >= 0
    """
    pass


class CreateBlockAssignmentRequestSchema:
    """
    Request body for manual block assignment creation.

    Fields:
        labour_plan_id: UUID (required)
        block_id: UUID (required)
        worker_group_id: UUID (optional, can be NULL for unassigned)
        assignment_date: date string YYYY-MM-DD (required)
        expected_yield_kg: decimal >= 0 (optional)
        notes: string (optional)
    """
    pass


class OverrideAssignmentRequestSchema:
    """
    Request body for PUT /api/labour/assignments/<id> (override group).

    Fields:
        worker_group_id: UUID (new group)
        override_reason: string (required, why changing)

    Effect:
        Sets is_manual_override=TRUE, stores original_group_id, updates worker_group_id
    """
    pass


class EmployeeOverrideRequestSchema:
    """
    Request body for POST /api/labour/assignments/<id>/employee-overrides.

    Fields:
        employee_id: UUID (required)
        action: add | remove (required)
        reason: string (optional, why removed)

    Effect:
        action='add': Creates EmployeeDayAssignment with assignment_type='manual_add'
        action='remove': Creates EmployeeDayAssignment with assignment_type='manual_remove'
    """
    pass


class RecordYieldRequestSchema:
    """
    Request body for POST /api/labour/plans/<id>/record-yield.

    Fields:
        yields: List[{assignment_id: UUID, actual_yield_kg: decimal}]

    Effect:
        Updates block_assignment.actual_yield_kg for each assignment_id
        Also upserts block_yield_record for ML feedback
    """
    pass


class CreateEmployeeRequestSchema:
    """
    Request body for POST /api/labour/employees.

    Fields (required):
        estate_id: UUID
        employee_code: string (unique per estate, max 50 chars)
        full_name: string (max 150 chars)
        hire_date: date string YYYY-MM-DD

    Fields (optional):
        gender: M | F | O
        national_id: string (max 50 chars)
        employment_type: permanent | casual | seasonal (default=permanent)
        skill_type: plucker | general | supervisor | driver (default=plucker)
        daily_wage_lkr: decimal > 0
        group_id: UUID (if assigning to a group at creation)
        notes: string
    """
    pass


class UpdateEmployeeRequestSchema:
    """
    Request body for PUT /api/labour/employees/<id>.

    Fields (all optional, updates only provided):
        full_name: string
        gender: M | F | O
        national_id: string
        employment_type: permanent | casual | seasonal
        skill_type: plucker | general | supervisor | driver
        daily_wage_lkr: decimal > 0
        is_active: boolean
        notes: string
    """
    pass


# ═════════════════════════════════════════════════════════════════════════════
# VALIDATION LOGIC (pseudo-code, implement in validation service)
# ═════════════════════════════════════════════════════════════════════════════

class ValidationRules:
    """
    Business rules for labour planning.

    1. EMPLOYEE CREATION:
       - employee_code must be unique per estate
       - hire_date must be <= today
       - if skill_type='supervisor', ensure no duplicate supervisors per group

    2. WORKER GROUP:
       - capacity should match block.worker_capacity (typical 15)
       - supervisor_id must reference an active employee with skill_type='supervisor'
       - group_code must be unique per estate

    3. LABOUR PLAN:
       - period_start must be 1st of month
       - only one plan per (estate, period_start)
       - total_workers should be sum of group capacities or >= 0
       - target_kg should be reasonable (e.g., > 0)

    4. BLOCK ASSIGNMENT:
       - assignment_date must be within plan's month
       - worker_group_id must be active
       - expected_yield_kg from ML (auto-calculated)
       - actual_yield_kg only settable if status != 'scheduled'
       - cannot update assignment after status='completed' (unless override permission)

    5. ASSIGNMENT STATUS WORKFLOW:
       - scheduled → in_progress (work starts)
       - in_progress → completed (work done, yield recorded)
       - in_progress → cancelled (work abandoned)
       - Cannot go backwards (completed → in_progress not allowed)

    6. PLAN STATUS WORKFLOW:
       - draft → published (manager approves)
       - published → in_progress (start date reached)
       - in_progress → completed (end of month)
       - completed → archived (optional, no more edits)

    7. ROTATION ROUND ENFORCEMENT:
       - current_round must be between 1 and total_rounds
       - when generating next month, increment current_round (wrap at total_rounds)
       - cannot have gaps in round matrix (every block assigned each round)

    8. MANAGER (read-only) RESTRICTIONS:
       - Can READ plans/assignments for own estate
       - Can RECORD actual yield (set actual_yield_kg)
       - Can ADD employees to own estate
       - Cannot: generate plans, change rotations, publish, archive

    9. EFFICIENCY TRACKING:
       - efficiency_pct = (actual_yield_kg / expected_yield_kg) * 100
       - cap at 200% (suspicious if higher)
       - track per-block, per-group, per-month
       - flag blocks with efficiency < 80% for review
    """
    pass
