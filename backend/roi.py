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


# ── Helper: Recalculate ROI snapshot for estate/year/month ────────────────────

def _recalculate_roi_snapshot(conn, estate_id, year, month):
    """
    Recalculate and upsert roi_snapshot for a given estate/year/month.
    - Joins input_cost and yield_record
    - Computes cost_per_kg = total_cost_lkr / yield_kg
    - Calculates rank and flags outliers (cost_per_kg > mean + 1 std dev)
    """
    try:
        with conn.cursor() as cur:
            # Fetch cost and yield for this estate/year/month
            cur.execute("""
                SELECT ic.total_cost_lkr, yr.yield_kg
                FROM input_cost ic
                LEFT JOIN yield_record yr
                    ON yr.estate_id = ic.estate_id
                    AND yr.year = ic.year
                    AND yr.month = ic.month
                WHERE ic.estate_id = %s AND ic.year = %s AND ic.month = %s
            """, (estate_id, year, month))
            
            row = cur.fetchone()
            if not row:
                logger.warning(f"No input_cost found for {estate_id}/{year}/{month}")
                return
            
            total_cost_lkr, yield_kg = row
            
            # Calculate cost_per_kg
            if yield_kg and yield_kg > 0:
                cost_per_kg = float(Decimal(str(total_cost_lkr)) / Decimal(str(yield_kg)))
            else:
                cost_per_kg = None
            
            # Calculate all cost_per_kg values for this period to determine rank and flags
            cur.execute("""
                SELECT COALESCE(ic.total_cost_lkr, 0) as cost, 
                       COALESCE(yr.yield_kg, 0) as yield
                FROM estate e
                LEFT JOIN input_cost ic
                    ON ic.estate_id = e.id AND ic.year = %s AND ic.month = %s
                LEFT JOIN yield_record yr
                    ON yr.estate_id = e.id AND yr.year = %s AND yr.month = %s
                WHERE ic.id IS NOT NULL OR yr.id IS NOT NULL
                ORDER BY ic.total_cost_lkr DESC NULLS LAST
            """, (year, month, year, month))
            
            all_costs = []
            rank = None
            for i, row in enumerate(cur.fetchall(), 1):
                cost, yield_val = row
                if yield_val and yield_val > 0:
                    cost_kg = float(Decimal(str(cost)) / Decimal(str(yield_val)))
                    all_costs.append(cost_kg)
                    if (estate_id == estate_id):  # Note: this logic will be refined
                        if rank is None:
                            rank = i
            
            # Simple rank: lower cost is better (rank 1 is lowest)
            # Recalculate with proper estate matching
            cur.execute("""
                WITH ranked AS (
                    SELECT 
                        ic.estate_id,
                        CASE WHEN yr.yield_kg > 0 
                             THEN ic.total_cost_lkr / yr.yield_kg 
                             ELSE NULL 
                        END as cost_per_kg,
                        ROW_NUMBER() OVER (ORDER BY ic.total_cost_lkr / yr.yield_kg ASC NULLS LAST) as rank
                    FROM input_cost ic
                    LEFT JOIN yield_record yr
                        ON yr.estate_id = ic.estate_id
                        AND yr.year = ic.year
                        AND yr.month = ic.month
                    WHERE ic.year = %s AND ic.month = %s
                )
                SELECT rank FROM ranked WHERE estate_id = %s
            """, (year, month, estate_id))
            
            rank_row = cur.fetchone()
            rank = rank_row[0] if rank_row else None
            
            # Check if flagged (cost_per_kg exceeds mean + 1 std dev)
            is_flagged = False
            flag_reason = None
            
            if all_costs and cost_per_kg is not None:
                mean_cost = sum(all_costs) / len(all_costs)
                variance = sum((x - mean_cost) ** 2 for x in all_costs) / len(all_costs)
                std_dev = variance ** 0.5
                threshold = mean_cost + std_dev
                
                if cost_per_kg > threshold:
                    is_flagged = True
                    flag_reason = f"Cost per kg (Rs. {cost_per_kg:.2f}) exceeds threshold (Rs. {threshold:.2f})"
            
            # Upsert roi_snapshot
            cur.execute("""
                INSERT INTO roi_snapshot (estate_id, year, month, cost_per_kg, rank, is_flagged, flag_reason, computed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (estate_id, year, month)
                DO UPDATE SET
                    cost_per_kg = %s,
                    rank = %s,
                    is_flagged = %s,
                    flag_reason = %s,
                    computed_at = %s
            """, (
                estate_id, year, month, cost_per_kg, rank, is_flagged, flag_reason, datetime.utcnow(),
                cost_per_kg, rank, is_flagged, flag_reason, datetime.utcnow()
            ))
            
            conn.commit()
            logger.info(f"ROI snapshot recalculated for {estate_id}/{year}/{month}")
    except Exception as e:
        logger.error(f"Error recalculating ROI snapshot: {e}", exc_info=True)


# ── Input Costs ───────────────────────────────────────────────────────────────

@roi_bp.route('/input-costs', methods=['GET'])
@token_required
def list_input_costs():
    """GET /api/roi/input-costs?estate_id=&year=&month="""
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
    """POST /api/roi/input-costs — create input cost record."""
    data = request.get_json() or {}
    
    estate_id = data.get('estate_id')
    year = int(data.get('year')) if data.get('year') is not None else None
    month = int(data.get('month')) if data.get('month') is not None else None
    fertilizer_cost_lkr = data.get('fertilizer_cost_lkr', 0)
    chemical_cost_lkr = data.get('chemical_cost_lkr', 0)
    labour_input_cost_lkr = data.get('labour_input_cost_lkr', 0)
    other_cost_lkr = data.get('other_cost_lkr', 0)
    source = data.get('source', 'manual')
    
    # Validation
    if not estate_id or year is None or month is None:
        return jsonify({'error': 'estate_id, year, and month are required'}), 400
    
    if not (2000 <= year <= 2100):
        return jsonify({'error': 'year must be between 2000 and 2100'}), 400
    
    if not (1 <= month <= 12):
        return jsonify({'error': 'month must be between 1 and 12'}), 400
    
    # Validate all cost fields are non-negative
    for field, value in [
        ('fertilizer_cost_lkr', fertilizer_cost_lkr),
        ('chemical_cost_lkr', chemical_cost_lkr),
        ('labour_input_cost_lkr', labour_input_cost_lkr),
        ('other_cost_lkr', other_cost_lkr)
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
            # Check for duplicate
            cur.execute("""
                SELECT id FROM input_cost
                WHERE estate_id = %s AND year = %s AND month = %s
            """, (estate_id, year, month))
            
            if cur.fetchone():
                return jsonify({'error': 'Input cost record already exists for this estate/year/month'}), 409
            
            # Verify estate exists
            cur.execute("SELECT id FROM estate WHERE id = %s", (estate_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Estate not found'}), 404
            
            # Insert input cost
            cur.execute("""
                INSERT INTO input_cost
                    (estate_id, year, month, fertilizer_cost_lkr, chemical_cost_lkr,
                     labour_input_cost_lkr, other_cost_lkr, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, estate_id, year, month,
                          fertilizer_cost_lkr, chemical_cost_lkr,
                          labour_input_cost_lkr, other_cost_lkr,
                          total_cost_lkr, source, created_at
            """, (
                estate_id, year, month,
                fertilizer_cost_lkr, chemical_cost_lkr,
                labour_input_cost_lkr, other_cost_lkr,
                source
            ))
            
            record = _row_dict(cur, cur.fetchone())
            conn.commit()
            
            # Trigger ROI snapshot recalculation
            _recalculate_roi_snapshot(conn, estate_id, year, month)
            
            return jsonify(record), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── Yield Records ─────────────────────────────────────────────────────────────

@roi_bp.route('/yield-records', methods=['GET'])
@token_required
def list_yield_records():
    """GET /api/roi/yield-records?estate_id=&year=&month="""
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
    """POST /api/roi/yield-records — create yield record."""
    data = request.get_json() or {}
    
    estate_id = data.get('estate_id')
    year = int(data.get('year')) if data.get('year') is not None else None
    month = int(data.get('month')) if data.get('month') is not None else None
    yield_kg = data.get('yield_kg')
    source = data.get('source', 'manual')
    
    # Validation
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
            # Check for duplicate
            cur.execute("""
                SELECT id FROM yield_record
                WHERE estate_id = %s AND year = %s AND month = %s
            """, (estate_id, year, month))
            
            if cur.fetchone():
                return jsonify({'error': 'Yield record already exists for this estate/year/month'}), 409
            
            # Verify estate exists
            cur.execute("SELECT id FROM estate WHERE id = %s", (estate_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Estate not found'}), 404
            
            # Insert yield record
            cur.execute("""
                INSERT INTO yield_record (estate_id, year, month, yield_kg, source)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, estate_id, year, month, yield_kg, source, created_at
            """, (estate_id, year, month, yield_kg_float, source))
            
            record = _row_dict(cur, cur.fetchone())
            conn.commit()
            
            # Trigger ROI snapshot recalculation
            _recalculate_roi_snapshot(conn, estate_id, year, month)
            
            return jsonify(record), 201
    except Exception as e:
        conn.rollback()
        return _db_err(e)
    finally:
        conn.close()


# ── ROI Summary & Rankings ────────────────────────────────────────────────────

@roi_bp.route('/summary', methods=['GET'])
@token_required
def get_roi_summary():
    """GET /api/roi/summary — get summary stats for current month."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    
    try:
        with conn.cursor() as cur:
            # Get current year and month (or allow query param)
            year = request.args.get('year', type=int)
            month = request.args.get('month', type=int)
            
            if not year or not month:
                now = datetime.now()
                year = now.year
                month = now.month
            
            # Get summary stats
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT rs.estate_id) as total_estates,
                    ROUND(AVG(rs.cost_per_kg)::numeric, 2) as avg_cost_per_kg,
                    MIN(rs.cost_per_kg) as best_cost_per_kg,
                    MAX(rs.cost_per_kg) as worst_cost_per_kg,
                    COUNT(CASE WHEN rs.is_flagged THEN 1 END) as flagged_count
                FROM roi_snapshot rs
                WHERE rs.year = %s AND rs.month = %s
            """, (year, month))
            
            row = cur.fetchone()
            summary = {
                'year': year,
                'month': month,
                'total_estates': row[0] or 0,
                'avg_cost_per_kg': float(row[1]) if row[1] else 0,
                'best_cost_per_kg': float(row[2]) if row[2] else 0,
                'worst_cost_per_kg': float(row[3]) if row[3] else 0,
                'flagged_count': row[4] or 0
            }
            
            return jsonify(summary), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


@roi_bp.route('/rankings', methods=['GET'])
@token_required
def get_roi_rankings():
    """GET /api/roi/rankings — get estate rankings by cost/kg."""
    conn = _db()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503
    
    try:
        with conn.cursor() as cur:
            year = request.args.get('year', type=int)
            month = request.args.get('month', type=int)
            
            if not year or not month:
                now = datetime.now()
                year = now.year
                month = now.month
            
            cur.execute("""
                SELECT 
                    rs.rank,
                    e.name as estate_name,
                    e.region,
                    rs.cost_per_kg,
                    COALESCE(yr.yield_kg, 0) as yield_kg,
                    COALESCE(ic.total_cost_lkr, 0) as total_cost,
                    rs.is_flagged,
                    rs.flag_reason
                FROM roi_snapshot rs
                JOIN estate e ON e.id = rs.estate_id
                LEFT JOIN input_cost ic ON ic.estate_id = e.id AND ic.year = rs.year AND ic.month = rs.month
                LEFT JOIN yield_record yr ON yr.estate_id = e.id AND yr.year = rs.year AND yr.month = rs.month
                WHERE rs.year = %s AND rs.month = %s
                ORDER BY rs.rank ASC NULLS LAST
            """, (year, month))
            
            rankings = _rows(cur)
            return jsonify(rankings), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()


# ── Estates List ──────────────────────────────────────────────────────────────

@roi_bp.route('/estates', methods=['GET'])
@token_required
def get_estates():
    """GET /api/roi/estates — list all estates for dropdown."""
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
            
            estates = _rows(cur)
            return jsonify(estates), 200
    except Exception as e:
        return _db_err(e)
    finally:
        conn.close()
