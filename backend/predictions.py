"""
Yield predictions module — calls the FastAPI ML service.
Falls back to heuristic if FastAPI is unavailable (FR-LAO-03).
"""
import logging
import os
import requests
from decimal import Decimal
from flask import Blueprint, jsonify, request
from auth import token_required, get_db_connection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

predictions_bp = Blueprint('predictions', __name__)

FASTAPI_URL = os.getenv('FASTAPI_URL', 'http://localhost:8000')
MODEL_VERSION = 'xgboost_v1'
FALLBACK_MODEL_VERSION = 'heuristic_v1_fallback'
CONFIDENCE_BAND = 0.10
FALLBACK_KG_PER_WORKER = 600.0
RECENT_WINDOW = 6


# =============================================================================
# Heuristic fallback (used when FastAPI is unavailable)
# =============================================================================

def _f(v):
    return float(v) if isinstance(v, Decimal) else v


def _heuristic_forecast(history, worker_capacity, year, month):
    if not history:
        return round(worker_capacity * FALLBACK_KG_PER_WORKER, 3)
    same_month_last_year = next(
        (y for (yr, mo, y) in history if yr == year - 1 and mo == month), None
    )
    if same_month_last_year is not None:
        return round(_f(same_month_last_year), 3)
    recent = [_f(y) for (_, _, y) in history[-RECENT_WINDOW:]]
    base = sum(recent) / len(recent)
    trend = (recent[-1] - recent[-2]) if len(recent) >= 2 else 0.0
    return round(max(0.0, base + trend), 3)


# =============================================================================
# ML prediction via FastAPI
# =============================================================================

def _call_fastapi(blocks_payload, year, month):
    """Call FastAPI /predict-batch. Returns list of predictions or None on failure."""
    try:
        response = requests.post(
            f"{FASTAPI_URL}/predict-batch",
            json={"blocks": blocks_payload, "year": year, "month": month},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("predictions", [])
        logger.warning("FastAPI returned %s", response.status_code)
        return None
    except Exception as e:
        logger.warning("FastAPI unavailable: %s", e)
        return None


def compute_block_predictions(cur, estate_id, year, month):
    """
    Compute + upsert yield predictions for every block of an estate.
    Tries FastAPI ML model first, falls back to heuristic if unavailable.
    Returns { block_id(str): predicted_yield_kg }
    """
    # Fetch all blocks with their ML features
    cur.execute("""
        SELECT b.id, b.block_code, b.zone, b.elevation_m, b.area_hectares,
               b.soil_type, b.growth_stage, b.bush_age_yrs, b.worker_capacity,
               ft.code AS last_fertilizer_type,
               EXTRACT(DAY FROM NOW() - MAX(fa.application_date))::INT AS days_since_fertilized
        FROM block b
        LEFT JOIN fertilizer_application fa ON fa.block_id = b.id
        LEFT JOIN fertilizer_type ft ON ft.id = fa.fertilizer_type_id
        WHERE b.estate_id = %s
        GROUP BY b.id, b.block_code, b.zone, b.elevation_m, b.area_hectares,
                 b.soil_type, b.growth_stage, b.bush_age_yrs, b.worker_capacity, ft.code
        ORDER BY b.block_code
    """, (estate_id,))
    blocks = cur.fetchall()
    print(f"DEBUG: blocks found = {len(blocks)}")

    # Fetch estate weather for this month
    cur.execute("""
        SELECT rainfall_mm, avg_temp_c, avg_humidity_pct
        FROM estate_weather
        WHERE estate_id = %s AND year = %s AND month = %s
    """, (estate_id, year, month))
    weather_row = cur.fetchone()
    weather = {
        "rainfall_mm": float(weather_row[0]) if weather_row else 185.0,
        "avg_temp_c": float(weather_row[1]) if weather_row else 22.4,
        "avg_humidity_pct": float(weather_row[2]) if weather_row else 78.0,
    }

    # Build FastAPI payload
    blocks_payload = []
    block_meta = {}

    for row in blocks:
        (block_id, block_code, zone, elevation_m, area_hectares,
         soil_type, growth_stage, bush_age_yrs, worker_capacity,
         last_fertilizer_type, days_since_fertilized) = row

        # Get last month's yield
        cur.execute("""
            SELECT yield_kg FROM block_yield_record
            WHERE block_id = %s AND (year * 12 + month) < (%s * 12 + %s)
            ORDER BY year DESC, month DESC LIMIT 1
        """, (block_id, year, month))
        last_yield_row = cur.fetchone()
        yield_last_month = float(last_yield_row[0]) if last_yield_row else None

        # Get history for fallback
        cur.execute("""
            SELECT year, month, yield_kg FROM block_yield_record
            WHERE block_id = %s ORDER BY year, month
        """, (block_id,))

        history = cur.fetchall()

        block_meta[str(block_id)] = {
            "worker_capacity": worker_capacity or 15,
            "history": history,
            "block_code": block_code,
        }

        blocks_payload.append({
            "block_id": str(block_id),
            "zone": zone or "Mid",
            "elevation_m": int(elevation_m) if elevation_m else 900,
            "area_hectares": float(area_hectares) if area_hectares else 2.0,
            "soil_type": soil_type or "Laterite",
            "growth_stage": growth_stage or "Mature",
            "bush_age_yrs": int(bush_age_yrs) if bush_age_yrs else 20,
            "rainfall_mm": weather["rainfall_mm"],
            "avg_temp_c": weather["avg_temp_c"],
            "avg_humidity_pct": weather["avg_humidity_pct"],
            "days_since_fertilized": int(days_since_fertilized) if days_since_fertilized else 45,
            "last_fertilizer_type": last_fertilizer_type or "EP_GOLD",
            "yield_last_month": yield_last_month,
        })

    # Try FastAPI first
    ml_predictions = _call_fastapi(blocks_payload, year, month)
    used_ml = ml_predictions is not None

    if used_ml:
        pred_map = {p["block_id"]: p for p in ml_predictions}
        logger.info("Using XGBoost ML model for %d blocks", len(blocks))
    else:
        logger.warning("FastAPI unavailable — using heuristic fallback")

    # Upsert predictions
    predictions = {}
    for bp in blocks_payload:
        block_id = bp["block_id"]
        meta = block_meta[block_id]

        if used_ml and block_id in pred_map:
            p = pred_map[block_id]
            predicted = round(float(p["predicted_yield_kg"]), 3)
            low = round(float(p["confidence_low"]), 3)
            high = round(float(p["confidence_high"]), 3)
            version = MODEL_VERSION
        else:
            predicted = _heuristic_forecast(
                meta["history"], meta["worker_capacity"], year, month
            )
            low = round(predicted * (1 - CONFIDENCE_BAND), 3)
            high = round(predicted * (1 + CONFIDENCE_BAND), 3)
            version = FALLBACK_MODEL_VERSION

        cur.execute("""
            INSERT INTO yield_prediction
                (block_id, year, month, predicted_yield_kg,
                 confidence_low, confidence_high, model_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (block_id, year, month) DO UPDATE SET
                predicted_yield_kg = EXCLUDED.predicted_yield_kg,
                confidence_low     = EXCLUDED.confidence_low,
                confidence_high    = EXCLUDED.confidence_high,
                model_version      = EXCLUDED.model_version,
                created_at         = NOW()
        """, (block_id, year, month, predicted, low, high, version))

        predictions[block_id] = predicted

    logger.info("Computed %d predictions for estate %s (%d-%02d) using %s",
                len(predictions), estate_id, year, month,
                "ML model" if used_ml else "heuristic fallback")
    return predictions


# =============================================================================
# API Endpoint: GET /labour/predictions
# =============================================================================

@predictions_bp.route('/labour/predictions', methods=['GET'])
@token_required
def get_predictions():
    """
    GET /labour/predictions?estate_id=&year=&month=
    Returns stored predictions from yield_prediction table.
    If none exist, triggers computation first.
    """
    estate_id = request.args.get('estate_id')
    year = int(request.args.get('year', 2026))
    month = int(request.args.get('month', 6))

    if not estate_id:
        return jsonify({'error': 'estate_id is required'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database unavailable'}), 503

    try:
        with conn.cursor() as cur:
            # Check if predictions exist
            cur.execute("""
                SELECT yp.id, b.block_code, yp.predicted_yield_kg,
                       yp.confidence_low, yp.confidence_high, yp.model_version
                FROM yield_prediction yp
                JOIN block b ON b.id = yp.block_id
                WHERE b.estate_id = %s AND yp.year = %s AND yp.month = %s
                ORDER BY b.block_code
            """, (estate_id, year, month))
            rows = cur.fetchall()
            print(f"DEBUG: rows={len(rows)} estate={estate_id} year={year} month={month}")
            logger.info("Existing rows: %d for estate %s year %s month %s", len(rows), estate_id, year, month)

            # If no predictions exist, compute them now
            if not rows:
                logger.info("No predictions found — computing now")
                compute_block_predictions(cur, estate_id, year, month)
                conn.commit()

                cur.execute("""
                    SELECT yp.id, b.block_code, yp.predicted_yield_kg,
                           yp.confidence_low, yp.confidence_high, yp.model_version
                    FROM yield_prediction yp
                    JOIN block b ON b.id = yp.block_id
                    WHERE b.estate_id = %s AND yp.year = %s AND yp.month = %s
                    ORDER BY b.block_code
                """, (estate_id, year, month))
                rows = cur.fetchall()
                print(f"DEBUG: rows={len(rows)} estate={estate_id} year={year} month={month}")

            result = []
            for row in rows:
                pred_id, block_code, predicted, low, high, version = row
                result.append({
                    "block_id": str(pred_id),
                    "block_code": block_code,
                    "predicted_yield_kg": float(predicted),
                    "confidence_low": float(low),
                    "confidence_high": float(high),
                    "model_version": version,
                })

            return jsonify(result), 200

    except Exception as e:
        conn.rollback()
        logger.error("Predictions error: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()