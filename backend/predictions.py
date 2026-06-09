"""Heuristic monthly yield prediction for the labour planner.

There is no trained ML model in the repo yet; the ``yield_prediction`` table is
populated by this lightweight forecaster, derived from the block's historical
``block_yield_record`` rows. It is intentionally simple and deterministic so the
monthly labour generator always has an expected yield per block to plan around.

When a block has no history we fall back to ``worker_capacity * 600`` — the same
constant the planner used before predictions existed — so a plan is never empty.
"""
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

MODEL_VERSION = 'heuristic_v1'
FALLBACK_KG_PER_WORKER = 600.0   # legacy constant: capacity * 600
CONFIDENCE_BAND = 0.15           # ±15% interval
RECENT_WINDOW = 6                # months averaged when no same-month-last-year


def _f(v):
    return float(v) if isinstance(v, Decimal) else v


def _forecast(history, worker_capacity, year, month):
    """Return (predicted_kg, used_fallback) for one block.

    history: list of (year, month, yield_kg) sorted ascending.
    Strategy:
      1. Prefer the same month last year (strong seasonal signal for tea).
      2. Else mean of the most recent RECENT_WINDOW records, nudged by the
         month-over-month trend of the last two records.
      3. Else fall back to capacity * 600.
    """
    if not history:
        return round(worker_capacity * FALLBACK_KG_PER_WORKER, 3), True

    same_month_last_year = next(
        (y for (yr, mo, y) in history if yr == year - 1 and mo == month), None
    )
    if same_month_last_year is not None:
        return round(_f(same_month_last_year), 3), False

    recent = [_f(y) for (_, _, y) in history[-RECENT_WINDOW:]]
    base = sum(recent) / len(recent)

    # light linear trend from the last two consecutive records
    trend = 0.0
    if len(recent) >= 2:
        trend = recent[-1] - recent[-2]

    predicted = max(0.0, base + trend)
    return round(predicted, 3), False


def compute_block_predictions(cur, estate_id, year, month):
    """Compute + upsert yield predictions for every block of an estate.

    Writes one row per block into ``yield_prediction`` (upsert on
    block_id/year/month) and returns ``{ block_id(str): predicted_yield_kg }``.

    The caller owns the transaction (we do not commit here).
    """
    cur.execute(
        "SELECT id, worker_capacity FROM block WHERE estate_id = %s ORDER BY block_code",
        (estate_id,),
    )
    blocks = cur.fetchall()

    predictions = {}
    for block_id, worker_capacity in blocks:
        # Only use history STRICTLY BEFORE the target month — a forecast must
        # not peek at the month it is predicting (or any later actuals), or a
        # stray same-month record skews the trend and zeroes the prediction.
        cur.execute(
            """
            SELECT year, month, yield_kg
            FROM block_yield_record
            WHERE block_id = %s
              AND (year < %s OR (year = %s AND month < %s))
            ORDER BY year, month
            """,
            (block_id, year, year, month),
        )
        history = cur.fetchall()

        predicted, used_fallback = _forecast(
            history, worker_capacity or 15, year, month
        )
        low = round(predicted * (1 - CONFIDENCE_BAND), 3)
        high = round(predicted * (1 + CONFIDENCE_BAND), 3)

        cur.execute(
            """
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
            """,
            (block_id, year, month, predicted, low, high,
             MODEL_VERSION + ('_fallback' if used_fallback else '')),
        )
        predictions[str(block_id)] = predicted

    logger.info(
        "Computed %d block predictions for estate %s (%d-%02d)",
        len(predictions), estate_id, year, month,
    )
    return predictions
