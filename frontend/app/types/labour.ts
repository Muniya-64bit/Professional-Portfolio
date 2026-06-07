/**
 * Labour Planning TypeScript Schemas
 * Strict typing for labour planning module
 */

// ═════════════════════════════════════════════════════════════════════════════
// ENUMS
// ═════════════════════════════════════════════════════════════════════════════

export enum EmploymentType {
  PERMANENT = 'permanent',
  CASUAL = 'casual',
  SEASONAL = 'seasonal',
}

export enum SkillType {
  PLUCKER = 'plucker',
  GENERAL = 'general',
  SUPERVISOR = 'supervisor',
  DRIVER = 'driver',
}

export enum PlanStatus {
  DRAFT = 'draft',
  PUBLISHED = 'published',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  ARCHIVED = 'archived',
}

export enum AssignmentStatus {
  SCHEDULED = 'scheduled',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
}

export enum AssignmentType {
  GROUP = 'group',
  MANUAL_ADD = 'manual_add',
  MANUAL_REMOVE = 'manual_remove',
}

export enum Gender {
  MALE = 'M',
  FEMALE = 'F',
  OTHER = 'O',
}

// ═════════════════════════════════════════════════════════════════════════════
// CORE TYPES
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Field-level worker (not a system user)
 */
export interface Employee {
  id: string; // UUID
  estate_id: string; // UUID
  employee_code: string; // Unique per estate
  full_name: string;
  gender?: Gender | null;
  national_id?: string | null;
  hire_date: string; // ISO date
  employment_type: EmploymentType;
  skill_type: SkillType;
  daily_wage_lkr?: number | null; // LKR cents stored as int in backend
  is_active: boolean;
  notes?: string | null;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/**
 * Team/gang of workers
 */
export interface WorkerGroup {
  id: string; // UUID
  estate_id: string; // UUID
  group_code: string; // Unique per estate
  group_name: string;
  supervisor_id?: string | null; // FK to Employee (skill_type='supervisor')
  capacity: number; // Target headcount
  is_active: boolean;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/**
 * Membership: Employee → WorkerGroup with effective dates
 */
export interface WorkerGroupMember {
  id: string; // UUID
  group_id: string; // UUID
  employee_id: string; // UUID
  joined_date: string; // ISO date
  left_date?: string | null; // ISO date or null if active
  is_active: boolean;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/**
 * Rotation cycle pattern for an estate
 * E.g., 4-block rotation = every group visits every block once per cycle
 */
export interface RotationCycle {
  id: string; // UUID
  estate_id: string; // UUID
  cycle_name: string;
  total_rounds: number; // = number of blocks
  current_round: number; // 1 to total_rounds
  is_active: boolean;
  created_by?: string | null; // UUID
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/**
 * Lookup: (round, block) → worker_group
 * Defines the full rotation matrix
 */
export interface RotationRoundBlock {
  id: string; // UUID
  rotation_cycle_id: string; // UUID
  round_number: number;
  block_id: string; // UUID
  worker_group_id: string; // UUID
  created_at: string; // ISO datetime
}

/**
 * Monthly labour plan for one estate
 */
export interface LabourPlan {
  id: string; // UUID
  estate_id: string; // UUID
  period_start: string; // ISO date (always 1st of month: YYYY-MM-01)
  total_workers: number;
  target_kg: number; // kg
  status: PlanStatus;
  notes?: string | null;
  created_by?: string | null; // UUID
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime

  // From joined data (optional)
  estate_name?: string;
  cycle_name?: string;
  current_round?: number;
  total_rounds?: number;
  blocks_assigned?: number;
  expected_total_kg?: number;
  actual_total_kg?: number;
}

/**
 * Daily block assignment
 */
export interface BlockAssignment {
  id: string; // UUID
  labour_plan_id?: string | null; // UUID
  block_id: string; // UUID
  worker_group_id?: string | null; // UUID
  assignment_date: string; // ISO date

  // Rotation tracking
  rotation_cycle_id?: string | null; // UUID
  rotation_round?: number | null;

  // Manual override
  is_manual_override: boolean;
  original_group_id?: string | null; // UUID (if overridden)
  override_reason?: string | null;
  overridden_by?: string | null; // UUID
  overridden_at?: string | null; // ISO datetime

  // Outcomes
  expected_yield_kg?: number | null; // kg
  actual_yield_kg?: number | null; // kg (set when recording yield)
  plucking_round_number?: number | null;

  status: AssignmentStatus;
  notes?: string | null;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime

  // From joined data (optional)
  block_code?: string;
  worker_capacity?: number;
  group_name?: string;
  group_code?: string;
  group_capacity?: number;
  original_group_name?: string;
}

/**
 * Individual-level assignment (override on group assignment)
 */
export interface EmployeeDayAssignment {
  id: string; // UUID
  block_assignment_id: string; // UUID
  employee_id: string; // UUID
  assignment_type: AssignmentType;
  kg_collected?: number | null; // kg (individual yield)
  added_by?: string | null; // UUID
  reason?: string | null;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

// ═════════════════════════════════════════════════════════════════════════════
// DERIVED / COMPUTED TYPES
// ═════════════════════════════════════════════════════════════════════════════

/**
 * BlockAssignment with calculated metrics
 */
export interface BlockAssignmentWithMetrics extends BlockAssignment {
  efficiency_pct?: number | null; // (actual / expected) * 100
  variance_kg?: number | null; // actual - expected
  capacity_met?: boolean;
  is_overdue?: boolean;
}

/**
 * WorkerGroup with members and metrics
 */
export interface WorkerGroupWithMembers extends WorkerGroup {
  members?: WorkerGroupMember[];
  headcount?: number;
  vacancy?: number;
  fill_rate_pct?: number; // (headcount / capacity) * 100
  supervisor_name?: string;
}

/**
 * Rotation matrix item: block → group for a round
 */
export interface RotationMatrixItem {
  block_code: string;
  group_code: string;
  block_id: string;
  worker_group_id: string;
}

/**
 * RotationCycle with full matrix
 */
export interface RotationCycleWithMatrix extends RotationCycle {
  matrix: Record<number, RotationMatrixItem[]>;
  completion_pct?: number;
  rounds_remaining?: number;
}

/**
 * Complete labour plan with all details
 */
export interface LabourPlanDetail extends LabourPlan {
  assignments: BlockAssignmentWithMetrics[];
  rotation?: RotationCycleWithMatrix;
  overall_efficiency_pct?: number;
  completion_status?: number; // % completed
}

// ═════════════════════════════════════════════════════════════════════════════
// REQUEST/RESPONSE TYPES
// ═════════════════════════════════════════════════════════════════════════════

/**
 * POST /api/labour/plans
 */
export interface CreateLabourPlanRequest {
  estate_id: string; // UUID
  period_start: string; // ISO date YYYY-MM-DD
  status?: PlanStatus; // optional, default='draft'
  notes?: string;
}

/**
 * PUT /api/labour/plans/<id>
 */
export interface UpdateLabourPlanRequest {
  status?: PlanStatus;
  notes?: string;
  total_workers?: number;
  target_kg?: number;
}

/**
 * PUT /api/labour/assignments/<id>
 */
export interface OverrideAssignmentRequest {
  worker_group_id: string; // UUID
  override_reason: string;
}

/**
 * POST /api/labour/assignments/<id>/employee-overrides
 */
export interface EmployeeOverrideRequest {
  employee_id: string; // UUID
  action: 'add' | 'remove';
  reason?: string;
}

/**
 * POST /api/labour/plans/<id>/record-yield
 */
export interface RecordYieldRequest {
  yields: Array<{
    assignment_id: string; // UUID
    actual_yield_kg: number;
  }>;
}

/**
 * POST /api/labour/employees
 */
export interface CreateEmployeeRequest {
  estate_id: string; // UUID
  employee_code: string;
  full_name: string;
  hire_date: string; // ISO date
  gender?: Gender | null;
  national_id?: string;
  employment_type?: EmploymentType;
  skill_type?: SkillType;
  daily_wage_lkr?: number;
  group_id?: string; // UUID (optional, assign to group at creation)
  notes?: string;
}

/**
 * PUT /api/labour/employees/<id>
 */
export interface UpdateEmployeeRequest {
  full_name?: string;
  gender?: Gender | null;
  national_id?: string;
  employment_type?: EmploymentType;
  skill_type?: SkillType;
  daily_wage_lkr?: number;
  is_active?: boolean;
  notes?: string;
}

/**
 * API error response
 */
export interface ApiError {
  error: string;
  code?: string;
  details?: Record<string, any>;
}

/**
 * Generic API response wrapper
 */
export interface ApiResponse<T> {
  data?: T;
  message?: string;
  error?: string;
}

// ═════════════════════════════════════════════════════════════════════════════
// UI STATE TYPES
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Labour planner UI state
 */
export interface LabourTabState {
  view: 'month' | 'rotation' | 'employees';
  estateId: string;
  plan: LabourPlanDetail | null;
  rotation: RotationCycleWithMatrix | null;
  employees: Employee[];
  groups: WorkerGroup[];
  loading: boolean;
  error: string;
}

/**
 * Employee modal state
 */
export interface EmployeeModalState {
  open: boolean;
  mode: 'add' | 'edit';
  employee?: Employee;
  saving: boolean;
  error: string;
}

/**
 * Yield recording modal state
 */
export interface YieldModalState {
  open: boolean;
  plan: LabourPlanDetail | null;
  yields: Record<string, number>; // assignment_id → actual_kg
  saving: boolean;
  error: string;
}

// ═════════════════════════════════════════════════════════════════════════════
// TYPE GUARDS
// ═════════════════════════════════════════════════════════════════════════════

export function isEmployee(obj: any): obj is Employee {
  return obj && typeof obj.id === 'string' && typeof obj.employee_code === 'string';
}

export function isLabourPlan(obj: any): obj is LabourPlan {
  return obj && typeof obj.id === 'string' && obj.period_start && obj.status;
}

export function isBlockAssignment(obj: any): obj is BlockAssignment {
  return obj && typeof obj.id === 'string' && obj.block_id && obj.assignment_date;
}

export function isRotationCycle(obj: any): obj is RotationCycle {
  return obj && typeof obj.id === 'string' && obj.total_rounds && obj.current_round;
}

// ═════════════════════════════════════════════════════════════════════════════
// VALIDATION HELPERS
// ═════════════════════════════════════════════════════════════════════════════

export class LabourValidation {
  /**
   * Validate employee code format
   */
  static isValidEmployeeCode(code: string): boolean {
    return code && code.length <= 50 && /^[A-Z0-9\-_]{1,50}$/.test(code);
  }

  /**
   * Validate group code format
   */
  static isValidGroupCode(code: string): boolean {
    return code && code.length <= 50 && /^[A-Z0-9\-_]{1,50}$/.test(code);
  }

  /**
   * Check if period_start is 1st of month
   */
  static isPeriodStart(dateStr: string): boolean {
    try {
      const d = new Date(dateStr);
      return d.getDate() === 1;
    } catch {
      return false;
    }
  }

  /**
   * Calculate efficiency percentage
   */
  static calculateEfficiency(
    expected: number | null | undefined,
    actual: number | null | undefined
  ): number | null {
    if (!expected || !actual) return null;
    if (expected === 0) return null;
    return Math.round((actual / expected) * 100 * 10) / 10; // 1 decimal
  }

  /**
   * Check if assignment status transition is valid
   */
  static isValidStatusTransition(
    from: AssignmentStatus,
    to: AssignmentStatus
  ): boolean {
    const valid: Record<AssignmentStatus, AssignmentStatus[]> = {
      [AssignmentStatus.SCHEDULED]: [AssignmentStatus.IN_PROGRESS, AssignmentStatus.CANCELLED],
      [AssignmentStatus.IN_PROGRESS]: [AssignmentStatus.COMPLETED, AssignmentStatus.CANCELLED],
      [AssignmentStatus.COMPLETED]: [],
      [AssignmentStatus.CANCELLED]: [],
    };
    return valid[from]?.includes(to) ?? false;
  }

  /**
   * Check if plan status transition is valid
   */
  static isValidPlanTransition(from: PlanStatus, to: PlanStatus): boolean {
    const valid: Record<PlanStatus, PlanStatus[]> = {
      [PlanStatus.DRAFT]: [PlanStatus.PUBLISHED],
      [PlanStatus.PUBLISHED]: [PlanStatus.IN_PROGRESS],
      [PlanStatus.IN_PROGRESS]: [PlanStatus.COMPLETED],
      [PlanStatus.COMPLETED]: [PlanStatus.ARCHIVED],
      [PlanStatus.ARCHIVED]: [],
    };
    return valid[from]?.includes(to) ?? false;
  }

  /**
   * Validate group capacity matches worker requirements
   */
  static validateGroupCapacity(groupCapacity: number, blockCapacity: number): boolean {
    // Allow small variance (e.g., 15±2)
    return Math.abs(groupCapacity - blockCapacity) <= 2;
  }
}
