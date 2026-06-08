"""
Unit tests for predictions.py — heuristic yield forecasting.
No DB calls needed; _forecast() is a pure function.
compute_block_predictions() is tested with a mock cursor.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')

from predictions import (
    _forecast, compute_block_predictions,
    FALLBACK_KG_PER_WORKER, CONFIDENCE_BAND, MODEL_VERSION, RECENT_WINDOW,
)


# ═════════════════════════════════════════════════════════════════════════════
# _forecast() — pure unit tests
# ═════════════════════════════════════════════════════════════════════════════

class TestForecast:
    def test_no_history_uses_fallback(self):
        predicted, used_fallback = _forecast([], worker_capacity=10, year=2025, month=6)
        assert used_fallback is True
        assert predicted == round(10 * FALLBACK_KG_PER_WORKER, 3)

    def test_same_month_last_year_used_preferentially(self):
        history = [
            (2024, 6, 5000.0),   # same month last year → should be used
            (2024, 5, 4000.0),
            (2024, 4, 3000.0),
        ]
        predicted, used_fallback = _forecast(history, worker_capacity=15, year=2025, month=6)
        assert used_fallback is False
        assert predicted == 5000.0

    def test_falls_back_to_recent_mean_when_no_same_month(self):
        # 6 recent months, no entry for last year's same month
        history = [(2024, m, 3000.0) for m in range(1, 7)]
        predicted, used_fallback = _forecast(history, worker_capacity=15, year=2025, month=8)
        assert used_fallback is False
        # base = mean of last 6 = 3000, trend from last two consecutive = 0
        assert predicted == 3000.0

    def test_trend_applied_correctly(self):
        # Last two records: 4000 then 5000 → trend = +1000
        history = [
            (2024, 1, 3000.0),
            (2024, 2, 4000.0),
            (2024, 3, 5000.0),
        ]
        predicted, used_fallback = _forecast(history, worker_capacity=15, year=2025, month=7)
        assert used_fallback is False
        # mean of recent (up to 6) = (3000+4000+5000)/3 = 4000, trend = +1000
        assert predicted == 5000.0

    def test_negative_trend_clamps_to_zero(self):
        # Declining history that would produce negative prediction
        history = [(2024, i, max(100.0 - i * 90, 0)) for i in range(1, 4)]
        # values: 10, 0 (would go negative) — ensure no negative output
        # actual: [10, 0, ... depends on formula] let's use a clear case
        history = [
            (2024, 1, 200.0),
            (2024, 2, 100.0),
            (2024, 3, 0.0),
        ]
        predicted, _ = _forecast(history, worker_capacity=5, year=2025, month=9)
        assert predicted >= 0.0

    def test_single_history_entry_no_trend(self):
        history = [(2023, 3, 2500.0)]
        predicted, used_fallback = _forecast(history, worker_capacity=10, year=2025, month=5)
        assert used_fallback is False
        assert predicted == 2500.0

    def test_fallback_scales_with_capacity(self):
        p1, _ = _forecast([], 5, 2025, 1)
        p2, _ = _forecast([], 10, 2025, 1)
        assert p2 == 2 * p1

    def test_result_is_rounded_to_3_decimal_places(self):
        history = [(2024, 6, 1000.1234567)]
        predicted, _ = _forecast(history, 15, 2025, 6)
        # check rounding
        assert predicted == round(predicted, 3)

    def test_recent_window_limits_history_used(self):
        # More than RECENT_WINDOW entries; only last RECENT_WINDOW matter
        history = [(2020 + i, 1, float(i * 100)) for i in range(10)]
        predicted, used_fallback = _forecast(history, 15, 2025, 3)
        assert used_fallback is False
        # Mean of last RECENT_WINDOW values
        recent_vals = [float(i * 100) for i in range(10 - RECENT_WINDOW, 10)]
        expected_base = sum(recent_vals) / len(recent_vals)
        trend = recent_vals[-1] - recent_vals[-2]
        expected = max(0.0, expected_base + trend)
        assert predicted == round(expected, 3)


# ═════════════════════════════════════════════════════════════════════════════
# compute_block_predictions() — integration with mock cursor
# ═════════════════════════════════════════════════════════════════════════════

class TestComputeBlockPredictions:
    def _make_cursor(self, blocks, yield_history=None):
        """Build a cursor mock that returns blocks then yield_history on successive calls."""
        cur = MagicMock()
        yield_history = yield_history or []

        call_count = [0]

        def fetchall_side_effect():
            c = call_count[0]
            call_count[0] += 1
            if c == 0:
                return blocks
            # Each subsequent call returns history for that block
            idx = c - 1
            if idx < len(yield_history):
                return yield_history[idx]
            return []

        cur.fetchall.side_effect = fetchall_side_effect
        return cur

    def test_returns_dict_of_block_predictions(self):
        import uuid
        b1 = (uuid.uuid4(), 15)
        cur = self._make_cursor(blocks=[b1], yield_history=[[]])
        result = compute_block_predictions(cur, 'estate-1', 2025, 6)
        assert isinstance(result, dict)
        assert len(result) == 1

    def test_no_blocks_returns_empty(self):
        cur = self._make_cursor(blocks=[], yield_history=[])
        result = compute_block_predictions(cur, 'estate-x', 2025, 6)
        assert result == {}

    def test_fallback_used_when_no_history(self):
        import uuid
        b1_id = uuid.uuid4()
        capacity = 10
        cur = self._make_cursor(blocks=[(b1_id, capacity)], yield_history=[[]])
        result = compute_block_predictions(cur, 'estate-1', 2025, 6)
        expected = round(capacity * FALLBACK_KG_PER_WORKER, 3)
        assert result[str(b1_id)] == expected

    def test_none_capacity_defaults_to_15(self):
        import uuid
        b1_id = uuid.uuid4()
        cur = self._make_cursor(blocks=[(b1_id, None)], yield_history=[[]])
        result = compute_block_predictions(cur, 'estate-1', 2025, 6)
        expected = round(15 * FALLBACK_KG_PER_WORKER, 3)
        assert result[str(b1_id)] == expected

    def test_insert_called_per_block(self):
        import uuid
        blocks = [(uuid.uuid4(), 15), (uuid.uuid4(), 12)]
        cur = self._make_cursor(blocks=blocks, yield_history=[[], []])
        compute_block_predictions(cur, 'estate-2', 2025, 6)
        # execute called: 1 (blocks query) + 2 (history queries) + 2 (inserts) = 5
        assert cur.execute.call_count == 5

    def test_confidence_band_applied(self):
        """The upsert INSERT should include confidence low/high derived from CONFIDENCE_BAND."""
        import uuid
        b1_id = uuid.uuid4()
        history = [(2024, 6, 1000.0)]  # same month last year → 1000.0
        cur = self._make_cursor(blocks=[(b1_id, 15)], yield_history=[history])
        compute_block_predictions(cur, 'estate-1', 2025, 6)

        # Find the INSERT call (the one that mentions yield_prediction)
        insert_call_args = None
        for c in cur.execute.call_args_list:
            args = c[0]
            if 'yield_prediction' in str(args[0]):
                insert_call_args = args
                break

        assert insert_call_args is not None
        params = insert_call_args[1]
        predicted = params[3]
        low = params[4]
        high = params[5]
        assert low == round(predicted * (1 - CONFIDENCE_BAND), 3)
        assert high == round(predicted * (1 + CONFIDENCE_BAND), 3)
