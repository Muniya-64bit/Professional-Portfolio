"""
Labour Planning Validators
Actual validation functions for labour planning data
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID


# ═════════════════════════════════════════════════════════════════════════════
# CUSTOM EXCEPTIONS
# ═════════════════════════════════════════════════════════════════════════════

class LabourValidationError(Exception):
    """Base validation error for labour planning"""
    def __init__(self, field: str, message: str, code: str = "VALIDATION_ERROR"):
        self.field = field
        self.message = message
        self.code = code
        super().__init__(f"{field}: {message}")


class EmployeeValidationError(LabourValidationError):
    """Employee validation error"""
    pass


class WorkerGroupValidationError(LabourValidationError):
    """Worker group validation error"""
    pass


class LabourPlanValidationError(LabourValidationError):
    """Labour plan validation error"""
    pass


class BlockAssignmentValidationError(LabourValidationError):
    """Block assignment validation error"""
    pass


class RotationValidationError(LabourValidationError):
    """Rotation validation error"""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# EMPLOYEE VALIDATORS
# ═════════════════════════════════════════════════════════════════════════════

class EmployeeValidator:
    """Validates employee data"""

    VALID_EMPLOYMENT_TYPES = {'permanent', 'casual', 'seasonal'}
    VALID_SKILL_TYPES = {'plucker', 'general', 'supervisor', 'driver'}
    VALID_GENDERS = {'M', 'F', 'O'}

    MAX_CODE_LENGTH = 50
    MAX_NAME_LENGTH = 150
    MAX_ID_LENGTH = 50
    MAX_WAGE = Decimal('999999.99')

    EMPLOYEE_CODE_PATTERN = re.compile(r'^[A-Z0-9\-_]{1,50}$')

    @staticmethod
    def validate_employee_code(code: str) -> Tuple[bool, Optional[str]]:
        """Validate employee code format

        Returns: (is_valid, error_message)
        """
        if not code or not isinstance(code, str):
            return False, "employee_code is required"

        if len(code) > EmployeeValidator.MAX_CODE_LENGTH:
            return False, f"employee_code max {EmployeeValidator.MAX_CODE_LENGTH} chars"

        if not EmployeeValidator.EMPLOYEE_CODE_PATTERN.match(code):
            return False, "employee_code must be alphanumeric (A-Z, 0-9, -, _)"

        return True, None

    @staticmethod
    def validate_full_name(name: str) -> Tuple[bool, Optional[str]]:
        """Validate employee full name"""
        if not name or not isinstance(name, str):
            return False, "full_name is required"

        name = name.strip()
        if not name:
            return False, "full_name cannot be empty"

        if len(name) > EmployeeValidator.MAX_NAME_LENGTH:
            return False, f"full_name max {EmployeeValidator.MAX_NAME_LENGTH} chars"

        return True, None

    @staticmethod
    def validate_hire_date(hire_date: Any) -> Tuple[bool, Optional[str]]:
        """Validate hire date (must be <= today)"""
        try:
            if isinstance(hire_date, str):
                d = datetime.strptime(hire_date, '%Y-%m-%d').date()
            elif isinstance(hire_date, datetime):
                d = hire_date.date()
            elif isinstance(hire_date, date):
                d = hire_date
            else:
                return False, "hire_date must be date or YYYY-MM-DD string"

            if d > date.today():
                return False, "hire_date cannot be in the future"

            return True, None
        except (ValueError, AttributeError):
            return False, "hire_date format invalid (use YYYY-MM-DD)"

    @staticmethod
    def validate_employment_type(emp_type: str) -> Tuple[bool, Optional[str]]:
        """Validate employment type"""
        if not emp_type or not isinstance(emp_type, str):
            return False, "employment_type is required"

        if emp_type not in EmployeeValidator.VALID_EMPLOYMENT_TYPES:
            valid = ', '.join(EmployeeValidator.VALID_EMPLOYMENT_TYPES)
            return False, f"employment_type must be one of: {valid}"

        return True, None

    @staticmethod
    def validate_skill_type(skill: str) -> Tuple[bool, Optional[str]]:
        """Validate skill type"""
        if not skill or not isinstance(skill, str):
            return False, "skill_type is required"

        if skill not in EmployeeValidator.VALID_SKILL_TYPES:
            valid = ', '.join(EmployeeValidator.VALID_SKILL_TYPES)
            return False, f"skill_type must be one of: {valid}"

        return True, None

    @staticmethod
    def validate_gender(gender: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Validate gender (optional)"""
        if gender is None:
            return True, None

        if not isinstance(gender, str):
            return False, "gender must be string or null"

        if gender not in EmployeeValidator.VALID_GENDERS:
            valid = ', '.join(EmployeeValidator.VALID_GENDERS)
            return False, f"gender must be one of: {valid}"

        return True, None

    @staticmethod
    def validate_daily_wage(wage: Optional[Any]) -> Tuple[bool, Optional[str]]:
        """Validate daily wage (optional, must be > 0)"""
        if wage is None:
            return True, None

        try:
            wage_dec = Decimal(str(wage))
            if wage_dec <= 0:
                return False, "daily_wage_lkr must be > 0"
            if wage_dec > EmployeeValidator.MAX_WAGE:
                return False, f"daily_wage_lkr max {EmployeeValidator.MAX_WAGE}"
            return True, None
        except:
            return False, "daily_wage_lkr must be a valid decimal number"

    @staticmethod
    def validate_employee_code_unique(code: str, estate_id: str, existing_codes: List[str]) -> Tuple[bool, Optional[str]]:
        """Check if employee code is unique per estate"""
        if code in existing_codes:
            return False, f"employee_code '{code}' already exists for this estate"
        return True, None

    @classmethod
    def validate_create_request(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate POST /api/labour/employees request

        Returns: dict of field -> error_message (empty if valid)
        """
        errors = {}

        # Required fields
        required = ['estate_id', 'employee_code', 'full_name', 'hire_date']
        for field in required:
            if field not in data or not data[field]:
                errors[field] = f"{field} is required"

        if errors:
            return errors

        # Validate each field
        valid, msg = cls.validate_employee_code(data['employee_code'])
        if not valid:
            errors['employee_code'] = msg

        valid, msg = cls.validate_full_name(data['full_name'])
        if not valid:
            errors['full_name'] = msg

        valid, msg = cls.validate_hire_date(data['hire_date'])
        if not valid:
            errors['hire_date'] = msg

        # Optional fields with defaults
        emp_type = data.get('employment_type', 'permanent')
        valid, msg = cls.validate_employment_type(emp_type)
        if not valid:
            errors['employment_type'] = msg

        skill = data.get('skill_type', 'plucker')
        valid, msg = cls.validate_skill_type(skill)
        if not valid:
            errors['skill_type'] = msg

        if 'gender' in data and data['gender']:
            valid, msg = cls.validate_gender(data['gender'])
            if not valid:
                errors['gender'] = msg

        if 'daily_wage_lkr' in data and data['daily_wage_lkr']:
            valid, msg = cls.validate_daily_wage(data['daily_wage_lkr'])
            if not valid:
                errors['daily_wage_lkr'] = msg

        return errors

    @classmethod
    def validate_update_request(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate PUT /api/labour/employees/<id> request"""
        errors = {}
        allowed_fields = {
            'full_name', 'gender', 'national_id', 'employment_type',
            'skill_type', 'daily_wage_lkr', 'is_active', 'notes'
        }

        # Check no unknown fields
        for field in data:
            if field not in allowed_fields:
                errors[field] = f"Cannot update field '{field}'"

        if errors:
            return errors

        # Validate each provided field
        if 'full_name' in data and data['full_name']:
            valid, msg = cls.validate_full_name(data['full_name'])
            if not valid:
                errors['full_name'] = msg

        if 'employment_type' in data and data['employment_type']:
            valid, msg = cls.validate_employment_type(data['employment_type'])
            if not valid:
                errors['employment_type'] = msg

        if 'skill_type' in data and data['skill_type']:
            valid, msg = cls.validate_skill_type(data['skill_type'])
            if not valid:
                errors['skill_type'] = msg

        if 'gender' in data and data['gender']:
            valid, msg = cls.validate_gender(data['gender'])
            if not valid:
                errors['gender'] = msg

        if 'daily_wage_lkr' in data and data['daily_wage_lkr']:
            valid, msg = cls.validate_daily_wage(data['daily_wage_lkr'])
            if not valid:
                errors['daily_wage_lkr'] = msg

        if 'is_active' in data:
            if not isinstance(data['is_active'], bool):
                errors['is_active'] = "is_active must be boolean"

        return errors


# ═════════════════════════════════════════════════════════════════════════════
# WORKER GROUP VALIDATORS
# ═════════════════════════════════════════════════════════════════════════════

class WorkerGroupValidator:
    """Validates worker group data"""

    MAX_CODE_LENGTH = 50
    MAX_NAME_LENGTH = 150
    MIN_CAPACITY = 1
    MAX_CAPACITY = 100
    TYPICAL_CAPACITY = 15
    CAPACITY_TOLERANCE = 2  # Allow ±2 variance from block capacity

    GROUP_CODE_PATTERN = re.compile(r'^[A-Z0-9\-_]{1,50}$')

    @staticmethod
    def validate_group_code(code: str) -> Tuple[bool, Optional[str]]:
        """Validate group code format"""
        if not code or not isinstance(code, str):
            return False, "group_code is required"

        if len(code) > WorkerGroupValidator.MAX_CODE_LENGTH:
            return False, f"group_code max {WorkerGroupValidator.MAX_CODE_LENGTH} chars"

        if not WorkerGroupValidator.GROUP_CODE_PATTERN.match(code):
            return False, "group_code must be alphanumeric (A-Z, 0-9, -, _)"

        return True, None

    @staticmethod
    def validate_group_name(name: str) -> Tuple[bool, Optional[str]]:
        """Validate group name"""
        if not name or not isinstance(name, str):
            return False, "group_name is required"

        name = name.strip()
        if not name:
            return False, "group_name cannot be empty"

        if len(name) > WorkerGroupValidator.MAX_NAME_LENGTH:
            return False, f"group_name max {WorkerGroupValidator.MAX_NAME_LENGTH} chars"

        return True, None

    @staticmethod
    def validate_capacity(capacity: Any) -> Tuple[bool, Optional[str]]:
        """Validate group capacity"""
        try:
            cap = int(capacity)
            if cap < WorkerGroupValidator.MIN_CAPACITY:
                return False, f"capacity minimum {WorkerGroupValidator.MIN_CAPACITY}"
            if cap > WorkerGroupValidator.MAX_CAPACITY:
                return False, f"capacity maximum {WorkerGroupValidator.MAX_CAPACITY}"
            return True, None
        except (ValueError, TypeError):
            return False, "capacity must be an integer"

    @staticmethod
    def validate_capacity_match(group_capacity: int, block_capacity: int) -> Tuple[bool, Optional[str]]:
        """Warn if group capacity doesn't match block capacity"""
        diff = abs(group_capacity - block_capacity)
        if diff > WorkerGroupValidator.CAPACITY_TOLERANCE:
            return False, (
                f"group capacity ({group_capacity}) should match block capacity ({block_capacity}). "
                f"Difference of {diff} exceeds tolerance of {WorkerGroupValidator.CAPACITY_TOLERANCE}"
            )
        return True, None


# ═════════════════════════════════════════════════════════════════════════════
# LABOUR PLAN VALIDATORS
# ═════════════════════════════════════════════════════════════════════════════

class LabourPlanValidator:
    """Validates labour plan data"""

    VALID_STATUSES = {'draft', 'published', 'in_progress', 'completed', 'archived'}

    # Valid status transitions
    VALID_TRANSITIONS = {
        'draft': {'published'},
        'published': {'in_progress'},
        'in_progress': {'completed'},
        'completed': {'archived'},
        'archived': set(),
    }

    MIN_TOTAL_WORKERS = 0
    MIN_TARGET_KG = 0

    @staticmethod
    def validate_period_start(period_str: Any) -> Tuple[bool, Optional[str]]:
        """Validate period_start is 1st of month (YYYY-MM-01)"""
        try:
            if isinstance(period_str, str):
                d = datetime.strptime(period_str, '%Y-%m-%d').date()
            elif isinstance(period_str, date):
                d = period_str
            else:
                return False, "period_start must be date or YYYY-MM-DD string"

            if d.day != 1:
                return False, "period_start must be 1st of month (YYYY-MM-01)"

            return True, None
        except ValueError:
            return False, "period_start format invalid (use YYYY-MM-DD)"

    @staticmethod
    def validate_status(status: str) -> Tuple[bool, Optional[str]]:
        """Validate plan status"""
        if not status or not isinstance(status, str):
            return False, "status is required"

        if status not in LabourPlanValidator.VALID_STATUSES:
            valid = ', '.join(LabourPlanValidator.VALID_STATUSES)
            return False, f"status must be one of: {valid}"

        return True, None

    @staticmethod
    def validate_status_transition(from_status: str, to_status: str) -> Tuple[bool, Optional[str]]:
        """Validate status workflow transition"""
        if from_status not in LabourPlanValidator.VALID_TRANSITIONS:
            return False, f"Unknown status '{from_status}'"

        allowed = LabourPlanValidator.VALID_TRANSITIONS[from_status]
        if to_status not in allowed:
            return False, (
                f"Cannot transition from '{from_status}' to '{to_status}'. "
                f"Allowed: {', '.join(allowed) if allowed else 'none'}"
            )

        return True, None

    @staticmethod
    def validate_total_workers(workers: Any) -> Tuple[bool, Optional[str]]:
        """Validate total workers count"""
        try:
            w = int(workers)
            if w < LabourPlanValidator.MIN_TOTAL_WORKERS:
                return False, f"total_workers minimum {LabourPlanValidator.MIN_TOTAL_WORKERS}"
            return True, None
        except (ValueError, TypeError):
            return False, "total_workers must be an integer"

    @staticmethod
    def validate_target_kg(target: Any) -> Tuple[bool, Optional[str]]:
        """Validate target yield in kg"""
        try:
            t = Decimal(str(target))
            if t < LabourPlanValidator.MIN_TARGET_KG:
                return False, f"target_kg minimum {LabourPlanValidator.MIN_TARGET_KG}"
            return True, None
        except:
            return False, "target_kg must be a valid number"

    @classmethod
    def validate_create_request(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate POST /api/labour/plans request"""
        errors = {}

        # Required fields
        if 'estate_id' not in data or not data['estate_id']:
            errors['estate_id'] = "estate_id is required"

        if 'period_start' not in data or not data['period_start']:
            errors['period_start'] = "period_start is required"
        else:
            valid, msg = cls.validate_period_start(data['period_start'])
            if not valid:
                errors['period_start'] = msg

        # Optional status (defaults to draft)
        if 'status' in data and data['status']:
            valid, msg = cls.validate_status(data['status'])
            if not valid:
                errors['status'] = msg

        return errors

    @classmethod
    def validate_update_request(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate PUT /api/labour/plans/<id> request"""
        errors = {}
        allowed = {'status', 'notes', 'total_workers', 'target_kg'}

        # Check no unknown fields
        for field in data:
            if field not in allowed:
                errors[field] = f"Cannot update field '{field}'"

        if 'status' in data and data['status']:
            valid, msg = cls.validate_status(data['status'])
            if not valid:
                errors['status'] = msg

        if 'total_workers' in data and data['total_workers'] is not None:
            valid, msg = cls.validate_total_workers(data['total_workers'])
            if not valid:
                errors['total_workers'] = msg

        if 'target_kg' in data and data['target_kg'] is not None:
            valid, msg = cls.validate_target_kg(data['target_kg'])
            if not valid:
                errors['target_kg'] = msg

        return errors


# ═════════════════════════════════════════════════════════════════════════════
# BLOCK ASSIGNMENT VALIDATORS
# ═════════════════════════════════════════════════════════════════════════════

class BlockAssignmentValidator:
    """Validates block assignment data"""

    VALID_STATUSES = {'scheduled', 'in_progress', 'completed', 'cancelled'}

    VALID_TRANSITIONS = {
        'scheduled': {'in_progress', 'cancelled'},
        'in_progress': {'completed', 'cancelled'},
        'completed': set(),
        'cancelled': set(),
    }

    MIN_YIELD_KG = 0
    MAX_YIELD_KG = Decimal('999999.999')
    EFFICIENCY_MIN = 0
    EFFICIENCY_MAX = 200  # Flag if > 200%
    EFFICIENCY_WARN = 80  # Warn if < 80%

    @staticmethod
    def validate_assignment_date(date_str: Any) -> Tuple[bool, Optional[str]]:
        """Validate assignment date"""
        try:
            if isinstance(date_str, str):
                d = datetime.strptime(date_str, '%Y-%m-%d').date()
            elif isinstance(date_str, date):
                d = date_str
            else:
                return False, "assignment_date must be date or YYYY-MM-DD string"
            return True, None
        except ValueError:
            return False, "assignment_date format invalid (use YYYY-MM-DD)"

    @staticmethod
    def validate_status(status: str) -> Tuple[bool, Optional[str]]:
        """Validate assignment status"""
        if not status or not isinstance(status, str):
            return False, "status is required"

        if status not in BlockAssignmentValidator.VALID_STATUSES:
            valid = ', '.join(BlockAssignmentValidator.VALID_STATUSES)
            return False, f"status must be one of: {valid}"

        return True, None

    @staticmethod
    def validate_status_transition(from_status: str, to_status: str) -> Tuple[bool, Optional[str]]:
        """Validate status workflow transition"""
        if from_status not in BlockAssignmentValidator.VALID_TRANSITIONS:
            return False, f"Unknown status '{from_status}'"

        allowed = BlockAssignmentValidator.VALID_TRANSITIONS[from_status]
        if to_status not in allowed:
            return False, (
                f"Cannot transition from '{from_status}' to '{to_status}'. "
                f"Allowed: {', '.join(allowed) if allowed else 'none'}"
            )

        return True, None

    @staticmethod
    def validate_yield_kg(yield_kg: Any, field_name: str = "yield_kg") -> Tuple[bool, Optional[str]]:
        """Validate yield in kg"""
        try:
            y = Decimal(str(yield_kg))
            if y < BlockAssignmentValidator.MIN_YIELD_KG:
                return False, f"{field_name} minimum {BlockAssignmentValidator.MIN_YIELD_KG}"
            if y > BlockAssignmentValidator.MAX_YIELD_KG:
                return False, f"{field_name} maximum {BlockAssignmentValidator.MAX_YIELD_KG}"
            return True, None
        except:
            return False, f"{field_name} must be a valid decimal number"

    @staticmethod
    def calculate_efficiency(expected_kg: Optional[float], actual_kg: Optional[float]) -> Tuple[Optional[float], Optional[str]]:
        """Calculate and validate efficiency percentage

        Returns: (efficiency_pct, warning_message or None)
        """
        if not expected_kg or not actual_kg:
            return None, None

        if expected_kg == 0:
            return None, "Cannot calculate efficiency: expected_kg is zero"

        efficiency = (float(actual_kg) / float(expected_kg)) * 100
        efficiency = round(efficiency, 1)

        # Check for suspicious values
        if efficiency > BlockAssignmentValidator.EFFICIENCY_MAX:
            return efficiency, f"Efficiency {efficiency}% exceeds maximum {BlockAssignmentValidator.EFFICIENCY_MAX}% (data error?)"

        if efficiency < BlockAssignmentValidator.EFFICIENCY_WARN:
            return efficiency, f"Efficiency {efficiency}% below acceptable {BlockAssignmentValidator.EFFICIENCY_WARN}% (review needed)"

        return efficiency, None


# ═════════════════════════════════════════════════════════════════════════════
# ROTATION VALIDATORS
# ═════════════════════════════════════════════════════════════════════════════

class RotationValidator:
    """Validates rotation cycle data"""

    MIN_ROUNDS = 1
    MAX_ROUNDS = 100

    @staticmethod
    def validate_total_rounds(rounds: Any) -> Tuple[bool, Optional[str]]:
        """Validate total rounds (should equal block count)"""
        try:
            r = int(rounds)
            if r < RotationValidator.MIN_ROUNDS:
                return False, f"total_rounds minimum {RotationValidator.MIN_ROUNDS}"
            if r > RotationValidator.MAX_ROUNDS:
                return False, f"total_rounds maximum {RotationValidator.MAX_ROUNDS}"
            return True, None
        except (ValueError, TypeError):
            return False, "total_rounds must be an integer"

    @staticmethod
    def validate_current_round(current: Any, total: int) -> Tuple[bool, Optional[str]]:
        """Validate current round is within bounds"""
        try:
            c = int(current)
            if c < 1:
                return False, "current_round minimum 1"
            if c > total:
                return False, f"current_round cannot exceed total_rounds ({total})"
            return True, None
        except (ValueError, TypeError):
            return False, "current_round must be an integer"

    @staticmethod
    def validate_round_number(round_num: Any, total: int) -> Tuple[bool, Optional[str]]:
        """Validate round number is in valid range"""
        try:
            r = int(round_num)
            if r < 1 or r > total:
                return False, f"round_number must be between 1 and {total}"
            return True, None
        except (ValueError, TypeError):
            return False, "round_number must be an integer"

    @staticmethod
    def validate_rotation_matrix(matrix: Dict[int, List], block_count: int, group_count: int) -> Tuple[bool, List[str]]:
        """Validate rotation matrix completeness

        Returns: (is_valid, list_of_errors)
        """
        errors = []

        # Each round should have exactly block_count entries
        for round_num, blocks in matrix.items():
            if len(blocks) != block_count:
                errors.append(f"Round {round_num}: has {len(blocks)} blocks, expected {block_count}")

        # Each group should appear exactly once per round
        for round_num, blocks in matrix.items():
            groups_in_round = [b['group_id'] for b in blocks]
            if len(set(groups_in_round)) != len(groups_in_round):
                errors.append(f"Round {round_num}: duplicate group assignment")

        # All blocks and groups should be present across all rounds
        all_blocks = set()
        all_groups = set()
        for blocks in matrix.values():
            for b in blocks:
                all_blocks.add(b['block_id'])
                all_groups.add(b['group_id'])

        if len(all_blocks) < block_count:
            errors.append(f"Not all blocks are assigned (found {len(all_blocks)}, expected {block_count})")

        if len(all_groups) < group_count:
            errors.append(f"Not all groups are used (found {len(all_groups)}, expected {group_count})")

        return len(errors) == 0, errors
