"""Fertilizer Rotation Planner — schedule engine + CRUD API."""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from flask import Blueprint, jsonify, request
from auth import (token_required, write_required, get_db_connection,
                  is_full_access, effective_estate_id)

logger = logging.getLogger(__name__)
fertilizer_bp = Blueprint('fertilizer', __name__, url_prefix='/api/fertilizer')


# ── Shared helpers ────────────────────────────────────────────────────────────

def _to_json(v):
    if isinstance(v, UUID):             return str(v)
    if isinstance(v, Decimal):          return float(v)
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
    return get_db_connection()


# ── Scheduling engine ─────────────────────────────────────────────────────────

def _first_of_month(d):
    """Normalise any date to the 1st of its month."""
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return d.replace(day=1)


def _generate_entries_for_schedule(cur, schedule_id, estate_id, period_start, today=None):
    """Generate fertilizer_schedule_entry rows for a monthly schedule run.

    Guard conditions (all three must pass for an entry to be inserted):
      1. Block area guard   — skip blocks with NULL / 0 area_hectares.
      2. Idempotency guard  — skip if an entry already exists for
                              (schedule_id, block_id, programme_id).
      3. Over-fertilization guard — skip if the last actual application of that
                              fertilizer on that block falls within the current
                              interval (applied too recently).

    Returns a counters dict: inserted / skipped_existing / skipped_area / skipped_recent.
    """
    if today is None:
        today = date.today()

    counters = dict(inserted=0, skipped_existing=0, skipped_area=0, skipped_recent=0)

    cur.execute("""
        SELECT b.id, b.area_hectares, b.growth_stage, b.zone
        FROM   block b
        WHERE  b.estate_id = %s
    """, (estate_id,))
    blocks = cur.fetchall()

    for block_id, area_ha, growth_stage, zone in blocks:
        # Guard 1: block must have a positive area
        if not area_ha or float(area_ha) <= 0:
            counters['skipped_area'] += 1
            continue

        # Programme steps that apply to this block's zone + growth stage
        cur.execute("""
            SELECT fp.id, fp.fertilizer_type_id, fp.application_no,
                   fp.interval_weeks, fp.rate_kg_per_ha
            FROM   fertilizer_programme fp
            WHERE  fp.estate_id   = %s
              AND  fp.is_active   = true
              AND  (fp.zone_override       IS NULL OR fp.zone_override       = %s)
              AND  (fp.growth_stage_filter IS NULL OR fp.growth_stage_filter = %s)
            ORDER  BY fp.fertilizer_type_id, fp.application_no
        """, (estate_id, zone, growth_stage))
        steps = cur.fetchall()

        for prog_id, fert_type_id, _app_no, interval_weeks, rate_kg_per_ha in steps:
            # Guard 2: idempotency — one entry per (schedule, block, programme step)
            cur.execute("""
                SELECT id FROM fertilizer_schedule_entry
                WHERE  schedule_id  = %s
                  AND  block_id     = %s
                  AND  programme_id = %s
            """, (schedule_id, block_id, prog_id))
            if cur.fetchone():
                counters['skipped_existing'] += 1
                continue

            # Find the last actual application of this fertilizer on this block
            cur.execute("""
                SELECT MAX(application_date)
                FROM   fertilizer_application
                WHERE  block_id           = %s
                  AND  fertilizer_type_id = %s
            """, (block_id, fert_type_id))
            last_date = (cur.fetchone() or [None])[0]

            if last_date is None:
                due_date = period_start
            else:
                due_date = last_date + timedelta(weeks=interval_weeks)
                # Guard 3: applied within the current interval → too soon
                if last_date >= (today - timedelta(weeks=interval_weeks)):
                    counters['skipped_recent'] += 1
                    continue

            # Derive initial status
            if due_date < today:
                status = 'overdue'
            elif due_date == today:
                status = 'due'
            else:
                status = 'pending'

            cur.execute("""
                INSERT INTO fertilizer_schedule_entry
                    (schedule_id, block_id, programme_id, due_date, status, scheduled_rate_kg_per_ha)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (schedule_id, block_id, programme_id) DO NOTHING
            """, (schedule_id, block_id, prog_id, due_date, status, rate_kg_per_ha))
            if cur.rowcount:
                counters['inserted'] += 1
            else:
                counters['skipped_existing'] += 1

    return counters


# ── Programme endpoints ───────────────────────────────────────────────────────

@fertilizer_bp.route('/programme', methods=['GET'])
@token_required
def get_programme():
    """List active fertilizer programme steps for an estate."""
    estate_id = request.args.get('estate_id')
    estate_id, err = effective_estate_id(estate_id)
    if err:
        return err

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            params = []
            where = "fp.is_active = true"
            if estate_id:
                where += " AND fp.estate_id = %s"
                params.append(estate_id)
            cur.execute(f"""
                SELECT fp.id, fp.estate_id, e.name AS estate_name,
                       fp.fertilizer_type_id, ft.code AS fertilizer_code,
                       ft.name AS fertilizer_name, ft.npk_n, ft.npk_p, ft.npk_k,
                       fp.application_no, fp.interval_weeks, fp.rate_kg_per_ha,
                       fp.zone_override, fp.growth_stage_filter, fp.notes,
                       fp.is_active, fp.created_at
                FROM   fertilizer_programme fp
                JOIN   estate         e  ON e.id  = fp.estate_id
                JOIN   fertilizer_type ft ON ft.id = fp.fertilizer_type_id
                WHERE  {where}
                ORDER  BY e.name, ft.code, fp.application_no
            """, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@fertilizer_bp.route('/programme', methods=['POST'])
@token_required
@write_required
def create_programme_step():
    """Add a programme step. Body fields: estate_id, fertilizer_type_id,
    application_no, interval_weeks, rate_kg_per_ha, [zone_override],
    [growth_stage_filter], [notes]."""
    data = request.get_json() or {}
    required = ('estate_id', 'fertilizer_type_id', 'application_no',
                'interval_weeks', 'rate_kg_per_ha')
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400

    if float(data['rate_kg_per_ha']) <= 0:
        return jsonify({'error': 'rate_kg_per_ha must be positive'}), 400
    if int(data['interval_weeks']) <= 0:
        return jsonify({'error': 'interval_weeks must be positive'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO fertilizer_programme
                    (estate_id, fertilizer_type_id, application_no,
                     interval_weeks, rate_kg_per_ha,
                     zone_override, growth_stage_filter, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                data['estate_id'], data['fertilizer_type_id'],
                int(data['application_no']), int(data['interval_weeks']),
                float(data['rate_kg_per_ha']),
                data.get('zone_override'), data.get('growth_stage_filter'),
                data.get('notes'),
            ))
            new_id = str(cur.fetchone()[0])
        conn.commit()
        return jsonify({'id': new_id, 'message': 'Programme step created'}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@fertilizer_bp.route('/programme/<programme_id>', methods=['PUT'])
@token_required
@write_required
def update_programme_step(programme_id):
    """Edit a programme step's rate, interval, notes, or zone/stage filters.
    Only the fields supplied in the body are updated."""
    data = request.get_json() or {}
    allowed = ('interval_weeks', 'rate_kg_per_ha', 'zone_override',
               'growth_stage_filter', 'notes')
    updates = {k: data[k] for k in allowed if k in data}
    if not updates:
        return jsonify({'error': 'No updatable fields provided'}), 400

    if 'rate_kg_per_ha' in updates and float(updates['rate_kg_per_ha']) <= 0:
        return jsonify({'error': 'rate_kg_per_ha must be positive'}), 400
    if 'interval_weeks' in updates and int(updates['interval_weeks']) <= 0:
        return jsonify({'error': 'interval_weeks must be positive'}), 400

    set_clause = ', '.join(f"{col} = %s" for col in updates)
    params = list(updates.values()) + [programme_id]

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE fertilizer_programme
                SET    {set_clause}, updated_at = NOW()
                WHERE  id = %s
                RETURNING id
            """, params)
            if not cur.fetchone():
                return jsonify({'error': 'Programme step not found'}), 404
        conn.commit()
        return jsonify({'message': 'Programme step updated'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@fertilizer_bp.route('/programme/<programme_id>', methods=['DELETE'])
@token_required
@write_required
def delete_programme_step(programme_id):
    """Soft-delete a programme step (sets is_active=false)."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE fertilizer_programme
                SET    is_active = false, updated_at = NOW()
                WHERE  id = %s
                RETURNING id
            """, (programme_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Programme step not found'}), 404
        conn.commit()
        return jsonify({'message': 'Programme step deactivated'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Schedule generation ───────────────────────────────────────────────────────

def _run_generate_schedule(estate_id, period_start, user_id=None):
    """Create a monthly schedule header + entries. Returns (payload, http_status).

    Returns 409 if a schedule already exists for (estate_id, period_start).
    Called by the HTTP route and the APScheduler monthly job.
    """
    period_start = _first_of_month(period_start)
    conn = _db()
    if not conn:
        return {'error': 'Database unavailable'}, 503
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM estate WHERE id = %s", (estate_id,))
            if not cur.fetchone():
                return {'error': 'Estate not found'}, 404

            # Conflict check — one schedule per estate per month
            cur.execute("""
                SELECT id, status, generated_at
                FROM   fertilizer_schedule
                WHERE  estate_id    = %s
                  AND  period_start = %s
            """, (estate_id, period_start))
            existing = cur.fetchone()
            if existing:
                return {
                    'error': 'Schedule already exists for this estate and month',
                    'schedule_id': str(existing[0]),
                    'status': existing[1],
                    'generated_at': existing[2].isoformat() if existing[2] else None,
                }, 409

            # Close any previously active schedules for this estate
            cur.execute("""
                UPDATE fertilizer_schedule
                SET    status = 'closed', updated_at = NOW()
                WHERE  estate_id = %s AND status = 'active'
            """, (estate_id,))

            # Insert header
            cur.execute("""
                INSERT INTO fertilizer_schedule
                    (estate_id, period_start, status, generated_by, generated_at)
                VALUES (%s, %s, 'active', %s, NOW())
                RETURNING id
            """, (estate_id, period_start, user_id))
            schedule_id = cur.fetchone()[0]

            counters = _generate_entries_for_schedule(
                cur, schedule_id, estate_id, period_start
            )

        conn.commit()
        return {
            'message': 'Schedule generated',
            'schedule_id': str(schedule_id),
            'estate_id': str(estate_id),
            'period_start': period_start.isoformat(),
            **counters,
        }, 201
    except Exception as e:
        conn.rollback()
        logger.error("DB error in _run_generate_schedule: %s", e, exc_info=True)
        return {'error': 'Database error'}, 500
    finally:
        conn.close()


def refresh_schedule_statuses():
    """Update stale fertilizer_schedule_entry statuses.

    due_date < today  → overdue
    due_date = today  → due
    due_date > today  → pending

    Only touches rows not already done/skipped.
    Returns a dict with counts of rows updated.
    """
    conn = _db()
    if not conn:
        logger.error("refresh_schedule_statuses: DB unavailable")
        return {'error': 'Database unavailable'}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE fertilizer_schedule_entry
                SET    status = 'overdue', updated_at = NOW()
                WHERE  status NOT IN ('done', 'skipped')
                  AND  due_date < CURRENT_DATE
            """)
            overdue_updated = cur.rowcount

            cur.execute("""
                UPDATE fertilizer_schedule_entry
                SET    status = 'due', updated_at = NOW()
                WHERE  status NOT IN ('done', 'skipped')
                  AND  due_date = CURRENT_DATE
            """)
            due_updated = cur.rowcount

            cur.execute("""
                UPDATE fertilizer_schedule_entry
                SET    status = 'pending', updated_at = NOW()
                WHERE  status NOT IN ('done', 'skipped')
                  AND  due_date > CURRENT_DATE
            """)
            pending_updated = cur.rowcount

        conn.commit()
        logger.info(
            "refresh_schedule_statuses: %d → overdue, %d → due, %d → pending",
            overdue_updated, due_updated, pending_updated,
        )
        return {'overdue_updated': overdue_updated, 'due_updated': due_updated, 'pending_updated': pending_updated}
    except Exception:
        conn.rollback()
        logger.exception("refresh_schedule_statuses failed")
        return {'error': 'Database error'}
    finally:
        conn.close()


# ── Schedule header endpoints ─────────────────────────────────────────────────

@fertilizer_bp.route('/schedules', methods=['GET'])
@token_required
def list_schedules():
    """List fertilizer schedule headers for an estate, newest first.
    Query params: estate_id"""
    estate_id = request.args.get('estate_id')
    estate_id, err = effective_estate_id(estate_id)
    if err:
        return err

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            params = []
            where  = ""
            if estate_id:
                where = "WHERE fs.estate_id = %s"
                params.append(estate_id)
            cur.execute(f"""
                SELECT fs.id, fs.estate_id, e.name AS estate_name,
                       fs.period_start, fs.status,
                       fs.generated_by, u.full_name AS generated_by_name,
                       fs.generated_at, fs.notes, fs.created_at,
                       COUNT(fse.id)                                          AS entry_count,
                       COUNT(fse.id) FILTER (WHERE fse.status = 'overdue')   AS overdue_count,
                       COUNT(fse.id) FILTER (WHERE fse.status = 'due')       AS due_count,
                       COUNT(fse.id) FILTER (WHERE fse.status = 'pending')   AS pending_count,
                       COUNT(fse.id) FILTER (WHERE fse.status = 'done')      AS done_count
                FROM   fertilizer_schedule fs
                JOIN   estate e ON e.id = fs.estate_id
                LEFT JOIN "user" u ON u.id = fs.generated_by
                LEFT JOIN fertilizer_schedule_entry fse ON fse.schedule_id = fs.id
                {where}
                GROUP  BY fs.id, e.name, u.full_name
                ORDER  BY fs.period_start DESC
            """, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@fertilizer_bp.route('/schedules/generate', methods=['POST'])
@fertilizer_bp.route('/generate', methods=['POST'])          # legacy alias
@token_required
@write_required
def generate_schedule():
    """Generate a monthly fertilizer schedule for an estate.
    Body: { "estate_id": "<uuid>", "period_start": "YYYY-MM-DD" }
    Returns 409 if a schedule already exists for that estate + month.
    """
    data = request.get_json() or {}
    estate_id    = data.get('estate_id')
    period_start = data.get('period_start')
    if not estate_id:
        return jsonify({'error': 'estate_id is required'}), 400
    if not period_start:
        from datetime import date as _date
        period_start = _date.today().replace(day=1)
    user_id = getattr(request, 'user', {}).get('user_id')
    payload, status = _run_generate_schedule(estate_id, period_start, user_id)
    return jsonify(payload), status


@fertilizer_bp.route('/schedules/<schedule_id>', methods=['DELETE'])
@token_required
@write_required
def delete_schedule(schedule_id):
    """Delete a schedule header and all its entries (cascade)."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM fertilizer_schedule WHERE id = %s RETURNING id
            """, (schedule_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Schedule not found'}), 404
        conn.commit()
        return jsonify({'message': 'Schedule deleted'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Schedule entry endpoints ──────────────────────────────────────────────────

@fertilizer_bp.route('/schedules/<schedule_id>/entries', methods=['GET'])
@token_required
def get_schedule_entries(schedule_id):
    """List entries for a specific schedule run.
    Query params: block_id, status (comma-separated), limit (default 200)."""
    block_id = request.args.get('block_id')
    statuses = [s.strip() for s in (request.args.get('status') or '').split(',') if s.strip()]
    limit    = min(int(request.args.get('limit', 200)), 500)

    conditions = ["fse.schedule_id = %s"]
    params     = [schedule_id]

    if block_id:
        conditions.append("fse.block_id = %s")
        params.append(block_id)
    if statuses:
        conditions.append("fse.status = ANY(%s)")
        params.append(statuses)

    params.append(limit)

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT fse.id, fse.schedule_id, fse.block_id, b.block_code,
                       e.id AS estate_id, e.name AS estate_name,
                       fp.id AS programme_id,
                       ft.id AS fertilizer_type_id,
                       ft.code AS fertilizer_code, ft.name AS fertilizer_name,
                       ft.npk_n, ft.npk_p, ft.npk_k,
                       fse.due_date, fse.status,
                       fse.scheduled_rate_kg_per_ha,
                       ROUND(fse.scheduled_rate_kg_per_ha * b.area_hectares, 1) AS total_kg_needed,
                       fse.actual_application_id, fse.generated_at, fse.updated_at
                FROM   fertilizer_schedule_entry fse
                JOIN   block               b   ON b.id  = fse.block_id
                JOIN   estate              e   ON e.id  = b.estate_id
                JOIN   fertilizer_programme fp  ON fp.id = fse.programme_id
                JOIN   fertilizer_type     ft  ON ft.id  = fp.fertilizer_type_id
                WHERE  {" AND ".join(conditions)}
                ORDER  BY fse.due_date ASC, b.block_code
                LIMIT  %s
            """, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@fertilizer_bp.route('/entries/<entry_id>', methods=['PUT'])
@fertilizer_bp.route('/schedule/<entry_id>', methods=['PUT'])   # legacy alias
@token_required
@write_required
def update_schedule_entry(entry_id):
    """Mark a schedule entry as done or skipped.
    Body: { "status": "done"|"skipped", "actual_application_id": "<uuid>" (optional) }"""
    data = request.get_json() or {}
    new_status = data.get('status')
    if new_status not in ('done', 'skipped'):
        return jsonify({'error': 'status must be "done" or "skipped"'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE fertilizer_schedule_entry
                SET    status                = %s,
                       actual_application_id = COALESCE(%s, actual_application_id),
                       updated_at            = NOW()
                WHERE  id = %s
                RETURNING id
            """, (new_status, data.get('actual_application_id'), entry_id))
            if not cur.fetchone():
                return jsonify({'error': 'Schedule entry not found'}), 404
        conn.commit()
        return jsonify({'message': f'Entry marked {new_status}'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Alerts ────────────────────────────────────────────────────────────────────

@fertilizer_bp.route('/alerts', methods=['GET'])
@token_required
def get_alerts():
    """Return pending / due / overdue schedule entries across all estates.
    Uses the v_fertilizer_schedule_alerts view. Optionally filter by estate_id."""
    estate_id = request.args.get('estate_id')
    estate_id, err = effective_estate_id(estate_id)
    if err:
        return err

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            if estate_id:
                cur.execute("""
                    SELECT * FROM v_fertilizer_schedule_alerts
                    WHERE  estate_id = %s
                """, (estate_id,))
            else:
                cur.execute("SELECT * FROM v_fertilizer_schedule_alerts")
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


# ── Application history + recording ──────────────────────────────────────────

@fertilizer_bp.route('/applications', methods=['GET'])
@token_required
def get_applications():
    """List fertilizer application history.
    Query params: estate_id, block_id, limit (default 200)."""
    estate_id = request.args.get('estate_id')
    estate_id, err = effective_estate_id(estate_id)
    if err:
        return err

    block_id = request.args.get('block_id')
    limit    = min(int(request.args.get('limit', 200)), 500)

    conditions = []
    params     = []

    if estate_id:
        conditions.append("b.estate_id = %s")
        params.append(estate_id)
    if block_id:
        conditions.append("fa.block_id = %s")
        params.append(block_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT fa.id, fa.block_id, b.block_code,
                       e.id AS estate_id, e.name AS estate_name,
                       fa.fertilizer_type_id, ft.code AS fertilizer_code,
                       ft.name AS fertilizer_name, ft.npk_n, ft.npk_p, ft.npk_k,
                       fa.application_date, fa.quantity_kg, fa.rate_kg_per_ha,
                       fa.recommendation, fa.notes, fa.applied_by,
                       fa.created_at
                FROM   fertilizer_application fa
                JOIN   block          b   ON b.id  = fa.block_id
                JOIN   estate         e   ON e.id  = b.estate_id
                JOIN   fertilizer_type ft  ON ft.id = fa.fertilizer_type_id
                {where}
                ORDER  BY fa.application_date DESC, e.name, b.block_code
                LIMIT  %s
            """, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@fertilizer_bp.route('/applications', methods=['POST'])
@token_required
@write_required
def record_application():
    """Record an actual fertilizer application.

    Body (required): block_id, fertilizer_type_id, application_date, quantity_kg
    Body (optional): rate_kg_per_ha, recommendation, notes, applied_by,
                     schedule_id (links to a fertilizer_schedule entry and marks it done)
    """
    data = request.get_json() or {}
    required = ('block_id', 'fertilizer_type_id', 'application_date', 'quantity_kg')
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400

    quantity_kg = float(data['quantity_kg'])
    if quantity_kg <= 0:
        return jsonify({'error': 'quantity_kg must be positive'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            # Block area guard for rate backfill
            cur.execute("SELECT area_hectares FROM block WHERE id = %s", (data['block_id'],))
            block_row = cur.fetchone()
            if not block_row:
                return jsonify({'error': 'Block not found'}), 404
            area_ha = float(block_row[0]) if block_row[0] else None

            # Compute rate if not supplied and area is known
            rate = data.get('rate_kg_per_ha')
            if rate is None and area_ha and area_ha > 0:
                rate = round(quantity_kg / area_ha, 2)

            # applied_by is UUID FK to "user" — use JWT user if not explicitly provided
            applied_by = data.get('applied_by') or request.user.get('user_id')

            cur.execute("""
                INSERT INTO fertilizer_application
                    (block_id, fertilizer_type_id, application_date,
                     quantity_kg, rate_kg_per_ha, recommendation, notes, applied_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                data['block_id'], data['fertilizer_type_id'],
                data['application_date'], quantity_kg, rate,
                data.get('recommendation'), data.get('notes'),
                applied_by,
            ))
            app_id = str(cur.fetchone()[0])

            # If a schedule entry was linked, mark it done
            schedule_id = data.get('schedule_id')
            if schedule_id:
                cur.execute("""
                    UPDATE fertilizer_schedule_entry
                    SET    status = 'done',
                           actual_application_id = %s,
                           updated_at = NOW()
                    WHERE  id = %s
                """, (app_id, schedule_id))

        conn.commit()
        return jsonify({'id': app_id, 'message': 'Application recorded'}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Fertilizer type catalogue ────────────────────────────────────────────────

@fertilizer_bp.route('/types', methods=['GET'])
@fertilizer_bp.route('/products', methods=['GET'])
@token_required
def get_fertilizer_types():
    """Return all fertilizer product types with NPK data."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, code, name, npk_n, npk_p, npk_k,
                       default_dosage_kg, description
                FROM   fertilizer_type
                ORDER  BY code
            """)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@fertilizer_bp.route('/types', methods=['POST'])
@fertilizer_bp.route('/products', methods=['POST'])
@token_required
@write_required
def create_fertilizer_type():
    """Create a new fertilizer product type.
    Body (required): code, name
    Body (optional): npk_n, npk_p, npk_k, default_dosage_kg, description"""
    data = request.get_json() or {}
    if not data.get('code') or not data.get('name'):
        return jsonify({'error': 'code and name are required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO fertilizer_type
                    (code, name, npk_n, npk_p, npk_k, default_dosage_kg, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                data['code'].strip().upper(),
                data['name'].strip(),
                data.get('npk_n'),
                data.get('npk_p'),
                data.get('npk_k'),
                data.get('default_dosage_kg'),
                data.get('description'),
            ))
            new_id = str(cur.fetchone()[0])
        conn.commit()
        return jsonify({'id': new_id, 'message': 'Fertilizer type created'}), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


@fertilizer_bp.route('/types/<type_id>', methods=['PUT'])
@fertilizer_bp.route('/products/<type_id>', methods=['PUT'])
@token_required
@write_required
def update_fertilizer_type(type_id):
    """Update an existing fertilizer product type.
    Updatable fields: name, npk_n, npk_p, npk_k, default_dosage_kg, description
    (code is immutable once set)."""
    data = request.get_json() or {}
    allowed = ('name', 'npk_n', 'npk_p', 'npk_k', 'default_dosage_kg', 'description')
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': 'No updatable fields provided'}), 400

    set_clause = ', '.join(f"{k} = %s" for k in updates)
    params = list(updates.values()) + [type_id]

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE fertilizer_type SET {set_clause} WHERE id = %s RETURNING id",
                params,
            )
            if not cur.fetchone():
                return jsonify({'error': 'Fertilizer type not found'}), 404
        conn.commit()
        return jsonify({'message': 'Fertilizer type updated'}), 200
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Block application history ─────────────────────────────────────────────────

@fertilizer_bp.route('/history', methods=['GET'])
@token_required
def get_history():
    """Full fertilizer application history for a single block, including the
    linked schedule entry status where one exists.
    Query params: block_id (required), limit (default 100)."""
    block_id = request.args.get('block_id')
    if not block_id:
        return jsonify({'error': 'block_id is required'}), 400

    limit = min(int(request.args.get('limit', 100)), 500)

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    try:
        with conn.cursor() as cur:
            # Verify block exists before querying history
            cur.execute("SELECT id FROM block WHERE id = %s", (block_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Block not found'}), 404

            cur.execute("""
                SELECT fa.id,
                       fa.application_date,
                       ft.code                              AS fertilizer_code,
                       ft.name                             AS fertilizer_name,
                       ft.npk_n, ft.npk_p, ft.npk_k,
                       fa.quantity_kg,
                       fa.rate_kg_per_ha,
                       ROUND(fa.rate_kg_per_ha * b.area_hectares, 1) AS total_kg,
                       fa.recommendation,
                       fa.notes,
                       fa.applied_by,
                       fs.id                               AS schedule_id,
                       fs.status                           AS schedule_status,
                       fs.due_date                         AS scheduled_due_date,
                       fa.created_at
                FROM   fertilizer_application fa
                JOIN   block           b   ON b.id  = fa.block_id
                JOIN   fertilizer_type ft  ON ft.id = fa.fertilizer_type_id
                LEFT   JOIN fertilizer_schedule_entry fs ON fs.actual_application_id = fa.id
                WHERE  fa.block_id = %s
                ORDER  BY fa.application_date DESC
                LIMIT  %s
            """, (block_id, limit))
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()
