"""ROI Calculator API — input costs, yield records, and ROI snapshots."""
import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from flask import Blueprint, jsonify, request
from auth import token_required, get_db_connection

logger = logging.getLogger(__name__)
roi_bp = Blueprint('roi', __name__, url_prefix='/api/roi')


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _to_json(v):
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
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


# ── Helper: Recalculate ROI snapshot ─────────────────────────────────────────

def _recalculate_roi_snapshot(year, month):
    """
    Opens its OWN connection, recalculates roi_snapshot for ALL estates
    in a given year/month, then closes it. Fully independent of the
    calling function's connection.
    """
    conn = get_db_connection()
    if not conn:
        logger.error("Snapshot recalc: could not get DB connection")
        return

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    ic.estate_id,
                    ic.total_cost_lkr,
                    yr.yield_kg,
                    CASE WHEN yr.yield_kg > 0
                         THEN ic.total_cost_lkr / yr.yield_kg
                         ELSE NULL
                    END as cost_per_kg
                FROM input_cost ic
                JOIN yield_record yr
                    ON yr.estate_id = ic.estate_id
                    AND yr.year = ic.year
                    AND yr.month = ic.month
                WHERE ic.year = %s AND ic.month = %s
            """, (year, month))

            rows = cur.fetchall()

            if not rows:
                logger.warning(f"Snapshot recalc: no complete data for {year}/{month}")
                return

            estate_costs = []
            for r in rows:
                eid, total_cost, yield_kg, cpk = r
                if cpk is not None:
                    estate_costs.append((str(eid), float(cpk)))

            if not estate_costs:
                return

            costs_only = [c for _, c in estate_costs]
            mean_cost = sum(costs_only) / len(costs_only)
            variance = sum((x - mean_cost) ** 2 for x in costs_only) / len(costs_only)
            std_dev = variance ** 0.5
            threshold = mean_cost + std_dev

            sorted_costs = sorted(estate_costs, key=lambda x: x[1])
            rank_map = {eid: i + 1 for i, (eid, _) in enumerate(sorted_costs)}

            for eid, cpk in estate_costs:
                rank = rank_map[eid]
                is_flagged = cpk > threshold
                flag_reason = (
                    f"Cost per kg (Rs. {cpk:.2f}) exceeds threshold (Rs. {threshold:.2f})"
                    if is_flagged else None
                )
                cur.execute("""
                    INSERT INTO roi_snapshot
                        (estate_id, year, month, cost_per_kg, rank, is_flagged, flag_reason, computed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (estate_id, year, month)
                    DO UPDATE SET
                        cost_per_kg  = EXCLUDED.cost_per_kg,
                        rank         = EXCLUDED.rank,
                        is_flagged   = EXCLUDED.is_flagged,
                        flag_reason  = EXCLUDED.flag_reason,
                        computed_at  = EXCLUDED.computed_at
                """, (eid, year, month, cpk, rank, is_flagged, flag_reason, datetime.utcnow()))

        conn.commit()
        logger.info(f"Snapshot recalculated for all estates in {year}/{month}")

    except Exception as e:
        logger.error(f"Snapshot recalc error: {e}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()


# ── Input Costs ───────────────────────────────────────────────────────────────

@roi_bp.route('/input-costs', methods=['GET'])
@token_required
def list_input_costs():
    estate_id = request.args.get('estate_id')
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503

    try:
        with conn.cursor() as cur:
            sql = """
                SELECT ic.id, ic.estate_id, e.name as estate_name,
                       ic.year, ic.month,
                       ic.fertilizer_cost_lkr, ic.chemical_cost_lkr,
                       ic.labour_input_cost_lkr, ic.other_cost_lkr,
                       ic.total_cost_lkr, ic.source,
                       ic.created_at, ic.updated_at
                FROM input_cost ic
                JOIN estate e ON e.id = ic.estate_id
                WHERE 1=1
            """
            params = []
            if estate_id:
                sql += " AND ic.estate_id = %s"
                params.append(estate_id)
            if year:
                sql += " AND ic.year = %s"
                params.append(year)
            if month:
                sql += " AND ic.month = %s"
                params.append(month)
            sql += " ORDER BY ic.year DESC, ic.month DESC"
            cur.execute(sql, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@roi_bp.route('/input-costs', methods=['POST'])
@token_required
def create_input_cost():
    data = request.get_json() or {}

    estate_id            = data.get('estate_id')
    year                 = int(data.get('year'))  if data.get('year')  is not None else None
    month                = int(data.get('month')) if data.get('month') is not None else None
    fertilizer_cost_lkr  = data.get('fertilizer_cost_lkr',  0)
    chemical_cost_lkr    = data.get('chemical_cost_lkr',    0)
    labour_input_cost_lkr= data.get('labour_input_cost_lkr',0)
    other_cost_lkr       = data.get('other_cost_lkr',       0)
    source               = data.get('source', 'manual')

    if not estate_id or year is None or month is None:
        return jsonify({'error': 'estate_id, year, and month are required'}), 400
    if not (2000 <= year <= 2100):
        return jsonify({'error': 'year must be between 2000 and 2100'}), 400
    if not (1 <= month <= 12):
        return jsonify({'error': 'month must be between 1 and 12'}), 400

    for field, value in [
        ('fertilizer_cost_lkr',   fertilizer_cost_lkr),
        ('chemical_cost_lkr',     chemical_cost_lkr),
        ('labour_input_cost_lkr', labour_input_cost_lkr),
        ('other_cost_lkr',        other_cost_lkr),
    ]:
        try:
            if float(value) < 0:
                return jsonify({'error': f'{field} must be non-negative'}), 400
        except (TypeError, ValueError):
            return jsonify({'error': f'{field} must be a valid number'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM input_cost
                WHERE estate_id = %s AND year = %s AND month = %s
            """, (estate_id, year, month))
            if cur.fetchone():
                return jsonify({'error': 'Input cost record already exists for this estate/year/month'}), 409

            cur.execute("SELECT id FROM estate WHERE id = %s", (estate_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Estate not found'}), 404

            cur.execute("""
                INSERT INTO input_cost
                    (estate_id, year, month, fertilizer_cost_lkr, chemical_cost_lkr,
                     labour_input_cost_lkr, other_cost_lkr, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, estate_id, year, month,
                          fertilizer_cost_lkr, chemical_cost_lkr,
                          labour_input_cost_lkr, other_cost_lkr,
                          total_cost_lkr, source, created_at
            """, (estate_id, year, month,
                  fertilizer_cost_lkr, chemical_cost_lkr,
                  labour_input_cost_lkr, other_cost_lkr, source))

            record = _row_dict(cur, cur.fetchone())

        conn.commit()  # commit BEFORE snapshot, on its own connection block

    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()  # close BEFORE snapshot opens its own connection

    # Snapshot runs on a completely separate connection after the record is safely committed
    try:
        _recalculate_roi_snapshot(year, month)
    except Exception as snap_err:
        logger.error(f"Snapshot failed (record was saved): {snap_err}")

    return jsonify(record), 201


# ── Yield Records ─────────────────────────────────────────────────────────────

@roi_bp.route('/yield-records', methods=['GET'])
@token_required
def list_yield_records():
    estate_id = request.args.get('estate_id')
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503

    try:
        with conn.cursor() as cur:
            sql = """
                SELECT yr.id, yr.estate_id, e.name as estate_name,
                       yr.year, yr.month, yr.yield_kg, yr.source,
                       yr.created_at, yr.updated_at
                FROM yield_record yr
                JOIN estate e ON e.id = yr.estate_id
                WHERE 1=1
            """
            params = []
            if estate_id:
                sql += " AND yr.estate_id = %s"
                params.append(estate_id)
            if year:
                sql += " AND yr.year = %s"
                params.append(year)
            if month:
                sql += " AND yr.month = %s"
                params.append(month)
            sql += " ORDER BY yr.year DESC, yr.month DESC"
            cur.execute(sql, params)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@roi_bp.route('/yield-records', methods=['POST'])
@token_required
def create_yield_record():
    data = request.get_json() or {}

    estate_id = data.get('estate_id')
    year      = int(data.get('year'))  if data.get('year')  is not None else None
    month     = int(data.get('month')) if data.get('month') is not None else None
    yield_kg  = data.get('yield_kg')
    source    = data.get('source', 'manual')

    if not estate_id or year is None or month is None or yield_kg is None:
        return jsonify({'error': 'estate_id, year, month, and yield_kg are required'}), 400
    if not (2000 <= year <= 2100):
        return jsonify({'error': 'year must be between 2000 and 2100'}), 400
    if not (1 <= month <= 12):
        return jsonify({'error': 'month must be between 1 and 12'}), 400

    try:
        yield_kg_float = float(yield_kg)
        if yield_kg_float < 0:
            return jsonify({'error': 'yield_kg must be non-negative'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'yield_kg must be a valid number'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM yield_record
                WHERE estate_id = %s AND year = %s AND month = %s
            """, (estate_id, year, month))
            if cur.fetchone():
                return jsonify({'error': 'Yield record already exists for this estate/year/month'}), 409

            cur.execute("SELECT id FROM estate WHERE id = %s", (estate_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Estate not found'}), 404

            cur.execute("""
                INSERT INTO yield_record (estate_id, year, month, yield_kg, source)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, estate_id, year, month, yield_kg, source, created_at
            """, (estate_id, year, month, yield_kg_float, source))

            record = _row_dict(cur, cur.fetchone())

        conn.commit()  # commit BEFORE snapshot

    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()  # close BEFORE snapshot opens its own connection

    # Snapshot runs on a completely separate connection after the record is safely committed
    try:
        _recalculate_roi_snapshot(year, month)
    except Exception as snap_err:
        logger.error(f"Snapshot failed (record was saved): {snap_err}")

    return jsonify(record), 201


# ── ROI Summary & Rankings ────────────────────────────────────────────────────

@roi_bp.route('/summary', methods=['GET'])
@token_required
def get_roi_summary():
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503

    try:
        with conn.cursor() as cur:
            months = request.args.get('months', type=int)
            year   = request.args.get('year',   type=int)
            month  = request.args.get('month',  type=int)

            if months:
                cur.execute("""
                    SELECT
                        COUNT(DISTINCT rs.estate_id)                                        as total_estates,
                        ROUND(AVG(rs.cost_per_kg)::numeric, 2)                             as avg_cost_per_kg,
                        MIN(rs.cost_per_kg)                                                as best_cost_per_kg,
                        MAX(rs.cost_per_kg)                                                as worst_cost_per_kg,
                        COUNT(DISTINCT CASE WHEN rs.is_flagged THEN rs.estate_id END)      as flagged_count
                    FROM roi_snapshot rs
                    WHERE (rs.year * 100 + rs.month) >= (
                        EXTRACT(YEAR FROM NOW() - INTERVAL '11 months')::int * 100 +
                        EXTRACT(MONTH FROM NOW() - INTERVAL '11 months')::int
                    )
                """)
            else:
                if not year or not month:
                    now   = datetime.now()
                    year  = now.year
                    month = now.month
                cur.execute("""
                    SELECT
                        COUNT(DISTINCT rs.estate_id)           as total_estates,
                        ROUND(AVG(rs.cost_per_kg)::numeric, 2) as avg_cost_per_kg,
                        MIN(rs.cost_per_kg)                    as best_cost_per_kg,
                        MAX(rs.cost_per_kg)                    as worst_cost_per_kg,
                        COUNT(CASE WHEN rs.is_flagged THEN 1 END) as flagged_count
                    FROM roi_snapshot rs
                    WHERE rs.year = %s AND rs.month = %s
                """, (year, month))

            row = cur.fetchone()
            return jsonify({
                'year':              year  if not months else None,
                'month':             month if not months else None,
                'total_estates':     row[0] or 0,
                'avg_cost_per_kg':   float(row[1]) if row[1] else 0,
                'best_cost_per_kg':  float(row[2]) if row[2] else 0,
                'worst_cost_per_kg': float(row[3]) if row[3] else 0,
                'flagged_count':     row[4] or 0,
            }), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@roi_bp.route('/rankings', methods=['GET'])
@token_required
def get_roi_rankings():
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503

    try:
        with conn.cursor() as cur:
            months = request.args.get('months', type=int)
            year   = request.args.get('year',   type=int)
            month  = request.args.get('month',  type=int)

            if months:
                cur.execute("""
                    SELECT
                        e.name                                 as estate_name,
                        e.region,
                        ROUND(AVG(rs.cost_per_kg)::numeric, 2) as cost_per_kg,
                        SUM(yr.yield_kg)                       as yield_kg,
                        SUM(ic.total_cost_lkr)                 as total_cost,
                        COUNT(rs.id)                           as months_with_data,
                        BOOL_OR(rs.is_flagged)                 as is_flagged,
                        ROW_NUMBER() OVER (
                            ORDER BY AVG(rs.cost_per_kg) ASC NULLS LAST
                        )                                      as rank
                    FROM roi_snapshot rs
                    JOIN estate e ON e.id = rs.estate_id
                    LEFT JOIN input_cost ic
                        ON ic.estate_id = e.id
                        AND ic.year = rs.year AND ic.month = rs.month
                    LEFT JOIN yield_record yr
                        ON yr.estate_id = e.id
                        AND yr.year = rs.year AND yr.month = rs.month
                    WHERE (rs.year * 100 + rs.month) >= (
                        EXTRACT(YEAR FROM NOW() - INTERVAL '11 months')::int * 100 +
                        EXTRACT(MONTH FROM NOW() - INTERVAL '11 months')::int
                    )
                    GROUP BY e.id, e.name, e.region
                    ORDER BY rank
                """)
            else:
                if not year or not month:
                    now   = datetime.now()
                    year  = now.year
                    month = now.month
                cur.execute("""
                    SELECT
                        rs.rank,
                        e.name      as estate_name,
                        e.region,
                        rs.cost_per_kg,
                        COALESCE(yr.yield_kg, 0)       as yield_kg,
                        COALESCE(ic.total_cost_lkr, 0) as total_cost,
                        rs.is_flagged,
                        rs.flag_reason
                    FROM roi_snapshot rs
                    JOIN estate e ON e.id = rs.estate_id
                    LEFT JOIN input_cost ic
                        ON ic.estate_id = e.id
                        AND ic.year = rs.year AND ic.month = rs.month
                    LEFT JOIN yield_record yr
                        ON yr.estate_id = e.id
                        AND yr.year = rs.year AND yr.month = rs.month
                    WHERE rs.year = %s AND rs.month = %s
                    ORDER BY rs.rank ASC NULLS LAST
                """, (year, month))

            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


# ── Estates List ──────────────────────────────────────────────────────────────

@roi_bp.route('/estates', methods=['GET'])
@token_required
def get_estates():
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, region, total_blocks
                FROM estate
                ORDER BY name
            """)
            return jsonify(_rows(cur)), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@roi_bp.route('/estate-trend', methods=['GET'])
@token_required
def get_estate_trend():
    """GET /api/roi/estate-trend?estate_id=&year= — monthly cost/kg for one estate for a full year."""
    estate_id = request.args.get('estate_id')
    year = request.args.get('year', type=int)

    if not estate_id or not year:
        return jsonify({'error': 'estate_id and year are required'}), 400

    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT rs.month, rs.cost_per_kg
                FROM roi_snapshot rs
                WHERE rs.estate_id = %s AND rs.year = %s
                ORDER BY rs.month ASC
            """, (estate_id, year))
            rows = cur.fetchall()

            # Return all 12 months, 0 for months with no data
            data = {row[0]: float(row[1]) if row[1] else 0 for row in rows}
            result = [
                {'month': m, 'cost_per_kg': data.get(m, 0)}
                for m in range(1, 13)
            ]
            return jsonify(result), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()