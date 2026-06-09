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

def _proportional_workers(block_ids, predictions, total_employees,
                          supervisor_per_block=None):
    """Distribute total_employees across blocks proportional to yield predictions.

    supervisor_per_block: {block_id_str: int} — supervisors anchored to that
    block's primary group.  They are NOT redistributed; only the remaining
    (non-supervisor + ungrouped) workers are spread proportionally.

    Uses the largest-remainder method so every result is a non-negative integer
    and values sum exactly to total_employees (no worker is left unallocated).
    Blocks with zero or missing predictions receive an equal share of the
    movable pool.
    """
    if not block_ids:
        return {}

    if supervisor_per_block is None:
        supervisor_per_block = {}

    block_strs = [str(b) for b in block_ids]
    n = len(block_strs)

    # Supervisors are fixed to their block — remove them from the movable pool
    fixed  = {bid: supervisor_per_block.get(bid, 0) for bid in block_strs}
    movable = max(0, total_employees - sum(fixed.values()))

    yields = {bid: max(predictions.get(bid, 0) or 0, 0) for bid in block_strs}
    total_yield = sum(yields.values())

    if movable == 0:
        return {bid: fixed[bid] for bid in block_strs}

    if total_yield == 0:
        # No predictions — distribute movable pool equally
        base, extra = divmod(movable, n)
        prop = {bid: base + (1 if i < extra else 0) for i, bid in enumerate(block_strs)}
    else:
        raw     = {bid: movable * (yields[bid] / total_yield) for bid in block_strs}
        prop    = {bid: int(s) for bid, s in raw.items()}
        deficit = movable - sum(prop.values())
        by_rem  = sorted(block_strs, key=lambda bid: raw[bid] - prop[bid], reverse=True)
        for i in range(int(deficit)):
            prop[by_rem[i % n]] += 1

    return {bid: fixed[bid] + prop[bid] for bid in block_strs}


def _snapshot_assignment_members(cur, plan_id):
    """Record which specific employees fill each block for this plan's month.

    Reconciles the per-block headcount (block_assignment.allocated_workers) with
    named individuals under the flexible-pool model:
      * Supervisors stay anchored to their group's block this month.
      * Every other active employee forms a pool, distributed across blocks in a
        deterministic order to fill each block's remaining headcount exactly.

    Result: COUNT(block_assignment_member) per block == allocated_workers, and
    each employee appears on exactly one block for the month.  Idempotent — it
    clears any existing snapshot for the plan first.  Returns rows inserted.
    """
    cur.execute("SELECT estate_id FROM labour_plan WHERE id = %s", (plan_id,))
    row = cur.fetchone()
    if not row:
        return 0
    estate_id = row[0]

    # Primary assignments carry the headcount (doubled-up coverage rows are 0)
    cur.execute(
        """SELECT id, block_id, worker_group_id, allocated_workers
           FROM block_assignment
           WHERE labour_plan_id = %s AND allocated_workers > 0
           ORDER BY block_id""",
        (plan_id,),
    )
    primaries = cur.fetchall()
    if not primaries:
        return 0

    group_ids = [r[2] for r in primaries if r[2] is not None]

    # Supervisors anchored to each block via the group covering it this month
    sups_by_group, anchored_sup_ids = {}, set()
    if group_ids:
        cur.execute(
            """SELECT wgm.group_id, e.id, e.skill_type
               FROM worker_group_member wgm
               JOIN employee e ON e.id = wgm.employee_id
               WHERE wgm.is_active = TRUE AND e.is_active = TRUE
                 AND e.skill_type = 'supervisor'
                 AND wgm.group_id = ANY(%s)""",
            (group_ids,),
        )
        for gid, eid, skill in cur.fetchall():
            sups_by_group.setdefault(gid, []).append((eid, skill))
            anchored_sup_ids.add(eid)

    # Pool = every other active employee, deterministic order
    cur.execute(
        """SELECT id, skill_type FROM employee
           WHERE estate_id = %s AND is_active = TRUE
           ORDER BY employee_code, id""",
        (estate_id,),
    )
    pool = [(eid, skill) for (eid, skill) in cur.fetchall()
            if eid not in anchored_sup_ids]

    # Fresh snapshot for this plan
    cur.execute("DELETE FROM block_assignment_member WHERE labour_plan_id = %s",
                (plan_id,))

    inserted, idx = 0, 0
    for ba_id, block_id, group_id, alloc in primaries:
        members = list(sups_by_group.get(group_id, []))      # anchored supervisors
        need = max(0, (alloc or 0) - len(members))
        members += pool[idx:idx + need]
        idx += need
        for eid, skill in members:
            cur.execute(
                """INSERT INTO block_assignment_member
                       (block_assignment_id, labour_plan_id, employee_id, skill_type)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (labour_plan_id, employee_id) DO NOTHING""",
                (ba_id, plan_id, eid, skill),
            )
            inserted += 1
    return inserted


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

    # All active group IDs (for full-coverage pass)
    cur.execute(
        "SELECT id FROM worker_group WHERE estate_id = %s AND is_active = TRUE",
        (estate_id,),
    )
    all_group_ids = {str(row[0]) for row in cur.fetchall()}

    # 5. Total active employees in this estate — grouped AND ungrouped.
    #    Every one of them must be accounted for in this plan.
    cur.execute(
        "SELECT COUNT(*) FROM employee WHERE estate_id = %s AND is_active = TRUE",
        (estate_id,),
    )
    total_employees = cur.fetchone()[0] or 1

    # assignment tuples: (block_id, group_id, expected_yield, note, is_primary)
    # is_primary=True  → rotation-assigned group; carries the block's worker quota
    # is_primary=False → doubled-up group for full coverage; allocated_workers = 0
    assignments = []
    assigned_groups = set()
    round_block_ids = []

    for block_id, group_id in round_rows:
        assignments.append((block_id, group_id,
                            predictions.get(str(block_id)), None, True))
        assigned_groups.add(str(group_id))
        round_block_ids.append(block_id)

    # 6. Full-coverage pass — leftover groups double up on the highest-predicted block.
    target_block = None
    if round_block_ids:
        target_block = max(round_block_ids,
                           key=lambda b: predictions.get(str(b), 0) or 0)
    leftover = [g for g in all_group_ids if g not in assigned_groups]
    for group_id in leftover:
        if target_block is None:
            break
        assignments.append((target_block, group_id, None,
                            'auto-assigned for full coverage', False))
        assigned_groups.add(group_id)

    # 7a. Supervisor anchoring — supervisors stay with their primary group's block.
    #     Query how many active supervisors belong to each primary-assignment group.
    supervisor_per_block = {}
    if round_rows:
        cur.execute(
            """SELECT rrb.block_id, COUNT(e.id)
               FROM rotation_round_block rrb
               JOIN worker_group_member wgm
                   ON wgm.group_id = rrb.worker_group_id AND wgm.is_active = TRUE
               JOIN employee e
                   ON e.id = wgm.employee_id
                  AND e.skill_type = 'supervisor'
                  AND e.is_active  = TRUE
               WHERE rrb.rotation_cycle_id = %s AND rrb.round_number = %s
               GROUP BY rrb.block_id""",
            (cycle_id, current_round),
        )
        supervisor_per_block = {str(row[0]): row[1] for row in cur.fetchall()}

    # 7b. Yield-proportional distribution of the non-supervisor pool.
    #     Supervisors are anchored; everyone else is distributed proportionally.
    #     All total_employees end up allocated — no one is left behind.
    block_worker_alloc = _proportional_workers(
        round_block_ids, predictions, total_employees,
        supervisor_per_block=supervisor_per_block,
    )

    # Count ungrouped employees (informational — included in total_employees
    # and therefore covered by the proportional allocation above).
    cur.execute(
        """SELECT COUNT(*) FROM employee e
           WHERE e.estate_id = %s AND e.is_active = TRUE
             AND NOT EXISTS (
                 SELECT 1 FROM worker_group_member m
                 WHERE m.employee_id = e.id AND m.is_active = TRUE)""",
        (estate_id,),
    )
    ungrouped = cur.fetchone()[0]

    # 8. Plan totals
    target_kg = round(sum((predictions.get(str(b)) or 0) for b in round_block_ids), 3)

    cur.execute(
        """INSERT INTO labour_plan
               (estate_id, created_by, period_start, total_workers, target_kg, status, notes)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (estate_id, created_by, period_start, total_employees, target_kg, status,
         notes or f'Auto-generated monthly plan — round {current_round}'),
    )
    plan_id = cur.fetchone()[0]

    # 9. Block assignments — primary rows carry the yield-proportional headcount;
    #    doubled-up rows carry 0 (they provide group coverage, not extra workers).
    for block_id, group_id, expected, note, is_primary in assignments:
        alloc = block_worker_alloc.get(str(block_id), 0) if is_primary else 0
        cur.execute(
            """INSERT INTO block_assignment
                   (labour_plan_id, block_id, worker_group_id, assignment_date,
                    rotation_cycle_id, rotation_round, expected_yield_kg,
                    allocated_workers, status, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'scheduled', %s)
               ON CONFLICT (block_id, assignment_date, worker_group_id) DO NOTHING""",
            (plan_id, block_id, group_id, period_start,
             cycle_id, current_round, expected, alloc, note),
        )

    # 9b. Snapshot the individual employees behind each block's headcount, so
    #     "who was in this group this month" stays queryable forever.
    members_snapshot = _snapshot_assignment_members(cur, plan_id)

    # 10. Link this month's predictions to the plan
    cur.execute(
        """UPDATE yield_prediction SET labour_plan_id = %s
           WHERE year = %s AND month = %s
             AND block_id IN (SELECT id FROM block WHERE estate_id = %s)""",
        (plan_id, year, month, estate_id),
    )

    # 11. Advance the rotation round for next month (wraps at total_rounds)
    cur.execute(
        """UPDATE rotation_cycle
           SET current_round = (current_round %% total_rounds) + 1, updated_at = NOW()
           WHERE id = %s""",
        (cycle_id,),
    )

    return {
        'estate_id':            str(estate_id),
        'created':              True,
        'plan_id':              str(plan_id),
        'period_start':         period_start.isoformat(),
        'rotation_round':       current_round,
        'predicted_total_kg':   target_kg,
        'total_workers':        total_employees,
        'groups_covered':       len(assigned_groups),
        'groups_doubled_up':    len(leftover),
        'ungrouped_employees':  ungrouped,
        'worker_distribution':  {str(k): v for k, v in block_worker_alloc.items()},
        'supervisors_anchored': {str(k): v for k, v in supervisor_per_block.items()},
        'members_snapshotted':  members_snapshot,
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
                SELECT ba.id, ba.block_id, b.block_code, b.worker_capacity,
                       wg.id AS worker_group_id,
                       wg.group_name, wg.group_code, wg.capacity AS group_capacity,
                       ba.allocated_workers,
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


@labour_bp.route('/plans/<plan_id>/members', methods=['GET'])
@token_required
def get_plan_members(plan_id):
    """GET /api/labour/plans/<plan_id>/members  ?group_code=  &block_code=

    Returns the snapshot of which specific employees worked each block/group for
    this plan's month — the answer to "who was in group X that month".
    """
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT b.block_code, wg.group_code, wg.group_name,
                       e.id AS employee_id, e.employee_code, e.full_name,
                       bam.skill_type, ba.rotation_round
                FROM block_assignment_member bam
                JOIN block_assignment ba ON ba.id = bam.block_assignment_id
                JOIN block b             ON b.id  = ba.block_id
                LEFT JOIN worker_group wg ON wg.id = ba.worker_group_id
                JOIN employee e          ON e.id  = bam.employee_id
                WHERE bam.labour_plan_id = %s
            """
            params = [plan_id]
            if request.args.get('group_code'):
                sql += " AND wg.group_code = %s"; params.append(request.args['group_code'])
            if request.args.get('block_code'):
                sql += " AND b.block_code = %s"; params.append(request.args['block_code'])
            sql += " ORDER BY b.block_code, e.skill_type DESC, e.employee_code"
            cur.execute(sql, params)
            rows = _rows(cur)

        # Group the flat rows by block/group for convenient consumption
        groups = {}
        for r in rows:
            key = r['block_code']
            g = groups.setdefault(key, {
                'block_code': r['block_code'],
                'group_code': r['group_code'],
                'group_name': r['group_name'],
                'rotation_round': r['rotation_round'],
                'members': [],
            })
            g['members'].append({
                'employee_id':   r['employee_id'],
                'employee_code': r['employee_code'],
                'full_name':     r['full_name'],
                'skill_type':    r['skill_type'],
            })
        return jsonify({
            'plan_id': plan_id,
            'total_members': len(rows),
            'blocks': list(groups.values()),
        }), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/rotation/members', methods=['GET'])
@token_required
def get_rotation_members():
    """GET /api/labour/rotation/members  ?estate_id=&round=&group_code=

    Returns the people assigned to a group for a given rotation round (= month).
    Used by the rotation view: click a group cell → see who was assigned.
    """
    estate_id, err = effective_estate_id(request.args.get('estate_id'))
    if err:
        return err
    round_no   = request.args.get('round')
    group_code = request.args.get('group_code')
    if not round_no:
        return jsonify({'error': 'round is required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT e.id AS employee_id, e.employee_code, e.full_name,
                       bam.skill_type, b.block_code, wg.group_code, wg.group_name,
                       lp.period_start
                FROM block_assignment_member bam
                JOIN block_assignment ba ON ba.id = bam.block_assignment_id
                JOIN labour_plan lp      ON lp.id = bam.labour_plan_id
                JOIN block b             ON b.id  = ba.block_id
                LEFT JOIN worker_group wg ON wg.id = ba.worker_group_id
                JOIN employee e          ON e.id  = bam.employee_id
                WHERE lp.estate_id = %s AND ba.rotation_round = %s
            """
            params = [estate_id, int(round_no)]
            if group_code:
                sql += " AND wg.group_code = %s"; params.append(group_code)
            sql += " ORDER BY (e.skill_type = 'supervisor') DESC, e.employee_code"
            cur.execute(sql, params)
            rows = _rows(cur)
        return jsonify({
            'round': int(round_no),
            'group_code': group_code,
            'period_start': rows[0]['period_start'] if rows else None,
            'block_code': rows[0]['block_code'] if rows else None,
            'count': len(rows),
            'members': rows,
        }), 200
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
                      AND rrb.round_number IN (
                          SELECT DISTINCT rotation_round
                          FROM block_assignment
                          WHERE rotation_cycle_id = %s
                            AND rotation_round IS NOT NULL
                      )
                    ORDER BY rrb.round_number, b.block_code
                """, (cycle['id'], cycle['id']))
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
                cycle['rounds_executed'] = len(matrix)
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
    if assignments_data is None:
        return jsonify({'error': 'assignments must be a list'}), 400

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

            # Create assignments (group_id may be None for unassigned blocks)
            created_count = 0
            block_ids, predictions, group_by_block = [], {}, {}
            for assign in assignments_data:
                block_id = assign.get('block_id')
                group_id = assign.get('worker_group_id') or None
                expected_yield = assign.get('expected_yield_kg') or 0

                if not block_id:
                    continue

                cur.execute("""
                    INSERT INTO block_assignment
                    (labour_plan_id, block_id, worker_group_id, expected_yield_kg,
                     is_manual_override, override_reason, status, assignment_date)
                    VALUES (%s, %s, %s, %s, TRUE, %s, 'scheduled', CURRENT_DATE)
                """, (plan_id, block_id, group_id, expected_yield,
                      'Manual plan creation'))
                created_count += 1
                block_ids.append(block_id)
                predictions[str(block_id)] = expected_yield
                group_by_block[str(block_id)] = group_id

            # Allocate workers yield-proportionally and snapshot who they are, so a
            # manually-created plan records its group membership like the cron does.
            members_snapshot = 0
            if block_ids:
                if not total_workers:
                    cur.execute("SELECT COUNT(*) FROM employee "
                                "WHERE estate_id = %s AND is_active = TRUE", (estate_id,))
                    total_workers = cur.fetchone()[0] or 0

                # Supervisors anchored per block via the assigned group
                supervisor_per_block = {}
                group_ids = list({g for g in group_by_block.values() if g})
                if group_ids:
                    cur.execute(
                        """SELECT wgm.group_id, COUNT(*)
                           FROM worker_group_member wgm
                           JOIN employee e ON e.id = wgm.employee_id
                           WHERE wgm.is_active = TRUE AND e.is_active = TRUE
                             AND e.skill_type = 'supervisor'
                             AND wgm.group_id = ANY(%s)
                           GROUP BY wgm.group_id""",
                        (group_ids,),
                    )
                    sup_by_group = {str(r[0]): r[1] for r in cur.fetchall()}
                    for bid_str, gid in group_by_block.items():
                        if gid:
                            supervisor_per_block[bid_str] = sup_by_group.get(str(gid), 0)

                alloc = _proportional_workers(
                    block_ids, predictions, total_workers,
                    supervisor_per_block=supervisor_per_block)
                for bid, n in alloc.items():
                    cur.execute(
                        "UPDATE block_assignment SET allocated_workers = %s "
                        "WHERE labour_plan_id = %s AND block_id = %s",
                        (n, plan_id, bid))

                cur.execute("UPDATE labour_plan SET total_workers = %s WHERE id = %s",
                            (total_workers, plan_id))
                members_snapshot = _snapshot_assignment_members(cur, plan_id)

            conn.commit()
        return jsonify({
            'plan_id': plan_id,
            'period_start': period_start.isoformat(),
            'assignments_created': created_count,
            'members_snapshotted': members_snapshot,
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
    group_id = data.get('worker_group_id') or None
    expected_yield = data.get('expected_yield_kg') or 0

    if not block_id:
        return jsonify({'error': 'block_id required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            # Verify plan exists
            cur.execute("SELECT id FROM labour_plan WHERE id = %s", (plan_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Plan not found'}), 404

            # Check block not already in plan
            cur.execute(
                "SELECT id FROM block_assignment WHERE labour_plan_id = %s AND block_id = %s",
                (plan_id, block_id)
            )
            if cur.fetchone():
                return jsonify({'error': 'Block already in this plan'}), 409

            # Add assignment
            cur.execute("""
                INSERT INTO block_assignment
                (labour_plan_id, block_id, worker_group_id, expected_yield_kg,
                 is_manual_override, override_reason, status, assignment_date)
                VALUES (%s, %s, %s, %s, TRUE, %s, 'scheduled', CURRENT_DATE)
            """, (plan_id, block_id, group_id, expected_yield,
                  'Manual assignment'))
            
            conn.commit()
        return jsonify({'message': 'Assignment added', 'block_id': block_id}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Block Assignment Management (Change Groups) ────────────────────────

@labour_bp.route('/assignments/<assignment_id>/change-group', methods=['PUT'])
@token_required
@write_required
def change_group_assignment(assignment_id):
    """PUT /api/labour/assignments/<id>/change-group — change group assigned to block.
    
    Body: { worker_group_id }
    
    Allows swapping which group is assigned to a block.
    """
    data = request.get_json() or {}
    new_group_id = data.get('worker_group_id')
    
    if not new_group_id:
        return jsonify({'error': 'worker_group_id required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            # Get current assignment
            cur.execute("""
                SELECT labour_plan_id, block_id, worker_group_id 
                FROM block_assignment WHERE id = %s
            """, (assignment_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Assignment not found'}), 404
            
            plan_id, block_id, old_group_id = row
            
            # Change the group
            cur.execute("""
                UPDATE block_assignment 
                SET worker_group_id = %s, 
                    is_manual_override = TRUE,
                    override_reason = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (new_group_id, f'Group changed from {old_group_id}', assignment_id))
            
            conn.commit()
        return jsonify({
            'message': 'Group assignment changed',
            'assignment_id': assignment_id,
            'new_group_id': new_group_id
        }), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/assignments/<assignment_id>/remove', methods=['DELETE'])
@token_required
@write_required
def remove_assignment(assignment_id):
    """DELETE /api/labour/assignments/<id>/remove — remove block assignment.
    
    Unassigns a group from a block.
    """
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM block_assignment WHERE id = %s", (assignment_id,))
            if cur.rowcount == 0:
                return jsonify({'error': 'Assignment not found'}), 404
            conn.commit()
        return jsonify({'message': 'Assignment removed'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@labour_bp.route('/assignments/<assignment_id>/remove-group', methods=['PUT'])
@token_required
@write_required
def remove_group_from_assignment(assignment_id):
    """PUT /api/labour/assignments/<id>/remove-group — remove group but keep assignment.
    
    Unassigns group from block (sets worker_group_id to NULL).
    Block stays in plan, just unassigned until new group is added.
    """
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE block_assignment 
                SET worker_group_id = NULL, 
                    is_manual_override = TRUE,
                    override_reason = 'Group removed - awaiting reassignment',
                    updated_at = NOW()
                WHERE id = %s
            """, (assignment_id,))
            if cur.rowcount == 0:
                return jsonify({'error': 'Assignment not found'}), 404
            conn.commit()
        return jsonify({'message': 'Group removed from block'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()
