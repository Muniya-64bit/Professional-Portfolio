from flask import Blueprint, jsonify, request
from auth import token_required
import psycopg
import os

water_bp = Blueprint('water', __name__)

def get_db():
    return psycopg.connect(os.environ.get('DATABASE_URL'))

# ── GET /api/water/status ─────────────────────────────────────────────────
# Returns latest month status for all factories
@water_bp.route('/api/water/status', methods=['GET'])
@token_required
def get_water_status():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT factory, estate, year, month, water_m3, yield_kg, intensity_m3_per_kg, baseline_intensity, track_status FROM v_water_status_latest")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    result = []
    for row in rows:
        result.append({
            'factory':           row[0],
            'estate':            row[1],
            'year':              row[2],
            'month':             row[3],
            'water_m3':          float(row[4]),
            'yield_kg':          float(row[5]),
            'intensity_l_per_kg': round(float(row[6]) * 1000, 3) if row[6] else None,
            'baseline_intensity': float(row[7]) * 1000 if row[7] else None,
            'track_status':      row[8]
        })

    return jsonify(result), 200


# ── GET /api/water/usage?estate_id=&year= ────────────────────────────────
# Returns monthly trend for one estate's factory
@water_bp.route('/api/water/usage', methods=['GET'])
@token_required
def get_water_usage():
    estate_id = request.args.get('estate_id')
    year      = request.args.get('year', 2026)

    conn = get_db()
    cur  = conn.cursor()

    if estate_id:
        cur.execute("""
            SELECT w.id, f.name, e.name, w.year, w.month,
                   w.water_m3, w.yield_kg, w.intensity, w.track_status
            FROM water_usage w
            JOIN factory f ON f.id = w.factory_id
            JOIN estate  e ON e.id = f.estate_id
            WHERE e.id = %s AND w.year = %s
            ORDER BY w.month
        """, (estate_id, year))
    else:
        cur.execute("""
            SELECT w.id, f.name, e.name, w.year, w.month,
                   w.water_m3, w.yield_kg, w.intensity, w.track_status
            FROM water_usage w
            JOIN factory f ON f.id = w.factory_id
            JOIN estate  e ON e.id = f.estate_id
            WHERE w.year = %s
            ORDER BY e.name, w.month
        """, (year,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    months = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    result = []
    for row in rows:
        result.append({
            'id':               row[0],
            'factory':          row[1],
            'estate':           row[2],
            'year':             row[3],
            'month_num':        row[4],
            'month':            months[row[4]],
            'water_m3':         float(row[5]),
            'yield_kg':         float(row[6]),
            'intensity_l_per_kg': round(float(row[7]) * 1000, 3) if row[7] else None,
            'track_status':     row[8]
        })

    return jsonify(result), 200


# ── GET /api/water/baseline ──────────────────────────────────────────────
# Returns baseline and annual target for all factories
@water_bp.route('/api/water/baseline', methods=['GET'])
@token_required
def get_water_baseline():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        SELECT wb.id, f.name, e.name, wb.baseline_year,
               wb.baseline_intensity, wb.annual_target_pct
        FROM water_baseline wb
        JOIN factory f ON f.id = wb.factory_id
        JOIN estate  e ON e.id = f.estate_id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    result = []
    for row in rows:
        result.append({
            'id':                  row[0],
            'factory':             row[1],
            'estate':              row[2],
            'baseline_year':       row[3],
            'baseline_intensity':  float(row[4]),
            'annual_target_pct':   float(row[5])
        })

    return jsonify(result), 200


# ── GET /api/water/estates ───────────────────────────────────────────────
# Returns all estates with their factory IDs (needed for filtering)
@water_bp.route('/api/water/estates', methods=['GET'])
@token_required
def get_water_estates():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        SELECT e.id, e.name, f.id AS factory_id, f.name AS factory_name
        FROM estate e
        JOIN factory f ON f.estate_id = e.id
        ORDER BY e.name
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    result = []
    for row in rows:
        result.append({
            'estate_id':    row[0],
            'estate':       row[1],
            'factory_id':   row[2],
            'factory':      row[3]
        })

    return jsonify(result), 200