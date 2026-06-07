"""
Labour Planning Serializers
Convert database rows to proper typed API responses
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID


# ═════════════════════════════════════════════════════════════════════════════
# SERIALIZATION HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def serialize_uuid(val: Any) -> Optional[str]:
    """Convert UUID to string"""
    if val is None:
        return None
    return str(val)


def serialize_date(val: Any) -> Optional[str]:
    """Convert date/datetime to ISO string"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return str(val)


def serialize_decimal(val: Any) -> Optional[float]:
    """Convert Decimal to float"""
    if val is None:
        return None
    return float(val)


def serialize_int(val: Any) -> Optional[int]:
    """Convert to int"""
    if val is None:
        return None
    return int(val)


def serialize_bool(val: Any) -> bool:
    """Convert to bool"""
    if val is None:
        return False
    return bool(val)


def serialize_string(val: Any) -> Optional[str]:
    """Convert to string"""
    if val is None:
        return None
    return str(val).strip() if isinstance(val, str) else str(val)


# ═════════════════════════════════════════════════════════════════════════════
# EMPLOYEE SERIALIZER
# ═════════════════════════════════════════════════════════════════════════════

class EmployeeSerializer:
    """Convert employee DB rows to API responses"""

    @staticmethod
    def serialize_employee(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize single employee row"""
        return {
            'id': serialize_uuid(row.get('id')),
            'estate_id': serialize_uuid(row.get('estate_id')),
            'employee_code': serialize_string(row.get('employee_code')),
            'full_name': serialize_string(row.get('full_name')),
            'gender': serialize_string(row.get('gender')),
            'national_id': serialize_string(row.get('national_id')),
            'hire_date': serialize_date(row.get('hire_date')),
            'employment_type': serialize_string(row.get('employment_type')),
            'skill_type': serialize_string(row.get('skill_type')),
            'daily_wage_lkr': serialize_decimal(row.get('daily_wage_lkr')),
            'is_active': serialize_bool(row.get('is_active')),
            'notes': serialize_string(row.get('notes')),
            'created_at': serialize_date(row.get('created_at')),
            'updated_at': serialize_date(row.get('updated_at')),
        }

    @staticmethod
    def serialize_employees(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize multiple employees"""
        return [EmployeeSerializer.serialize_employee(row) for row in rows]


# ═════════════════════════════════════════════════════════════════════════════
# WORKER GROUP SERIALIZER
# ═════════════════════════════════════════════════════════════════════════════

class WorkerGroupSerializer:
    """Convert worker group DB rows to API responses"""

    @staticmethod
    def serialize_group(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize single worker group"""
        return {
            'id': serialize_uuid(row.get('id')),
            'estate_id': serialize_uuid(row.get('estate_id')),
            'group_code': serialize_string(row.get('group_code')),
            'group_name': serialize_string(row.get('group_name')),
            'supervisor_id': serialize_uuid(row.get('supervisor_id')),
            'capacity': serialize_int(row.get('capacity')),
            'is_active': serialize_bool(row.get('is_active')),
            'created_at': serialize_date(row.get('created_at')),
            'updated_at': serialize_date(row.get('updated_at')),
        }

    @staticmethod
    def serialize_group_with_metrics(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize group with headcount and fill metrics"""
        group = WorkerGroupSerializer.serialize_group(row)
        headcount = serialize_int(row.get('headcount', 0))
        capacity = serialize_int(row.get('capacity', 0))
        vacancy = capacity - headcount if capacity else 0
        fill_rate_pct = (headcount / capacity * 100) if capacity else 0

        return {
            **group,
            'headcount': headcount,
            'vacancy': vacancy,
            'fill_rate_pct': round(fill_rate_pct, 1),
            'supervisor_name': serialize_string(row.get('supervisor_name')),
            'members': row.get('members', []),
        }

    @staticmethod
    def serialize_groups(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize multiple groups"""
        return [WorkerGroupSerializer.serialize_group(row) for row in rows]


# ═════════════════════════════════════════════════════════════════════════════
# WORKER GROUP MEMBER SERIALIZER
# ═════════════════════════════════════════════════════════════════════════════

class WorkerGroupMemberSerializer:
    """Convert group member DB rows to API responses"""

    @staticmethod
    def serialize_member(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize single group member"""
        return {
            'id': serialize_uuid(row.get('id')),
            'group_id': serialize_uuid(row.get('group_id')),
            'employee_id': serialize_uuid(row.get('employee_id')),
            'joined_date': serialize_date(row.get('joined_date')),
            'left_date': serialize_date(row.get('left_date')),
            'is_active': serialize_bool(row.get('is_active')),
            'created_at': serialize_date(row.get('created_at')),
            'updated_at': serialize_date(row.get('updated_at')),
            # Optional: join with employee details
            'employee_code': serialize_string(row.get('employee_code')),
            'full_name': serialize_string(row.get('full_name')),
            'skill_type': serialize_string(row.get('skill_type')),
        }

    @staticmethod
    def serialize_members(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize multiple members"""
        return [WorkerGroupMemberSerializer.serialize_member(row) for row in rows]


# ═════════════════════════════════════════════════════════════════════════════
# ROTATION CYCLE SERIALIZER
# ═════════════════════════════════════════════════════════════════════════════

class RotationCycleSerializer:
    """Convert rotation cycle DB rows to API responses"""

    @staticmethod
    def serialize_cycle(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize single rotation cycle"""
        return {
            'id': serialize_uuid(row.get('id')),
            'estate_id': serialize_uuid(row.get('estate_id')),
            'cycle_name': serialize_string(row.get('cycle_name')),
            'total_rounds': serialize_int(row.get('total_rounds')),
            'current_round': serialize_int(row.get('current_round')),
            'is_active': serialize_bool(row.get('is_active')),
            'created_by': serialize_uuid(row.get('created_by')),
            'created_at': serialize_date(row.get('created_at')),
            'updated_at': serialize_date(row.get('updated_at')),
        }

    @staticmethod
    def serialize_cycle_with_matrix(row: Dict[str, Any], matrix: Dict[int, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Serialize cycle with full rotation matrix"""
        cycle = RotationCycleSerializer.serialize_cycle(row)
        total_rounds = serialize_int(row.get('total_rounds', 0))
        current_round = serialize_int(row.get('current_round', 0))

        completion_pct = (current_round / total_rounds * 100) if total_rounds else 0
        rounds_remaining = total_rounds - current_round if total_rounds else 0

        return {
            **cycle,
            'matrix': matrix,
            'completion_pct': round(completion_pct, 1),
            'rounds_remaining': rounds_remaining,
        }


# ═════════════════════════════════════════════════════════════════════════════
# LABOUR PLAN SERIALIZER
# ═════════════════════════════════════════════════════════════════════════════

class LabourPlanSerializer:
    """Convert labour plan DB rows to API responses"""

    @staticmethod
    def serialize_plan(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize single labour plan"""
        return {
            'id': serialize_uuid(row.get('id')),
            'estate_id': serialize_uuid(row.get('estate_id')),
            'period_start': serialize_date(row.get('period_start')),
            'total_workers': serialize_int(row.get('total_workers')),
            'target_kg': serialize_decimal(row.get('target_kg')),
            'status': serialize_string(row.get('status')),
            'notes': serialize_string(row.get('notes')),
            'created_by': serialize_uuid(row.get('created_by')),
            'created_at': serialize_date(row.get('created_at')),
            'updated_at': serialize_date(row.get('updated_at')),
            # From joined data
            'estate_name': serialize_string(row.get('estate_name')),
            'cycle_name': serialize_string(row.get('cycle_name')),
            'current_round': serialize_int(row.get('current_round')),
            'total_rounds': serialize_int(row.get('total_rounds')),
            'blocks_assigned': serialize_int(row.get('blocks_assigned')),
            'expected_total_kg': serialize_decimal(row.get('expected_total_kg')),
            'actual_total_kg': serialize_decimal(row.get('actual_total_kg')),
        }

    @staticmethod
    def serialize_plan_with_assignments(
        plan_row: Dict[str, Any],
        assignments: List[Dict[str, Any]],
        rotation: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Serialize plan with full assignment details"""
        plan = LabourPlanSerializer.serialize_plan(plan_row)

        # Calculate overall efficiency
        expected_total = serialize_decimal(plan_row.get('expected_total_kg', 0))
        actual_total = serialize_decimal(plan_row.get('actual_total_kg', 0))
        overall_efficiency = None
        if expected_total and actual_total:
            overall_efficiency = round((actual_total / expected_total) * 100, 1)

        # Calculate completion status
        if assignments:
            completed = len([a for a in assignments if a.get('status') == 'completed'])
            completion_status = round((completed / len(assignments)) * 100, 1)
        else:
            completion_status = 0

        return {
            **plan,
            'assignments': assignments,
            'rotation': rotation,
            'overall_efficiency_pct': overall_efficiency,
            'completion_status': completion_status,
        }

    @staticmethod
    def serialize_plans(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize multiple plans"""
        return [LabourPlanSerializer.serialize_plan(row) for row in rows]


# ═════════════════════════════════════════════════════════════════════════════
# BLOCK ASSIGNMENT SERIALIZER
# ═════════════════════════════════════════════════════════════════════════════

class BlockAssignmentSerializer:
    """Convert block assignment DB rows to API responses"""

    @staticmethod
    def serialize_assignment(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize single block assignment"""
        expected = serialize_decimal(row.get('expected_yield_kg'))
        actual = serialize_decimal(row.get('actual_yield_kg'))

        # Calculate efficiency
        efficiency_pct = None
        variance_kg = None
        if expected and actual:
            efficiency_pct = round((actual / expected) * 100, 1)
            variance_kg = round(actual - expected, 1)

        return {
            'id': serialize_uuid(row.get('id')),
            'labour_plan_id': serialize_uuid(row.get('labour_plan_id')),
            'block_id': serialize_uuid(row.get('block_id')),
            'worker_group_id': serialize_uuid(row.get('worker_group_id')),
            'assignment_date': serialize_date(row.get('assignment_date')),
            'rotation_cycle_id': serialize_uuid(row.get('rotation_cycle_id')),
            'rotation_round': serialize_int(row.get('rotation_round')),
            'is_manual_override': serialize_bool(row.get('is_manual_override')),
            'original_group_id': serialize_uuid(row.get('original_group_id')),
            'override_reason': serialize_string(row.get('override_reason')),
            'overridden_by': serialize_uuid(row.get('overridden_by')),
            'overridden_at': serialize_date(row.get('overridden_at')),
            'expected_yield_kg': expected,
            'actual_yield_kg': actual,
            'plucking_round_number': serialize_int(row.get('plucking_round_number')),
            'status': serialize_string(row.get('status')),
            'notes': serialize_string(row.get('notes')),
            'created_at': serialize_date(row.get('created_at')),
            'updated_at': serialize_date(row.get('updated_at')),
            # From joined data
            'block_code': serialize_string(row.get('block_code')),
            'worker_capacity': serialize_int(row.get('worker_capacity')),
            'group_name': serialize_string(row.get('group_name')),
            'group_code': serialize_string(row.get('group_code')),
            'group_capacity': serialize_int(row.get('group_capacity')),
            'original_group_name': serialize_string(row.get('original_group_name')),
            # Computed metrics
            'efficiency_pct': efficiency_pct,
            'variance_kg': variance_kg,
        }

    @staticmethod
    def serialize_assignments(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize multiple assignments"""
        return [BlockAssignmentSerializer.serialize_assignment(row) for row in rows]

    @staticmethod
    def serialize_assignment_with_capacity_check(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize assignment with capacity check"""
        assignment = BlockAssignmentSerializer.serialize_assignment(row)
        worker_capacity = serialize_int(row.get('worker_capacity'))
        assigned_workers = serialize_int(row.get('assigned_workers', 0))
        capacity_met = assigned_workers >= worker_capacity if worker_capacity else False

        return {
            **assignment,
            'capacity_met': capacity_met,
        }


# ═════════════════════════════════════════════════════════════════════════════
# EMPLOYEE DAY ASSIGNMENT SERIALIZER
# ═════════════════════════════════════════════════════════════════════════════

class EmployeeDayAssignmentSerializer:
    """Convert employee day assignment DB rows to API responses"""

    @staticmethod
    def serialize_assignment(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize single employee day assignment"""
        return {
            'id': serialize_uuid(row.get('id')),
            'block_assignment_id': serialize_uuid(row.get('block_assignment_id')),
            'employee_id': serialize_uuid(row.get('employee_id')),
            'assignment_type': serialize_string(row.get('assignment_type')),
            'kg_collected': serialize_decimal(row.get('kg_collected')),
            'added_by': serialize_uuid(row.get('added_by')),
            'reason': serialize_string(row.get('reason')),
            'created_at': serialize_date(row.get('created_at')),
            'updated_at': serialize_date(row.get('updated_at')),
            # Optional: joined employee details
            'employee_code': serialize_string(row.get('employee_code')),
            'full_name': serialize_string(row.get('full_name')),
            'skill_type': serialize_string(row.get('skill_type')),
        }

    @staticmethod
    def serialize_assignments(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize multiple assignments"""
        return [EmployeeDayAssignmentSerializer.serialize_assignment(row) for row in rows]


# ═════════════════════════════════════════════════════════════════════════════
# ROTATION MATRIX SERIALIZER
# ═════════════════════════════════════════════════════════════════════════════

class RotationMatrixSerializer:
    """Convert rotation round blocks to matrix structure"""

    @staticmethod
    def build_matrix(rows: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """Convert flat rows to nested matrix structure

        Input: rows with (round_number, block_code, group_code, block_id, worker_group_id)
        Output: {round_number: [{block_code, group_code, block_id, worker_group_id}, ...]}
        """
        matrix = {}

        for row in rows:
            round_num = serialize_int(row.get('round_number'))
            if round_num not in matrix:
                matrix[round_num] = []

            matrix[round_num].append({
                'block_code': serialize_string(row.get('block_code')),
                'block_id': serialize_uuid(row.get('block_id')),
                'group_code': serialize_string(row.get('group_code')),
                'worker_group_id': serialize_uuid(row.get('worker_group_id')),
            })

        # Sort by round number
        return dict(sorted(matrix.items()))


# ═════════════════════════════════════════════════════════════════════════════
# EFFICIENCY REPORT SERIALIZER
# ═════════════════════════════════════════════════════════════════════════════

class EfficiencyReportSerializer:
    """Serialize efficiency metrics and analysis"""

    @staticmethod
    def serialize_plan_efficiency(row: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize plan-level efficiency metrics"""
        expected = serialize_decimal(row.get('expected_total_kg', 0))
        actual = serialize_decimal(row.get('actual_total_kg', 0))

        efficiency_pct = None
        variance_kg = None
        variance_pct = None

        if expected and actual:
            efficiency_pct = round((actual / expected) * 100, 1)
            variance_kg = round(actual - expected, 3)
            if expected:
                variance_pct = round((variance_kg / expected) * 100, 1)

        return {
            'period_start': serialize_date(row.get('period_start')),
            'estate_name': serialize_string(row.get('estate_name')),
            'expected_total_kg': expected,
            'actual_total_kg': actual,
            'efficiency_pct': efficiency_pct,
            'variance_kg': variance_kg,
            'variance_pct': variance_pct,
            'total_blocks': serialize_int(row.get('total_blocks')),
            'blocks_completed': serialize_int(row.get('blocks_completed')),
            'blocks_pending': serialize_int(row.get('total_blocks', 0)) - serialize_int(row.get('blocks_completed', 0)),
        }

    @staticmethod
    def serialize_block_efficiency(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize per-block efficiency"""
        results = []
        for row in rows:
            expected = serialize_decimal(row.get('expected_yield_kg'))
            actual = serialize_decimal(row.get('actual_yield_kg'))

            efficiency_pct = None
            if expected and actual:
                efficiency_pct = round((actual / expected) * 100, 1)

            results.append({
                'block_code': serialize_string(row.get('block_code')),
                'block_id': serialize_uuid(row.get('block_id')),
                'group_code': serialize_string(row.get('group_code')),
                'group_name': serialize_string(row.get('group_name')),
                'expected_yield_kg': expected,
                'actual_yield_kg': actual,
                'efficiency_pct': efficiency_pct,
                'status': serialize_string(row.get('status')),
                'is_manual_override': serialize_bool(row.get('is_manual_override')),
            })

        return results
