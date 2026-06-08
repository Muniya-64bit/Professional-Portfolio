# Backend Module Test Analysis

## 1. MODULE: labour.py

### Core Business Logic Functions

#### `_generate_estate_plan(cur, estate_id, period_start, created_by=None, status='published', notes=None)`
- **Purpose**: Core monthly labour plan generation engine
- **Parameters**: 
  - `cur`: Database cursor
  - `estate_id`: UUID of estate
  - `period_start`: Date (first day of month)
  - `created_by`: UUID of user (optional)
  - `status`: 'published' | 'draft' (default 'published')
  - `notes`: Optional string
- **Returns**: Dictionary with:
  - `estate_id`, `created` (bool), `reason` (if not created), `plan_id`
  - `period_start`, `rotation_round`, `predicted_total_kg`, `total_workers`
  - `groups_covered`, `groups_doubled_up`, `ungrouped_employees`
- **Side Effects**: 
  - Inserts into `labour_plan`, `block_assignment`, updates `rotation_cycle`
  - Upserts `yield_prediction` records
  - **Idempotent**: Returns early if plan already exists for (estate_id, period_start)
  - **Transaction**: Caller manages commit/rollback
- **Key Logic**:
  - Computes predictions for all blocks
  - Maps rotation round groups to blocks
  - Full-coverage: assigns leftover groups to highest-predicted block
  - Advances rotation round by 1 (wraps at total_rounds)

#### `generate_monthly_plans(year, month, estate_id=None, created_by=None)`
- **Purpose**: Generate monthly plans for one or all estates
- **Parameters**:
  - `year`: Integer year
  - `month`: Integer month (1-12)
  - `estate_id`: UUID or None for all estates
  - `created_by`: UUID of user (optional)
- **Returns**: Tuple `(payload_dict, http_status_code)` where payload contains:
  - `period_start`, `estates_processed`, `plans_created`
  - `results`: List of plan creation results
- **Side Effects**: 
  - Creates own DB connection
  - Commits per estate (failure in one doesn't rollback others)
  - Calls `_generate_estate_plan()` for each estate
- **Error Handling**: Catches exceptions per estate, returns error reason in results

### Testable API Endpoints

#### Labour Plans
| Function | Route | Method | Parameters | Returns | Notable |
|----------|-------|--------|-----------|---------|---------|
| `list_plans()` | `/api/labour/plans` | GET | `estate_id` (QS), `period_start` (QS) | Array of plan objects | Joins with rotation_cycle, block_assignment; filters optional |
| `create_plan()` | `/api/labour/plans` | POST | Body: `estate_id`, `period_start`, `status?`, `notes?` | Created plan summary | Calls `_generate_estate_plan()`, HTTP 201/409 |
| `get_plan(plan_id)` | `/api/labour/plans/<id>` | GET | `plan_id` (path) | Plan object + assignments array | Includes predicted vs actual yields, efficiency calc |
| `update_plan(plan_id)` | `/api/labour/plans/<id>` | PUT | Body: `status`, `notes`, `total_workers`, `target_kg` (subset) | Success message | Only allowed fields can be updated |
| `generate_monthly()` | `/api/labour/plans/generate-monthly` | POST | Body: `year?`, `month?`, `estate_id?` | Results array | Defaults to next month if not provided |

#### Predictions
| Function | Route | Method | Parameters | Returns | Notable |
|----------|-------|--------|-----------|---------|---------|
| `list_predictions()` | `/api/labour/predictions` | GET | `estate_id?`, `year?`, `month?` (QS) | Array of yield_prediction objects | Includes confidence intervals |

#### Block Assignments & Overrides
| Function | Route | Method | Parameters | Returns | Notable |
|----------|-------|--------|-----------|---------|---------|
| `override_assignment(assignment_id)` | `/api/labour/assignments/<id>` | PUT | Body: `worker_group_id`, `override_reason`, `actual_yield_kg`, `expected_yield_kg`, `status`, `notes` (subset) | Updated assignment | Sets `is_manual_override=TRUE`, saves original group |
| `employee_override(assignment_id)` | `/api/labour/assignments/<id>/employee-override` | POST | Body: `employee_id`, `action` ('add'\|'remove'), `reason?` | Success | Creates/deletes EmployeeDayAssignment record |

#### Employee Management
| Function | Route | Method | Parameters | Returns | Notable |
|----------|-------|--------|-----------|---------|---------|
| `list_employees()` | `/api/labour/employees` | GET | `estate_id?` (QS) | Array of employee objects | Includes group membership, hire_date, employment_type |
| `create_employee()` | `/api/labour/employees` | POST | Body: `employee_code`, `full_name`, `employment_type`, `skill_type`, `hire_date`, `estate_id`, `gender?`, `national_id?`, `daily_wage_lkr?` | Created employee | Uses labour_validators.EmployeeValidator |
| `update_employee(employee_id)` | `/api/labour/employees/<id>` | PUT | Body: Subset of fields (not PK/FK) | Updated employee | Soft-update (is_active control) |
| `delete_employee(employee_id)` | `/api/labour/employees/<id>` | DELETE | None | Success message | Soft delete (sets is_active=FALSE) |

#### Worker Groups
| Function | Route | Method | Parameters | Returns | Notable |
|----------|-------|--------|-----------|---------|---------|
| `list_groups()` | `/api/labour/groups` | GET | `estate_id?` (QS) | Array of group objects | Includes member count, supervisor name |
| `update_group_member(group_id)` | `/api/labour/groups/<id>/member` | PUT | Body: `employee_id`, `action` ('add'\|'remove') | Updated membership | Enforces one-active-group-per-employee |

#### Rotation Cycles
| Function | Route | Method | Parameters | Returns | Notable |
|----------|-------|--------|-----------|---------|---------|
| `get_rotation()` | `/api/labour/rotation` | GET | `estate_id` (QS) | Active rotation cycle + round_block mapping | Defines group-to-block assignments per round |

#### Yield Recording & Efficiency
| Function | Route | Method | Parameters | Returns | Notable |
|----------|-------|--------|-----------|---------|---------|
| `record_plan_yield(plan_id)` | `/api/labour/plans/<id>/yield` | POST | Body: `block_id`, `actual_yield_kg` (array of records) | Updated assignments | Populates `actual_yield_kg` on block_assignments |
| `plan_efficiency(plan_id)` | `/api/labour/plans/<id>/efficiency` | GET | None | Efficiency breakdown per block/group | Calculates: (actual/expected) * 100 |

#### Estate & Block Management
| Function | Route | Method | Parameters | Returns | Notable |
|----------|-------|--------|-----------|---------|---------|
| `list_estates()` | `/api/labour/estates` | GET | `estate_id?` (QS) | Array of estates | Includes block count, region |
| `create_estate()` | `/api/labour/estates` | POST | Body: `name`, `region?`, `total_blocks?`, `worker_capacity?` | Created estate | Must have at least one block |
| `update_estate(estate_id)` | `/api/labour/estates/<id>` | PUT | Body: Subset of fields | Updated estate | Can't change PK/FK |
| `delete_estate(estate_id)` | `/api/labour/estates/<id>` | DELETE | None | Success message | Soft delete |
| `list_blocks()` | `/api/labour/blocks` | GET | `estate_id` (QS) | Array of blocks | Includes block_code, worker_capacity, status |
| `create_block()` | `/api/labour/blocks` | POST | Body: `estate_id`, `block_code`, `worker_capacity`, `crop_type?`, `area_hectares?` | Created block | Validates unique block_code per estate |
| `update_block(block_id)` | `/api/labour/blocks/<id>` | PUT | Body: Subset of fields | Updated block | |
| `delete_block(block_id)` | `/api/labour/blocks/<id>` | DELETE | None | Success message | Soft delete; can't delete if active assignments exist |

#### Manual Plan Management
| Function | Route | Method | Parameters | Returns | Notable |
|----------|-------|--------|-----------|---------|---------|
| `create_manual_plan()` | `/api/labour/plans/manual` | POST | Body: `estate_id`, `period_start`, `total_workers?`, `target_kg?`, `assignments` (list) | Created plan | Bypasses rotation; direct assignment specification |
| `add_assignment_to_plan(plan_id)` | `/api/labour/plans/<id>/assignment` | POST | Body: `block_id`, `worker_group_id`, `expected_yield_kg?` | Created assignment | Adds to existing plan |
| `change_group_assignment(assignment_id)` | `/api/labour/assignments/<id>/group` | PUT | Body: `worker_group_id` | Updated assignment | Changes group for existing block assignment |
| `remove_assignment(assignment_id)` | `/api/labour/assignments/<id>` | DELETE | None | Success message | Deletes block_assignment record |
| `remove_group_from_assignment(assignment_id)` | `/api/labour/assignments/<id>/remove-group` | PUT | None | Updated assignment | Sets `worker_group_id=NULL` |

### Helper Functions (Internal)
| Function | Purpose | Parameters | Returns |
|----------|---------|-----------|---------|
| `_to_json(v)` | Serializes UUID, Decimal, date/datetime to JSON | Value | JSON-serializable value |
| `_row_dict(cur, row)` | Converts database row to dict using cursor description | cursor, row tuple | Dictionary |
| `_rows(cur)` | Converts all fetchall() rows to list of dicts | cursor | List of dicts |
| `_db_err(e)` | Formats database errors as JSON | Exception | (JSON error response, 500) |
| `_db()` | Gets DB connection; returns None on failure | None | Connection or None |
| `_first_of_month(value)` | Normalizes date/datetime/string to first of month | date\|datetime\|str | date object |
| `_next_month(d)` | Gets first day of next month | date | date object |

---

## 2. MODULE: water.py

### Data Retrieval Functions (API Endpoints)

| Function | Route | Method | Parameters | Returns | Query Source | Notable |
|----------|-------|--------|-----------|---------|--------------|---------|
| `get_water_status()` | `/api/water/status` | GET | None | Array with: factory, estate, year, month, water_m3, yield_kg, intensity_l_per_kg, baseline_intensity, track_status | `v_water_status_latest` view | Latest month status for all factories |
| `get_water_usage()` | `/api/water/usage` | GET | `estate_id?`, `year?` (QS; default 2026) | Array with: id, factory, estate, year, month_num, month, water_m3, yield_kg, intensity_l_per_kg, track_status | `water_usage` ⨝ `factory` ⨝ `estate` | Joins 3 tables; filters optional |
| `get_water_baseline()` | `/api/water/baseline` | GET | None | Array with: id, factory, estate, baseline_year, baseline_intensity (l/kg), annual_target_pct | `water_baseline` ⨝ `factory` ⨝ `estate` | Historical baseline data + targets |
| `get_water_estates()` | `/api/water/estates` | GET | None | Array with: estate_id, estate_name, factory_id, factory_name | `estate` ⨝ `factory` | Maps estates to factories (1-to-1 or 1-to-many) |

### Helper Functions
| Function | Purpose |
|----------|---------|
| `get_db()` | Returns psycopg connection from DATABASE_URL env var |

### Calculations (Inline)
- **intensity_l_per_kg**: Converts database value m³/kg to liters/kg: `float(row[6]) * 1000`
- **baseline_intensity**: Converts to liters: `float(row[7]) * 1000`
- **month**: Maps month number to string abbreviation (Jan–Dec)

### Data Transformations
- All numeric values converted to `float()` for JSON serialization
- Null handling: intensity values can be None
- Months array used for human-readable format

---

## 3. MODULE: schemas.py

### Enums (Data Validation)
| Enum | Values | Purpose |
|------|--------|---------|
| `EmploymentType` | PERMANENT, CASUAL, SEASONAL | Employee contract classification |
| `SkillType` | PLUCKER, GENERAL, SUPERVISOR, DRIVER | Worker skill level/role |
| `PlanStatus` | DRAFT, PUBLISHED, IN_PROGRESS, COMPLETED, ARCHIVED | Labour plan lifecycle |
| `AssignmentStatus` | SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED | Block assignment state |
| `AssignmentType` | GROUP, MANUAL_ADD, MANUAL_REMOVE | Employee assignment override type |
| `Gender` | M, F, O | Employee gender |

### Schema Classes (Documentation)
| Class | Table | Key Fields | Constraints |
|-------|-------|-----------|-------------|
| `EmployeeSchema` | `employee` | `id` (UUID), `estate_id`, `employee_code`, `full_name`, `gender`, `national_id`, `hire_date`, `employment_type`, `skill_type`, `daily_wage_lkr`, `is_active`, `notes` | UNIQUE(estate_id, employee_code); daily_wage_lkr > 0 or NULL |
| `WorkerGroupSchema` | `worker_group` | `id` (UUID), `estate_id`, `group_code`, `group_name`, `supervisor_id`, `capacity`, `is_active` | UNIQUE(estate_id, group_code); capacity > 0 |
| `WorkerGroupMemberSchema` | `worker_group_member` | `id` (UUID), `group_id`, `employee_id`, `joined_date`, `left_date`, `is_active` | UNIQUE(employee_id) WHERE is_active=TRUE |
| `RotationCycleSchema` | `rotation_cycle` | `id` (UUID), `estate_id`, `cycle_name`, `total_rounds`, `current_round`, `is_active`, `created_by`, `created_at`, `updated_at` | UNIQUE(estate_id) WHERE is_active=TRUE; current_round BETWEEN 1 AND total_rounds |
| `RotationRoundBlockSchema` | `rotation_round_block` | `id`, `rotation_cycle_id`, `round_number`, `block_id`, `worker_group_id`, `created_at` | UNIQUE(cycle_id, round_num, block_id); UNIQUE(cycle_id, round_num, group_id) |
| `LabourPlanSchema` | `labour_plan` | `id` (UUID), `estate_id`, `period_start`, `total_workers`, `target_kg`, `status`, `notes`, `created_by`, `created_at`, `updated_at` | UNIQUE(estate_id, period_start); period_start always 1st of month |
| `BlockAssignmentSchema` | `block_assignment` | `id`, `labour_plan_id`, `block_id`, `worker_group_id`, `assignment_date`, `rotation_cycle_id`, `rotation_round`, `is_manual_override`, `original_group_id`, `override_reason`, `overridden_by`, `overridden_at`, `expected_yield_kg`, `actual_yield_kg`, `plucking_round_number`, `status`, `notes`, `created_at`, `updated_at` | UNIQUE(block_id, assignment_date); status IN enum |
| `EmployeeDayAssignmentSchema` | `employee_day_assignment` | `id`, `block_assignment_id`, `employee_id`, `assignment_type`, `kg_collected`, `added_by`, `reason`, `created_at`, `updated_at` | UNIQUE(block_assignment_id, employee_id) |

### Validation Rules (per schema documentation)
- **Employee**: code alphanumeric + unique per estate; name ≤150 chars; hire_date ≤ today; wage ≤ 999999.99
- **WorkerGroup**: code unique per estate; capacity > 0; supervisor must have skill_type='supervisor'
- **RotationCycle**: Only one active per estate; current_round must be valid (1–total_rounds)
- **Labour Plan**: period_start must be 1st of month; status follows lifecycle
- **Block Assignment**: Efficiency calculated as (actual/expected) * 100 if both present

---

## 4. MODULE: reports.py

### Data Fetching Function

#### `_fetch(estate_id, year, month)`
- **Purpose**: Single-query-pass to fetch all report data
- **Parameters**:
  - `estate_id`: UUID
  - `year`: Integer
  - `month`: Integer (1-12)
- **Returns**: Tuple `(data_dict, error_string)` or `(None, error_msg)` on failure
- **Side Effects**: 
  - Opens and closes DB connection
  - **No calculation** – raw data retrieval only
- **Data Returned** (in dict `d`):
  - `estate`: {id, name, region, total_blocks}
  - `plan`: {id, total_workers, target_kg, status} or None
  - `assignments`: [{block, group, capacity, expected, actual, efficiency, status}]
  - `groups`: [{code, name, capacity, headcount, supervisor}]
  - `total_employees`: Integer count
  - `by_skill`: {skill_type: count} dict
  - `by_type`: {employment_type: count} dict
  - `monthly_yield`: [{month, yield_kg}] for entire year
  - `weather`: [{month, rainfall_mm, avg_temp_c, avg_humidity_pct}] for year
  - `roi_snapshot`: {cost_per_kg, rank, is_flagged, flag_reason} or None
  - `roi_monthly_trend`: [{month, cost_per_kg}] for year
  - `year`, `month`: From parameters

### Chart Generation Functions

| Function | Input Type | Returns | Visual | Testable Aspects |
|----------|-----------|---------|--------|------------------|
| `_chart_yield_efficiency(assignments)` | List of assignment dicts with actual/expected | BytesIO PNG or None | Horizontal grouped bars (expected vs actual per block) with efficiency % labels | Filters items with actual; colors by efficiency (≥100%→green, ≥90%→orange, else red); empty input→None |
| `_chart_monthly_yield(monthly_yield)` | List of {month, yield_kg} | BytesIO PNG or None | Bar chart with trend line overlay (numpy polyfit if ≥3 points) | Value labels on bars; trend line only if ≥3 points; empty/short list→None |
| `_chart_weather(weather)` | List of {month, rainfall, temp, humidity} | BytesIO PNG or None | Dual-axis: rainfall bars + temp/humidity lines | Handles None values; legend combines both axes |
| `_chart_group_fill(groups)` | List of {code, capacity, headcount} | BytesIO PNG or None | Horizontal bar: capacity vs headcount per group with % label | Empty input→None; percent calculation handles 0 capacity |
| `_chart_roi_trend(monthly_roi)` | List of {month, cost_per_kg} | BytesIO PNG or None | Line chart with fill-under area + value labels on points | Empty/short list→None |

### PDF Builder Function

#### `_build_pdf(data)`
- **Purpose**: Constructs multi-page PDF report from data dict
- **Parameters**: `data` dict from `_fetch()`
- **Returns**: BytesIO buffer with PDF binary
- **Side Effects**: 
  - Imports reportlab modules (lazy import)
  - Calls all chart generators internally
  - Uses matplotlib/numpy for chart generation
- **Pages**:
  1. Cover page: Estate name, period, metadata table
  2. Executive summary: KPIs (efficiency %, kg/worker, variance)
  3. Charts: Yield efficiency, monthly trend, weather, group fill, ROI trend
  4. Detailed tables: Assignments, groups, employee breakdown
- **Styling**: 
  - Color palette with navy/primary/success/warning/danger colors
  - Borders, headers, footers, page numbers
  - Aspect ratio preservation for images

### API Endpoint

#### `generate_report()`
- **Route**: `/api/reports/generate`
- **Method**: POST
- **Body Parameters**:
  - `estate_id`: UUID (required)
  - `year`: Integer (required)
  - `month`: Integer (required, 1-12)
- **Returns**: 
  - Success: PDF file attachment (application/pdf) with filename `KVPL_{estate_name}_{year}_{month:02d}_Report.pdf`
  - Error 400: Missing/invalid parameters
  - Error 403: Forbidden (manager accessing different estate)
  - Error 404: Estate not found
  - Error 500: PDF build failed
  - Error 503: Database unavailable
- **Side Effects**: 
  - Calls `effective_estate_id()` for access control (managers ↔ their estate only)
  - Calls `_fetch()` then `_build_pdf()` sequentially
  - Streams file to client
- **Validation**:
  - Estate ID checked against user's allowed estate(s)
  - Month validated (1-12)
  - Year converted to int

### Helper Functions

| Function | Purpose | Parameters | Returns |
|----------|---------|-----------|---------|
| `_f(v)` | Converts Decimal to float, else returns as-is | Value | float or original type |
| `_db()` | Gets DB connection from auth module | None | Connection |
| `_apply_clean_style(ax, show_top=False, show_right=False)` | Removes chart borders/spines | matplotlib axis, bool flags | None (modifies axis) |
| `_save_fig(fig)` | Renders figure to PNG BytesIO | matplotlib figure | BytesIO buffer |

---

## Summary: Testable Functions by Category

### Critical Business Logic (High Priority)
- `_generate_estate_plan()` — Core plan generation with rotation + coverage logic
- `generate_monthly_plans()` — Batch generation for multiple estates
- `_fetch()` — Report data aggregation (7+ queries)
- `_build_pdf()` — Multi-page PDF assembly

### Data Validation (High Priority)
- Labour validators in `labour_validators.py` (not fully shown but referenced)
- Enum values in `schemas.py` for constraint checking
- Chart input validation (None/empty list handling)

### API Integration (Medium Priority)
- All `@labour_bp.route` endpoints (read/write operations)
- All `@water_bp.route` endpoints (read-only)
- `@reports_bp.route('/generate')` endpoint

### Data Transformation (Medium Priority)
- `_to_json()` — Serialization
- `_chart_*()` functions — Chart data transformation
- Month/date helpers in labour.py

### Edge Cases & Error Handling (Medium Priority)
- Idempotency in `_generate_estate_plan()`
- Null value handling in charts
- DB connection failures
- Permission checks (estate_id validation)

