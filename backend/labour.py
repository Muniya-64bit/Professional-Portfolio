"""Labour planner API — routes and DB helpers."""
import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from flask import Blueprint, jsonify, request
from auth import token_required, get_db_connection

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


# ── Labour Plans ──────────────────────────────────────────────────────────────

@labour_bp.route('/plans', methods=['GET'])
@token_required
def list_plans():
    """GET /api/labour/plans  ?estate_id=  &week_start="""
    estate_id  = request.args.get('estate_id')
    week_start = request.args.get('week_start')
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT lp.id, lp.week_start, lp.total_workers, lp.target_kg,
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
            if week_start:
                where.append("lp.week_start = %s"); params.append(week_start)
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += (" GROUP BY lp.id, e.name, e.id, "
                    "rc.cycle_name, rc.current_round, rc.total_rounds "
                    "ORDER BY lp.week_start DESC")
            cur.execute(sql, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/plans', methods=['POST'])
@token_required
def create_plan():
    """POST /api/labour/plans — create plan + auto-generate assignments from rotation."""
    data = request.get_json() or {}
    estate_id     = data.get('estate_id')
    week_start    = data.get('week_start')
    total_workers = data.get('total_workers')
    target_kg     = data.get('target_kg')
    notes         = data.get('notes', '')
    user_id       = request.user.get('user_id')

    if not estate_id or not week_start or not total_workers:
        return jsonify({'error': 'estate_id, week_start, and total_workers are required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO labour_plan
                    (estate_id, created_by, week_start, total_workers, target_kg, status, notes)
                VALUES (%s, %s, %s, %s, %s, 'draft', %s)
                RETURNING id
            """, (estate_id, user_id, week_start, total_workers, target_kg, notes))
            plan_id = str(cur.fetchone()[0])

            # Auto-generate block_assignment rows from active rotation round
            cur.execute("""
                INSERT INTO block_assignment (
                    labour_plan_id, block_id, worker_group_id,
                    assignment_date, rotation_cycle_id, rotation_round,
                    expected_yield_kg, status
                )
                SELECT
                    %s,
                    rrb.block_id,
                    rrb.worker_group_id,
                    %s::DATE,
                    rc.id,
                    rc.current_round,
                    b.worker_capacity * 600.0,
                    'scheduled'
                FROM rotation_cycle rc
                JOIN rotation_round_block rrb
                     ON rrb.rotation_cycle_id = rc.id
                     AND rrb.round_number = rc.current_round
                JOIN block b ON b.id = rrb.block_id
                WHERE rc.estate_id = %s AND rc.is_active = TRUE
                ON CONFLICT (block_id, assignment_date) DO NOTHING
            """, (plan_id, week_start, estate_id))

            conn.commit()
        return jsonify({'id': plan_id, 'message': 'Labour plan created'}), 201
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
                SELECT lp.id, lp.week_start, lp.total_workers, lp.target_kg,
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

            cur.execute("""
                SELECT ba.id, b.block_code, b.worker_capacity,
                       wg.group_name, wg.group_code, wg.capacity AS group_capacity,
                       ba.assignment_date, ba.rotation_round, ba.is_manual_override,
                       ba.expected_yield_kg, ba.actual_yield_kg,
                       ba.plucking_round_number, ba.status, ba.notes,
                       og.group_name AS original_group_name,
                       ba.override_reason
                FROM block_assignment ba
                JOIN block b ON b.id = ba.block_id
                LEFT JOIN worker_group wg ON wg.id = ba.worker_group_id
                LEFT JOIN worker_group og ON og.id = ba.original_group_id
                WHERE ba.labour_plan_id = %s
                ORDER BY b.block_code
            """, (plan_id,))
            plan['assignments'] = _rows(cur)
        return jsonify(plan), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/plans/<plan_id>', methods=['PUT'])
@token_required
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


# ── Block Assignments ─────────────────────────────────────────────────────────

@labour_bp.route('/assignments/<assignment_id>', methods=['PUT'])
@token_required
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
    estate_id  = request.args.get('estate_id')
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
                data['estate_id'], data['employee_code'], data['full_name'],
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
                    SET is_active = FALSE, left_date = CURRENT_DATE, updated_at = NOW()
                    WHERE employee_id = %s AND is_active = TRUE
                """, (emp_id,))
                cur.execute("""
                    INSERT INTO worker_group_member (group_id, employee_id, joined_date, is_active)
                    VALUES (%s, %s, %s, TRUE)
                """, (group_id, emp_id, data['hire_date']))

            conn.commit()
        return jsonify({'id': emp_id, 'message': 'Employee created'}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/employees/<employee_id>', methods=['PUT'])
@token_required
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
            conn.commit()
        return jsonify({'message': 'Employee updated'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Worker Groups ─────────────────────────────────────────────────────────────

@labour_bp.route('/groups', methods=['GET'])
@token_required
def list_groups():
    """GET /api/labour/groups  ?estate_id="""
    estate_id = request.args.get('estate_id')
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
    estate_id = request.args.get('estate_id')
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


# ── Estates (needed for estate selector in frontend) ──────────────────────────

@labour_bp.route('/estates', methods=['GET'])
@token_required
def list_estates():
    """GET /api/labour/estates — all estates with block count."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.id, e.name, e.region, e.total_blocks,
                       COUNT(b.id) AS block_count
                FROM estate e
                LEFT JOIN block b ON b.estate_id = e.id
                GROUP BY e.id, e.name, e.region, e.total_blocks
                ORDER BY e.name
            """)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()
