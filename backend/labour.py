"""Labour planner API — routes and DB helpers."""
import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from flask import Blueprint, jsonify, request
from auth import (token_required, get_db_connection, write_required,
                  is_full_access, effective_estate_id)
from predictions import compute_block_predictions

logger = logging.getLogger(__name__)
labour_bp = Blueprint('labour', __name__, url_prefix='/api/labour')


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _to_json(v):
    if isinstance(v, (UUID,)):       return str(v)
    if isinstance(v, Decimal):       return float(v)
    if isinstance(v, (date, datetime)): return v.isoformat()
    return v

def _row_dict(cur, row):
    return {cur.description[i].name: _to_json(row[i]) for i in range(len(row))}

def _rows(cur):
    return [_row_dict(cur, r) for r in cur.fetchall()]

def _db_err(e):
    logger.error("DB error: %s", e, exc_info=True)
    return jsonify({'error': 'Database error'}), 500

def _db():
    conn = get_db_connection()
    if not conn:
        return None
    return conn


# ── Month / period helpers ────────────────────────────────────────────────────

def _first_of_month(value):
    """Normalize a date / datetime / 'YYYY-MM-DD' string to the 1st of its month."""
    if isinstance(value, str):
        value = datetime.strptime(value[:10], '%Y-%m-%d').date()
    elif isinstance(value, datetime):
        value = value.date()
    return value.replace(day=1)


def _next_month(d):
    """First day of the month after date d."""
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


# ── Monthly plan generation (shared by manual create + cron) ──────────────────

def _generate_estate_plan(cur, estate_id, period_start, created_by=None,
                          status='published', notes=None):
    """Create one estate's monthly labour plan and return a summary dict.

    Idempotent: if a plan already exists for (estate_id, period_start) it is
    skipped and the rotation round is NOT advanced.

    Pipeline: compute predictions → place rotation-round groups on blocks
    (expected_yield = prediction) → full-coverage pass so every active group is
    assigned a block (extra groups double up on the highest-predicted block) →
    fill plan totals → advance the rotation round by one month.

    The caller owns commit/rollback.
    """
    year, month = period_start.year, period_start.month

    # 1. Idempotency — one plan per estate per month
    cur.execute(
        "SELECT id FROM labour_plan WHERE estate_id = %s AND period_start = %s",
        (estate_id, period_start),
    )
    existing = cur.fetchone()
    if existing:
        return {'estate_id': str(estate_id), 'created': False,
                'reason': 'plan already exists', 'plan_id': str(existing[0])}

    # 2. Active rotation cycle defines which round (= this month) to lay down
    cur.execute(
        """SELECT id, current_round, total_rounds
           FROM rotation_cycle
           WHERE estate_id = %s AND is_active = TRUE""",
        (estate_id,),
    )
    cyc = cur.fetchone()
    if not cyc:
        return {'estate_id': str(estate_id), 'created': False,
                'reason': 'no active rotation cycle'}
    cycle_id, current_round, total_rounds = cyc

    # 3. Predictions for every block this month (also upserts yield_prediction)
    predictions = compute_block_predictions(cur, estate_id, year, month)

    # 4. Rotation round → which group covers which block
    cur.execute(
        """SELECT block_id, worker_group_id
           FROM rotation_round_block
           WHERE rotation_cycle_id = %s AND round_number = %s""",
        (cycle_id, current_round),
    )
    round_rows = cur.fetchall()

    # All active groups + capacities (for coverage + headcount)
    cur.execute(
        "SELECT id, capacity FROM worker_group WHERE estate_id = %s AND is_active = TRUE",
        (estate_id,),
    )
    group_capacity = {str(gid): cap for gid, cap in cur.fetchall()}

    # assignment tuples: (block_id, group_id, expected_yield, note)
    assignments = []
    assigned_groups = set()
    round_block_ids = []
    for block_id, group_id in round_rows:
        assignments.append((block_id, group_id,
                            predictions.get(str(block_id)), None))
        assigned_groups.add(str(group_id))
        round_block_ids.append(block_id)

    # 5. Full-coverage pass — every active group must have a workspace.
    #    Leftover groups double up on the highest-predicted block this round.
    target_block = None
    if round_block_ids:
        target_block = max(round_block_ids,
                           key=lambda b: predictions.get(str(b), 0) or 0)
    leftover = [g for g in group_capacity if g not in assigned_groups]
    for group_id in leftover:
        if target_block is None:
            break
        assignments.append((target_block, group_id, None,
                            'auto-assigned for full coverage'))
        assigned_groups.add(group_id)

    # Ungrouped active employees can't be auto-placed — report them.
    cur.execute(
        """SELECT COUNT(*) FROM employee e
           WHERE e.estate_id = %s AND e.is_active = TRUE
             AND NOT EXISTS (
                 SELECT 1 FROM worker_group_member m
                 WHERE m.employee_id = e.id AND m.is_active = TRUE)""",
        (estate_id,),
    )
    ungrouped = cur.fetchone()[0]

    # 6. Plan totals
    target_kg = round(sum((predictions.get(str(b)) or 0) for b in round_block_ids), 3)
    total_workers = sum(group_capacity.get(g, 0) for g in assigned_groups) or 1

    cur.execute(
        """INSERT INTO labour_plan
               (estate_id, created_by, period_start, total_workers, target_kg, status, notes)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (estate_id, created_by, period_start, total_workers, target_kg, status,
         notes or f'Auto-generated monthly plan — round {current_round}'),
    )
    plan_id = cur.fetchone()[0]

    # 7. Block assignments
    for block_id, group_id, expected, note in assignments:
        cur.execute(
            """INSERT INTO block_assignment
                   (labour_plan_id, block_id, worker_group_id, assignment_date,
                    rotation_cycle_id, rotation_round, expected_yield_kg, status, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'scheduled', %s)
               ON CONFLICT (block_id, assignment_date, worker_group_id) DO NOTHING""",
            (plan_id, block_id, group_id, period_start,
             cycle_id, current_round, expected, note),
        )

    # 8. Link this month's predictions to the plan
    cur.execute(
        """UPDATE yield_prediction SET labour_plan_id = %s
           WHERE year = %s AND month = %s
             AND block_id IN (SELECT id FROM block WHERE estate_id = %s)""",
        (plan_id, year, month, estate_id),
    )

    # 9. Advance the rotation round for next month (wraps at total_rounds)
    cur.execute(
        """UPDATE rotation_cycle
           SET current_round = (current_round %% total_rounds) + 1, updated_at = NOW()
           WHERE id = %s""",
        (cycle_id,),
    )

    return {
        'estate_id':         str(estate_id),
        'created':           True,
        'plan_id':           str(plan_id),
        'period_start':      period_start.isoformat(),
        'rotation_round':    current_round,
        'predicted_total_kg': target_kg,
        'total_workers':     total_workers,
        'groups_covered':    len(assigned_groups),
        'groups_doubled_up': len(leftover),
        'ungrouped_employees': ungrouped,
    }


def generate_monthly_plans(year, month, estate_id=None, created_by=None):
    """Generate monthly plans for one or all estates. Owns its own connection.

    Shared by the manual endpoint and the scheduler. Commits per estate so one
    estate failing does not roll back the others. Returns (payload, http_status).
    """
    conn = _db()
    if not conn:
        return {'error': 'Database unavailable'}, 503

    period_start = date(int(year), int(month), 1)
    results = []
    try:
        with conn.cursor() as cur:
            if estate_id:
                estate_ids = [estate_id]
            else:
                cur.execute("SELECT id FROM estate ORDER BY name")
                estate_ids = [r[0] for r in cur.fetchall()]

            for eid in estate_ids:
                try:
                    summary = _generate_estate_plan(
                        cur, eid, period_start, created_by=created_by)
                    conn.commit()
                    results.append(summary)
                except Exception as e:
                    conn.rollback()
                    logger.error("Monthly generation failed for estate %s: %s",
                                 eid, e, exc_info=True)
                    results.append({'estate_id': str(eid), 'created': False,
                                    'reason': f'error: {e}'})
        created = sum(1 for r in results if r.get('created'))
        return ({'period_start': period_start.isoformat(),
                 'estates_processed': len(results),
                 'plans_created': created,
                 'results': results}, 200)
    finally:
        conn.close()


# ── Labour Plans ──────────────────────────────────────────────────────────────

@labour_bp.route('/plans', methods=['GET'])
@token_required
def list_plans():
    """GET /api/labour/plans  ?estate_id=  &period_start="""
    estate_id, err = effective_estate_id(request.args.get('estate_id'))
    if err:
        return err
    period_start = request.args.get('period_start')
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT lp.id, lp.period_start, lp.total_workers, lp.target_kg,
                       lp.status, lp.notes, lp.created_at,
                       e.name  AS estate_name,
                       e.id    AS estate_id,
                       rc.cycle_name,
                       rc.current_round,
                       rc.total_rounds,
                       COUNT(ba.id)                    AS blocks_assigned,
                       COALESCE(SUM(ba.expected_yield_kg), 0) AS expected_total_kg,
                       COALESCE(SUM(ba.actual_yield_kg),  0) AS actual_total_kg
                FROM labour_plan lp
                JOIN estate e   ON e.id  = lp.estate_id
                LEFT JOIN rotation_cycle rc
                       ON rc.estate_id = lp.estate_id AND rc.is_active = TRUE
                LEFT JOIN block_assignment ba ON ba.labour_plan_id = lp.id
            """
            where, params = [], []
            if estate_id:
                where.append("lp.estate_id = %s"); params.append(estate_id)
            if period_start:
                where.append("lp.period_start = %s")
                params.append(_first_of_month(period_start))
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += (" GROUP BY lp.id, e.name, e.id, "
                    "rc.cycle_name, rc.current_round, rc.total_rounds "
                    "ORDER BY lp.period_start DESC")
            cur.execute(sql, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/plans', methods=['POST'])
@token_required
@write_required
def create_plan():
    """POST /api/labour/plans — create one estate's monthly plan.

    Body: { estate_id, period_start (any day of the month), status?, notes? }
    Worker assignments, expected yields (predictions) and totals are generated
    automatically from the active rotation round.
    """
    data         = request.get_json() or {}
    estate_id    = data.get('estate_id')
    period_raw   = data.get('period_start') or data.get('week_start')
    user_id      = request.user.get('user_id')

    if not estate_id or not period_raw:
        return jsonify({'error': 'estate_id and period_start are required'}), 400

    period_start = _first_of_month(period_raw)

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            summary = _generate_estate_plan(
                cur, estate_id, period_start, created_by=user_id,
                status=data.get('status', 'draft'), notes=data.get('notes'))
            conn.commit()
        if not summary.get('created'):
            return jsonify(summary), 409
        return jsonify(summary), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/plans/<plan_id>', methods=['GET'])
@token_required
def get_plan(plan_id):
    """GET /api/labour/plans/<id> — plan header + all block assignments."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT lp.id, lp.period_start, lp.total_workers, lp.target_kg,
                       lp.status, lp.notes, lp.created_at,
                       e.name AS estate_name, e.id AS estate_id,
                       rc.cycle_name, rc.current_round, rc.total_rounds
                FROM labour_plan lp
                JOIN estate e ON e.id = lp.estate_id
                LEFT JOIN rotation_cycle rc
                       ON rc.estate_id = lp.estate_id AND rc.is_active = TRUE
                WHERE lp.id = %s
            """, (plan_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Plan not found'}), 404
            plan = _row_dict(cur, row)

            if not is_full_access() and str(plan.get('estate_id')) != str(request.user.get('estate_id')):
                return jsonify({'error': 'Forbidden'}), 403

            cur.execute("""
                SELECT ba.id, b.block_code, b.worker_capacity,
                       wg.group_name, wg.group_code, wg.capacity AS group_capacity,
                       ba.assignment_date, ba.rotation_round, ba.is_manual_override,
                       ba.expected_yield_kg, ba.actual_yield_kg,
                       ba.plucking_round_number, ba.status, ba.notes,
                       og.group_name AS original_group_name,
                       ba.override_reason,
                       COALESCE(yp.predicted_yield_kg, ba.expected_yield_kg) AS predicted_yield_kg
                FROM block_assignment ba
                JOIN block b ON b.id = ba.block_id
                LEFT JOIN worker_group wg ON wg.id = ba.worker_group_id
                LEFT JOIN worker_group og ON og.id = ba.original_group_id
                LEFT JOIN yield_prediction yp ON yp.block_id = b.id
                       AND yp.year = EXTRACT(YEAR FROM %s::DATE)
                       AND yp.month = EXTRACT(MONTH FROM %s::DATE)
                WHERE ba.labour_plan_id = %s
                ORDER BY b.block_code
            """, (plan['period_start'], plan['period_start'], plan_id))
            plan['assignments'] = _rows(cur)
        return jsonify(plan), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/plans/<plan_id>', methods=['PUT'])
@token_required
@write_required
def update_plan(plan_id):
    """PUT /api/labour/plans/<id> — update status / notes / totals."""
    data = request.get_json() or {}
    allowed = {'status', 'notes', 'total_workers', 'target_kg'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sets   = ', '.join(f"{k} = %s" for k in updates)
            params = list(updates.values()) + [plan_id]
            cur.execute(f"UPDATE labour_plan SET {sets}, updated_at = NOW() WHERE id = %s", params)
            if cur.rowcount == 0:
                return jsonify({'error': 'Plan not found'}), 404
            conn.commit()
        return jsonify({'message': 'Plan updated'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Monthly auto-generation + predictions ─────────────────────────────────────

@labour_bp.route('/plans/generate-monthly', methods=['POST'])
@token_required
@write_required
def generate_monthly():
    """POST /api/labour/plans/generate-monthly
    Body (all optional): { year, month, estate_id }
    Defaults to NEXT month for all estates. Mirrors what the monthly cron runs.
    """
    data    = request.get_json() or {}
    user_id = request.user.get('user_id')

    if data.get('year') and data.get('month'):
        year, month = int(data['year']), int(data['month'])
    else:
        nxt = _next_month(date.today())
        year, month = nxt.year, nxt.month

    result, status = generate_monthly_plans(
        year, month, estate_id=data.get('estate_id'), created_by=user_id)
    return jsonify(result), status


@labour_bp.route('/predictions', methods=['GET'])
@token_required
def list_predictions():
    """GET /api/labour/predictions  ?estate_id=  &year=  &month="""
    estate_id, err = effective_estate_id(request.args.get('estate_id'))
    if err:
        return err
    year      = request.args.get('year')
    month     = request.args.get('month')

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT yp.id, yp.block_id, b.block_code, yp.year, yp.month,
                       yp.predicted_yield_kg, yp.confidence_low, yp.confidence_high,
                       yp.model_version, yp.labour_plan_id, b.estate_id
                FROM yield_prediction yp
                JOIN block b ON b.id = yp.block_id
            """
            where, params = [], []
            if estate_id:
                where.append("b.estate_id = %s"); params.append(estate_id)
            if year:
                where.append("yp.year = %s");  params.append(int(year))
            if month:
                where.append("yp.month = %s"); params.append(int(month))
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY b.block_code"
            cur.execute(sql, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


# ── Block Assignments ─────────────────────────────────────────────────────────

@labour_bp.route('/assignments/<assignment_id>', methods=['PUT'])
@token_required
@write_required
def override_assignment(assignment_id):
    """PUT /api/labour/assignments/<id>
    Body fields (all optional):
      worker_group_id, override_reason, actual_yield_kg, expected_yield_kg, status, notes
    """
    data    = request.get_json() or {}
    user_id = request.user.get('user_id')

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT worker_group_id FROM block_assignment WHERE id = %s", (assignment_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Assignment not found'}), 404
            current_group = row[0]

            sets, params = ['updated_at = NOW()'], []

            new_group = data.get('worker_group_id')
            if new_group and str(new_group) != str(current_group):
                sets  += ['worker_group_id = %s', 'original_group_id = %s',
                           'is_manual_override = TRUE', 'override_reason = %s',
                           'overridden_by = %s', 'overridden_at = NOW()']
                params += [new_group, current_group, data.get('override_reason'), user_id]

            for field in ('actual_yield_kg', 'expected_yield_kg', 'status', 'notes'):
                if field in data:
                    sets.append(f"{field} = %s")
                    params.append(data[field])

            params.append(assignment_id)
            cur.execute(f"UPDATE block_assignment SET {', '.join(sets)} WHERE id = %s", params)
            conn.commit()
        return jsonify({'message': 'Assignment updated'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/assignments/<assignment_id>/employee-overrides', methods=['POST'])
@token_required
@write_required
def employee_override(assignment_id):
    """POST /api/labour/assignments/<id>/employee-overrides
    Body: { employee_id, assignment_type: manual_add|manual_remove, reason }
    """
    data    = request.get_json() or {}
    emp_id  = data.get('employee_id')
    kind    = data.get('assignment_type')
    reason  = data.get('reason', '')
    user_id = request.user.get('user_id')

    if not emp_id or kind not in ('manual_add', 'manual_remove'):
        return jsonify({'error': 'employee_id and assignment_type (manual_add|manual_remove) required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO employee_day_assignment
                    (block_assignment_id, employee_id, assignment_type, added_by, reason)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (block_assignment_id, employee_id)
                DO UPDATE SET assignment_type = EXCLUDED.assignment_type,
                              reason = EXCLUDED.reason,
                              updated_at = NOW()
            """, (assignment_id, emp_id, kind, user_id, reason))
            conn.commit()
        return jsonify({'message': f'Employee {kind} recorded'}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Employees ─────────────────────────────────────────────────────────────────

@labour_bp.route('/employees', methods=['GET'])
@token_required
def list_employees():
    """GET /api/labour/employees  ?estate_id=  &group_id=  &skill_type="""
    estate_id, err = effective_estate_id(request.args.get('estate_id'))
    if err:
        return err
    group_id   = request.args.get('group_id')
    skill_type = request.args.get('skill_type')

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT emp.id, emp.employee_code, emp.full_name, emp.gender,
                       emp.hire_date, emp.employment_type, emp.skill_type,
                       emp.daily_wage_lkr, emp.is_active, emp.notes,
                       wg.group_name, wg.group_code, wg.id AS group_id
                FROM employee emp
                LEFT JOIN worker_group_member wgm
                       ON wgm.employee_id = emp.id AND wgm.is_active = TRUE
                LEFT JOIN worker_group wg ON wg.id = wgm.group_id
            """
            where, params = ['emp.is_active = TRUE'], []
            if estate_id:
                where.append("emp.estate_id = %s"); params.append(estate_id)
            if group_id:
                where.append("wgm.group_id = %s"); params.append(group_id)
            if skill_type:
                where.append("emp.skill_type = %s"); params.append(skill_type)
            sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY wg.group_code NULLS LAST, emp.skill_type DESC, emp.full_name"
            cur.execute(sql, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/employees', methods=['POST'])
@token_required
def create_employee():
    """POST /api/labour/employees — add a new field worker."""
    data = request.get_json() or {}
    required = ('estate_id', 'employee_code', 'full_name', 'hire_date')
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing: {", ".join(missing)}'}), 400

    # Scope check: managers can only add to their own estate
    estate_id, err = effective_estate_id(data.get('estate_id'))
    if err:
        return err

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO employee (
                    estate_id, employee_code, full_name, gender, national_id,
                    hire_date, employment_type, skill_type, daily_wage_lkr, notes
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                estate_id, data['employee_code'], data['full_name'],
                data.get('gender'), data.get('national_id'), data['hire_date'],
                data.get('employment_type', 'permanent'),
                data.get('skill_type', 'plucker'),
                data.get('daily_wage_lkr'),
                data.get('notes', ''),
            ))
            emp_id = str(cur.fetchone()[0])

            group_id = data.get('group_id')
            if group_id:
                # Remove from any current group first
                cur.execute("""
                    UPDATE worker_group_member
                    SET is_active = FALSE,
                        left_date = CASE WHEN CURRENT_DATE > joined_date THEN CURRENT_DATE ELSE joined_date + INTERVAL '1 day' END,
                        updated_at = NOW()
                    WHERE employee_id = %s AND is_active = TRUE
                """, (emp_id,))
                cur.execute("""
                    INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
                    VALUES (%s, %s, %s, TRUE)
                """, (group_id, emp_id, data['hire_date']))
                # If skill_type is 'supervisor', set as supervisor for this group
                if data.get('skill_type') == 'supervisor':
                    cur.execute("""
                        UPDATE worker_group SET supervisor_id = %s WHERE id = %s
                    """, (emp_id, group_id))

            conn.commit()
        return jsonify({'id': emp_id, 'message': 'Employee created'}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/employees/<employee_id>', methods=['PUT'])
@token_required
@write_required
def update_employee(employee_id):
    """PUT /api/labour/employees/<id> — update profile fields."""
    data    = request.get_json() or {}
    allowed = {'full_name', 'gender', 'national_id', 'employment_type',
               'skill_type', 'daily_wage_lkr', 'is_active', 'notes'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': 'No valid fields'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sets   = ', '.join(f"{k} = %s" for k in updates)
            params = list(updates.values()) + [employee_id]
            cur.execute(f"UPDATE employee SET {sets}, updated_at = NOW() WHERE id = %s", params)
            if cur.rowcount == 0:
                return jsonify({'error': 'Employee not found'}), 404

            # If group_id provided, move the employee to that group
            group_id = data.get('group_id')
            if group_id is not None:
                # Deactivate current membership
                cur.execute("""
                    UPDATE worker_group_member
                    SET is_active = FALSE,
                        left_date = CASE WHEN CURRENT_DATE > joined_date THEN CURRENT_DATE ELSE joined_date + INTERVAL '1 day' END,
                        updated_at = NOW()
                    WHERE employee_id = %s AND is_active = TRUE
                """, (employee_id,))
                # Assign to new group if not empty string
                if group_id:
                    cur.execute("""
                        INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
                        VALUES (%s, %s, CURRENT_DATE, TRUE)
                        ON CONFLICT (group_id, employee_id)
                        DO UPDATE SET is_active = TRUE, left_date = NULL, updated_at = NOW()
                    """, (group_id, employee_id))
                    # If skill_type is 'supervisor', set as supervisor for this group
                    if updates.get('skill_type') == 'supervisor':
                        cur.execute("""
                            UPDATE worker_group SET supervisor_id = %s WHERE id = %s
                        """, (employee_id, group_id))

            conn.commit()
        return jsonify({'message': 'Employee updated'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/employees/<employee_id>', methods=['DELETE'])
@token_required
@write_required
def delete_employee(employee_id):
    """DELETE /api/labour/employees/<id> — soft delete (sets is_active = FALSE)."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            # Soft delete the employee
            cur.execute("""
                UPDATE employee SET is_active = FALSE, updated_at = NOW()
                WHERE id = %s AND is_active = TRUE
            """, (employee_id,))
            if cur.rowcount == 0:
                return jsonify({'error': 'Employee not found'}), 404

            # Clear supervisor assignment for this employee's group if they were a supervisor
            cur.execute("""
                UPDATE worker_group SET supervisor_id = NULL
                WHERE supervisor_id = %s AND supervisor_id IS NOT NULL
            """, (employee_id,))

            # Deactivate group membership
            cur.execute("""
                UPDATE worker_group_member
                SET is_active = FALSE,
                    left_date = CASE WHEN CURRENT_DATE > joined_date THEN CURRENT_DATE ELSE joined_date + INTERVAL '1 day' END,
                    updated_at = NOW()
                WHERE employee_id = %s AND is_active = TRUE
            """, (employee_id,))

            conn.commit()
        return jsonify({'message': 'Employee deactivated'}), 200
    except Exception as e:
        logger.error("Delete employee error: %s", str(e), exc_info=True)
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Worker Groups ─────────────────────────────────────────────────────────────

@labour_bp.route('/groups', methods=['GET'])
@token_required
def list_groups():
    """GET /api/labour/groups  ?estate_id="""
    estate_id, err = effective_estate_id(request.args.get('estate_id'))
    if err:
        return err
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT wg.id, wg.group_code, wg.group_name, wg.capacity,
                       wg.is_active, e.name AS estate_name, e.id AS estate_id,
                       sup.full_name AS supervisor_name,
                       sup.employee_code AS supervisor_code,
                       COUNT(wgm.id) AS current_headcount
                FROM worker_group wg
                JOIN estate e ON e.id = wg.estate_id
                LEFT JOIN employee sup ON sup.id = wg.supervisor_id
                LEFT JOIN worker_group_member wgm
                       ON wgm.group_id = wg.id AND wgm.is_active = TRUE
                WHERE wg.is_active = TRUE
            """
            params = []
            if estate_id:
                sql += " AND wg.estate_id = %s"; params.append(estate_id)
            sql += (" GROUP BY wg.id, wg.group_code, wg.group_name, wg.capacity, "
                    "wg.is_active, e.name, e.id, sup.full_name, sup.employee_code "
                    "ORDER BY wg.group_code")
            cur.execute(sql, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/groups/<group_id>/members', methods=['POST'])
@token_required
@write_required
def update_group_member(group_id):
    """POST /api/labour/groups/<id>/members
    Body: { employee_id, action: add|remove }
    """
    data       = request.get_json() or {}
    employee_id = data.get('employee_id')
    action      = data.get('action')
    if not employee_id or action not in ('add', 'remove'):
        return jsonify({'error': 'employee_id and action (add|remove) required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            if action == 'add':
                # Deactivate current membership first
                cur.execute("""
                    UPDATE worker_group_member
                    SET is_active = FALSE, left_date = CURRENT_DATE, updated_at = NOW()
                    WHERE employee_id = %s AND is_active = TRUE
                """, (employee_id,))
                cur.execute("""
                    INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
                    VALUES (%s, %s, CURRENT_DATE, TRUE)
                """, (group_id, employee_id))
            else:
                cur.execute("""
                    UPDATE worker_group_member
                    SET is_active = FALSE, left_date = CURRENT_DATE, updated_at = NOW()
                    WHERE group_id = %s AND employee_id = %s AND is_active = TRUE
                """, (group_id, employee_id))
            conn.commit()
        return jsonify({'message': f'Member {action}ed'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Rotation ──────────────────────────────────────────────────────────────────

@labour_bp.route('/rotation', methods=['GET'])
@token_required
def get_rotation():
    """GET /api/labour/rotation  ?estate_id=
    Returns active rotation cycle(s) with full block-group matrix.
    """
    estate_id, err = effective_estate_id(request.args.get('estate_id'))
    if err:
        return err
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT rc.id, rc.cycle_name, rc.total_rounds, rc.current_round,
                       e.name AS estate_name, e.id AS estate_id
                FROM rotation_cycle rc
                JOIN estate e ON e.id = rc.estate_id
                WHERE rc.is_active = TRUE
            """
            params = []
            if estate_id:
                sql += " AND rc.estate_id = %s"; params.append(estate_id)
            cur.execute(sql, params)
            cycles = _rows(cur)

            for cycle in cycles:
                cur.execute("""
                    SELECT rrb.round_number, b.block_code,
                           wg.group_name, wg.group_code, wg.capacity
                    FROM rotation_round_block rrb
                    JOIN block b        ON b.id  = rrb.block_id
                    JOIN worker_group wg ON wg.id = rrb.worker_group_id
                    WHERE rrb.rotation_cycle_id = %s
                    ORDER BY rrb.round_number, b.block_code
                """, (cycle['id'],))
                matrix = {}
                for row in cur.fetchall():
                    d = _row_dict(cur, row)
                    rn = d['round_number']
                    matrix.setdefault(rn, []).append({
                        'block_code':  d['block_code'],
                        'group_name':  d['group_name'],
                        'group_code':  d['group_code'],
                        'capacity':    d['capacity'],
                    })
                cycle['matrix'] = matrix
        return jsonify(cycles), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


# ── Yield recording + efficiency ─────────────────────────────────────────────

@labour_bp.route('/plans/<plan_id>/record-yield', methods=['POST'])
@token_required
def record_plan_yield(plan_id):
    """POST /api/labour/plans/<plan_id>/record-yield

    Records actual harvest yield for one or more block assignments in a plan.
    Also upserts into block_yield_record so the prediction model learns from
    real outcomes over time.

    Body: { yields: [{ assignment_id, actual_yield_kg }] }
    """
    data   = request.get_json() or {}
    yields = data.get('yields', [])
    if not yields:
        return jsonify({'error': 'yields array is required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT period_start, estate_id FROM labour_plan WHERE id = %s", (plan_id,))
            plan_row = cur.fetchone()
            if not plan_row:
                return jsonify({'error': 'Plan not found'}), 404
            year  = plan_row[0].year
            month = plan_row[0].month
            plan_estate_id = plan_row[1]

            # Scope check: managers can only record yields for their own estate
            _, err = effective_estate_id(plan_estate_id)
            if err:
                return err

            updated = 0
            for entry in yields:
                assignment_id = entry.get('assignment_id')
                actual_kg     = entry.get('actual_yield_kg')
                if assignment_id is None or actual_kg is None:
                    continue

                cur.execute("""
                    UPDATE block_assignment
                    SET actual_yield_kg = %s, updated_at = NOW()
                    WHERE id = %s AND labour_plan_id = %s
                    RETURNING block_id
                """, (actual_kg, assignment_id, plan_id))
                row = cur.fetchone()
                if not row:
                    continue
                block_id = row[0]
                updated += 1

                # Sum all recorded actuals for this block in this plan so that
                # block_yield_record holds the total block yield (not per-group).
                cur.execute("""
                    SELECT COALESCE(SUM(actual_yield_kg), 0)
                    FROM block_assignment
                    WHERE labour_plan_id = %s AND block_id = %s
                      AND actual_yield_kg IS NOT NULL
                """, (plan_id, block_id))
                block_total = float(cur.fetchone()[0])

                cur.execute("""
                    INSERT INTO block_yield_record
                        (block_id, year, month, yield_kg, source)
                    VALUES (%s, %s, %s, %s, 'labour_plan')
                    ON CONFLICT (block_id, year, month)
                    DO UPDATE SET yield_kg = EXCLUDED.yield_kg, updated_at = NOW()
                """, (block_id, year, month, block_total))

            conn.commit()
        return jsonify({'message': f'{updated} assignment(s) updated',
                        'updated': updated}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/plans/<plan_id>/efficiency', methods=['GET'])
@token_required
def plan_efficiency(plan_id):
    """GET /api/labour/plans/<plan_id>/efficiency

    Returns efficiency metrics comparing actual vs expected yield.
    Efficiency is only computed for assignments where actual_yield_kg has been
    recorded; assignments still awaiting harvest show null efficiency.
    """
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT lp.id, lp.period_start, lp.total_workers, lp.target_kg,
                       lp.status, e.name AS estate_name, e.id AS estate_id
                FROM labour_plan lp
                JOIN estate e ON e.id = lp.estate_id
                WHERE lp.id = %s
            """, (plan_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Plan not found'}), 404
            plan = _row_dict(cur, row)

            if not is_full_access() and str(plan.get('estate_id')) != str(request.user.get('estate_id')):
                return jsonify({'error': 'Forbidden'}), 403

            cur.execute("""
                SELECT ba.id AS assignment_id,
                       b.block_code,
                       wg.group_name, wg.group_code,
                       ba.expected_yield_kg, ba.actual_yield_kg,
                       ba.status
                FROM block_assignment ba
                JOIN block b ON b.id = ba.block_id
                LEFT JOIN worker_group wg ON wg.id = ba.worker_group_id
                WHERE ba.labour_plan_id = %s
                ORDER BY b.block_code
            """, (plan_id,))
            assignments = _rows(cur)

        # Per-assignment efficiency
        for a in assignments:
            exp = a.get('expected_yield_kg')
            act = a.get('actual_yield_kg')
            if exp is not None and act is not None and float(exp) > 0:
                a['efficiency_pct'] = round(float(act) / float(exp) * 100, 2)
                a['variance_kg']    = round(float(act) - float(exp), 3)
            else:
                a['efficiency_pct'] = None
                a['variance_kg']    = None

        # Plan-level rollup
        expected_total = sum(
            float(a['expected_yield_kg']) for a in assignments
            if a.get('expected_yield_kg') is not None)
        actual_total = sum(
            float(a['actual_yield_kg']) for a in assignments
            if a.get('actual_yield_kg') is not None)
        total_workers = plan.get('total_workers') or 1

        plan['expected_total_kg']  = round(expected_total, 3)
        plan['actual_total_kg']    = round(actual_total, 3)
        plan['variance_kg']        = round(actual_total - expected_total, 3)
        plan['plan_efficiency_pct'] = (
            round(actual_total / expected_total * 100, 2)
            if expected_total > 0 and actual_total > 0 else None)
        plan['kg_per_worker'] = (
            round(actual_total / total_workers, 2)
            if actual_total > 0 else None)
        plan['assignments_recorded'] = sum(
            1 for a in assignments if a.get('actual_yield_kg') is not None)
        plan['assignments_pending']  = sum(
            1 for a in assignments if a.get('actual_yield_kg') is None)
        plan['assignments'] = assignments

        return jsonify(plan), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


# ── Estates (needed for estate selector in frontend) ──────────────────────────

@labour_bp.route('/estates', methods=['GET'])
@token_required
def list_estates():
    """GET /api/labour/estates — estates with block count.

    Full-access roles see all estates; a manager sees only their own.
    """
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT e.id, e.name, e.region, e.total_blocks,
                       COUNT(b.id) AS block_count
                FROM estate e
                LEFT JOIN block b ON b.estate_id = e.id
            """
            params = []
            if not is_full_access():
                sql += " WHERE e.id = %s"
                params.append(request.user.get('estate_id'))
            sql += (" GROUP BY e.id, e.name, e.region, e.total_blocks"
                    " ORDER BY e.name")
            cur.execute(sql, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


# ── Block Management ──────────────────────────────────────────────────────────

@labour_bp.route('/blocks', methods=['GET'])
@token_required
def list_blocks():
    """GET /api/labour/blocks?estate_id=<id> — list blocks for an estate."""
    estate_id, err = effective_estate_id(request.args.get('estate_id'))
    if err:
        return err
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT id, estate_id, block_code, soil_type, growth_stage, area_hectares, state
                FROM block WHERE estate_id = %s
                ORDER BY block_code
            """
            cur.execute(sql, (estate_id,))
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/blocks', methods=['POST'])
@token_required
@write_required
def create_block():
    """POST /api/labour/blocks — create a new block."""
    data = request.get_json() or {}
    required = ('estate_id', 'block_code')
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing: {", ".join(missing)}'}), 400

    estate_id, err = effective_estate_id(data.get('estate_id'))
    if err:
        return err

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO block (estate_id, block_code, soil_type, growth_stage, area_hectares, state)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                estate_id,
                data['block_code'],
                data.get('soil_type'),
                data.get('growth_stage'),
                data.get('area_hectares'),
                data.get('state', 'active'),
            ))
            block_id = str(cur.fetchone()[0])
            conn.commit()
        return jsonify({'id': block_id, 'message': 'Block created'}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/blocks/<block_id>', methods=['PUT'])
@token_required
@write_required
def update_block(block_id):
    """PUT /api/labour/blocks/<id> — update block details."""
    data = request.get_json() or {}
    allowed = {'block_code', 'soil_type', 'growth_stage', 'area_hectares', 'state'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': 'No valid fields'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sets = ', '.join(f"{k} = %s" for k in updates)
            params = list(updates.values()) + [block_id]
            cur.execute(f"UPDATE block SET {sets}, updated_at = NOW() WHERE id = %s", params)
            if cur.rowcount == 0:
                return jsonify({'error': 'Block not found'}), 404
            conn.commit()
        return jsonify({'message': 'Block updated'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/blocks/<block_id>', methods=['DELETE'])
@token_required
@write_required
def delete_block(block_id):
    """DELETE /api/labour/blocks/<id> — delete a block."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM block WHERE id = %s", (block_id,))
            if cur.rowcount == 0:
                return jsonify({'error': 'Block not found'}), 404
            conn.commit()
        return jsonify({'message': 'Block deleted'}), 200
    except Exception as e:
        conn.rollback()
        logger.error("Delete block error: %s", str(e), exc_info=True)
        return _db_err(e)
    finally:
        conn.close()


# ── Estate Management ──────────────────────────────────────────────

@labour_bp.route('/estates', methods=['POST'])
@token_required
@write_required
def create_estate():
    """POST /api/labour/estates — create a new estate."""
    data = request.get_json() or {}
    required = ('name', 'region')
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing: {", ".join(missing)}'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO estate (name, region, total_blocks)
                VALUES (%s, %s, 0)
                RETURNING id, name, region
            """, (data['name'], data['region']))
            row = cur.fetchone()
            conn.commit()
        return jsonify({'id': str(row[0]), 'name': row[1], 'region': row[2], 'message': 'Estate created'}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/estates/<estate_id>', methods=['PUT'])
@token_required
@write_required
def update_estate(estate_id):
    """PUT /api/labour/estates/<id> — update estate details."""
    data = request.get_json() or {}
    allowed = {'name', 'region'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': 'No valid fields'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sets = ', '.join(f"{k} = %s" for k in updates)
            params = list(updates.values()) + [estate_id]
            cur.execute(f"UPDATE estate SET {sets} WHERE id = %s", params)
            if cur.rowcount == 0:
                return jsonify({'error': 'Estate not found'}), 404
            conn.commit()
        return jsonify({'message': 'Estate updated'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/estates/<estate_id>', methods=['DELETE'])
@token_required
@write_required
def delete_estate(estate_id):
    """DELETE /api/labour/estates/<id> — delete an estate."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM estate WHERE id = %s", (estate_id,))
            if cur.rowcount == 0:
                return jsonify({'error': 'Estate not found'}), 404
            conn.commit()
        return jsonify({'message': 'Estate deleted'}), 200
    except Exception as e:
        conn.rollback()
        logger.error("Delete estate error: %s", str(e), exc_info=True)
        return _db_err(e)
    finally:
        conn.close()


# ── Manual Labour Plan & Assignment (Fallback) ───────────────────────────

@labour_bp.route('/plans/manual/create', methods=['POST'])
@token_required
@write_required
def create_manual_plan():
    """POST /api/labour/plans/manual/create — create plan without rotation (fallback).
    
    Body: {
      estate_id, period_start, 
      assignments: [{block_id, worker_group_id, expected_yield_kg?}, ...],
      total_workers?, target_kg?, status?, notes?
    }
    
    Use when automated cron fails or needs manual override.
    """
    data = request.get_json() or {}
    estate_id = data.get('estate_id')
    period_raw = data.get('period_start')
    assignments_data = data.get('assignments', [])
    user_id = request.user.get('user_id')

    if not estate_id or not period_raw:
        return jsonify({'error': 'estate_id and period_start required'}), 400
    if not assignments_data:
        return jsonify({'error': 'assignments array required (empty list allowed)'}), 400

    period_start = _first_of_month(period_raw)
    
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            # Check plan doesn't already exist
            cur.execute(
                "SELECT id FROM labour_plan WHERE estate_id = %s AND period_start = %s",
                (estate_id, period_start)
            )
            if cur.fetchone():
                return jsonify({'error': 'Plan already exists for this period'}), 409

            # Create plan
            total_workers = data.get('total_workers', 0)
            target_kg = data.get('target_kg', 0)
            status = data.get('status', 'draft')
            notes = data.get('notes') or f'Manual plan created by {user_id}'
            
            cur.execute("""
                INSERT INTO labour_plan (estate_id, created_by, period_start, 
                                        total_workers, target_kg, status, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (estate_id, user_id, period_start, total_workers, target_kg, status, notes))
            
            plan_id = str(cur.fetchone()[0])

            # Create assignments
            created_count = 0
            for assign in assignments_data:
                block_id = assign.get('block_id')
                group_id = assign.get('worker_group_id')
                expected_yield = assign.get('expected_yield_kg', 0)
                
                if not block_id or not group_id:
                    continue
                    
                cur.execute("""
                    INSERT INTO block_assignment 
                    (labour_plan_id, block_id, worker_group_id, expected_yield_kg, 
                     is_manual_override, override_reason, status)
                    VALUES (%s, %s, %s, %s, TRUE, %s, 'open')
                """, (plan_id, block_id, group_id, expected_yield, 
                      'Manual assignment (cron fallback)'))
                created_count += 1

            conn.commit()
        return jsonify({
            'plan_id': plan_id,
            'period_start': period_start.isoformat(),
            'assignments_created': created_count,
            'message': 'Manual plan created successfully'
        }), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/plans/<plan_id>/assignments/add', methods=['POST'])
@token_required
@write_required
def add_assignment_to_plan(plan_id):
    """POST /api/labour/plans/<id>/assignments/add — add group assignment to existing plan.
    
    Body: { block_id, worker_group_id, expected_yield_kg? }
    
    Use to add missing assignments after plan creation.
    """
    data = request.get_json() or {}
    block_id = data.get('block_id')
    group_id = data.get('worker_group_id')
    expected_yield = data.get('expected_yield_kg', 0)
    
    if not block_id or not group_id:
        return jsonify({'error': 'block_id and worker_group_id required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            # Verify plan exists
            cur.execute("SELECT id FROM labour_plan WHERE id = %s", (plan_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Plan not found'}), 404

            # Add assignment
            cur.execute("""
                INSERT INTO block_assignment 
                (labour_plan_id, block_id, worker_group_id, expected_yield_kg, 
                 is_manual_override, override_reason, status)
                VALUES (%s, %s, %s, %s, TRUE, %s, 'open')
                ON CONFLICT (labour_plan_id, block_id, worker_group_id) 
                DO UPDATE SET expected_yield_kg = %s
            """, (plan_id, block_id, group_id, expected_yield,
                  'Manual assignment (cron fallback)', expected_yield))
            
            conn.commit()
        return jsonify({'message': 'Assignment added', 'block_id': block_id}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()
