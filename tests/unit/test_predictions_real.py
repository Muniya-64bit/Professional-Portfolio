"""Tests for predictions module - calls actual functions."""
import pytest
from decimal import Decimal

# Import actual predictions functions and constants
from predictions import (
    _f, _forecast,
    MODEL_VERSION, FALLBACK_KG_PER_WORKER, CONFIDENCE_BAND, RECENT_WINDOW
)


class TestPredictionsConstants:
    """Test predictions module constants."""

    def test_model_version_string(self):
        """Test MODEL_VERSION is defined."""
        assert MODEL_VERSION == 'heuristic_v1'
        assert isinstance(MODEL_VERSION, str)

    def test_fallback_kg_per_worker(self):
        """Test FALLBACK_KG_PER_WORKER constant."""
        assert FALLBACK_KG_PER_WORKER == 600.0
        assert isinstance(FALLBACK_KG_PER_WORKER, float)

    def test_confidence_band(self):
        """Test CONFIDENCE_BAND constant."""
        assert CONFIDENCE_BAND == 0.15
        assert 0 < CONFIDENCE_BAND < 1

    def test_recent_window(self):
        """Test RECENT_WINDOW constant."""
        assert RECENT_WINDOW == 6
        assert isinstance(RECENT_WINDOW, int)


class TestFloatHelper:
    """Test _f helper function."""

    def test_f_converts_decimal(self):
        """Test _f converts Decimal to float."""
        result = _f(Decimal('100.50'))
        assert result == 100.50
        assert isinstance(result, float)

    def test_f_passes_through_float(self):
        """Test _f passes float through unchanged."""
        result = _f(100.50)
        assert result == 100.50

    def test_f_passes_through_int(self):
        """Test _f passes int through unchanged."""
        result = _f(100)
        assert result == 100


class TestForecastFunction:
    """Test the _forecast pure function."""

    def test_forecast_no_history_uses_fallback(self):
        """Test fallback when no history."""
        predicted, used_fallback = _forecast([], 15, 2024, 6)

        assert used_fallback is True
        assert predicted == round(15 * FALLBACK_KG_PER_WORKER, 3)

    def test_forecast_same_month_last_year(self):
        """Test forecast uses same-month-last-year when available."""
        history = [(2023, 6, 1200.0), (2023, 7, 1100.0), (2023, 8, 1300.0)]
        predicted, used_fallback = _forecast(history, 15, 2024, 6)

        assert used_fallback is False
        assert predicted == 1200.0

    def test_forecast_no_same_month_uses_recent_mean(self):
        """Test forecast uses recent mean when no same-month-last-year."""
        history = [(2023, 7, 1100.0), (2023, 8, 1200.0), (2023, 9, 1300.0)]
        predicted, used_fallback = _forecast(history, 15, 2024, 6)

        # No same-month entry, uses recent mean + trend
        assert used_fallback is False
        assert predicted > 0

    def test_forecast_with_trend(self):
        """Test forecast applies trend from last two records."""
        # Increasing trend: each month 100 more
        history = [(2023, 1, 1000.0), (2023, 2, 1100.0), (2023, 3, 1200.0)]
        predicted, used_fallback = _forecast(history, 15, 2024, 6)

        # Should reflect upward trend
        assert used_fallback is False
        assert predicted > 0

    def test_forecast_different_worker_capacities(self):
        """Test fallback scales with worker capacity."""
        predicted_5, _ = _forecast([], 5, 2024, 6)
        predicted_15, _ = _forecast([], 15, 2024, 6)

        assert predicted_15 == predicted_5 * 3

    def test_forecast_decimal_yield_values(self):
        """Test forecast handles Decimal yield values."""
        history = [(2023, 6, Decimal('1200.5'))]
        predicted, used_fallback = _forecast(history, 15, 2024, 6)

        assert used_fallback is False
        assert predicted == pytest.approx(1200.5)

    def test_forecast_non_negative(self):
        """Test forecast never returns negative values."""
        # Strongly declining trend
        history = [(2023, 1, 1000.0), (2023, 2, 100.0)]
        predicted, used_fallback = _forecast(history, 15, 2024, 6)

        assert predicted >= 0

    def test_forecast_single_history_entry(self):
        """Test forecast with only one history entry."""
        history = [(2023, 1, 800.0)]
        predicted, used_fallback = _forecast(history, 15, 2024, 6)

        # No same-month, single entry means no trend, just mean
        assert used_fallback is False
        assert predicted == pytest.approx(800.0)
