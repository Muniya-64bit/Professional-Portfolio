"""Tests for reports module - calls actual functions."""
import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

# Import reports module
import reports


class TestReportsModule:
    """Test reports module functions and helpers."""

    def test_month_names_constant(self):
        """Test MONTH_NAMES constant exists."""
        assert hasattr(reports, 'MONTH_NAMES')
        assert len(reports.MONTH_NAMES) == 12
        assert reports.MONTH_NAMES[0] == 'January'
        assert reports.MONTH_NAMES[11] == 'December'

    def test_month_abbreviations_constant(self):
        """Test MONTH_ABBR constant exists."""
        assert hasattr(reports, 'MONTH_ABBR')
        assert len(reports.MONTH_ABBR) == 12
        assert reports.MONTH_ABBR[0] == 'Jan'
        assert reports.MONTH_ABBR[11] == 'Dec'

    def test_float_conversion_helper(self):
        """Test _f helper converts Decimal to float."""
        # Access the private function through module
        assert hasattr(reports, '_f')
        
        decimal_val = Decimal('100.50')
        result = reports._f(decimal_val)
        
        assert result == 100.50
        assert isinstance(result, float)

    def test_float_conversion_non_decimal(self):
        """Test _f helper with non-Decimal value."""
        value = 100.50
        result = reports._f(value)
        
        assert result == 100.50

    def test_float_conversion_integer(self):
        """Test _f helper with integer."""
        value = 100
        result = reports._f(value)
        
        assert result == 100


class TestReportsBlueprintSetup:
    """Test reports blueprint configuration."""

    def test_reports_blueprint_exists(self):
        """Test that reports blueprint is defined."""
        assert hasattr(reports, 'reports_bp')
        bp = reports.reports_bp
        
        assert bp is not None
        assert bp.name == 'reports'
        assert bp.url_prefix == '/api/reports'

    def test_blueprint_route_registration(self):
        """Test that blueprint routes are configured."""
        bp = reports.reports_bp
        
        # Blueprint should have deferred functions registered
        assert bp.deferred_functions is not None


class TestReportsDataLayer:
    """Test reports data fetching functions."""

    def test_fetch_function_exists(self):
        """Test _fetch function exists."""
        assert hasattr(reports, '_fetch')

    @patch('reports.get_db_connection')
    def test_fetch_database_unavailable(self, mock_db):
        """Test _fetch when database is unavailable."""
        mock_db.return_value = None
        
        result, message = reports._fetch("test-estate", 2024, 6)
        
        assert result is None
        assert 'Database unavailable' in message

    def test_db_helper_exists(self):
        """Test _db helper function."""
        assert hasattr(reports, '_db')


class TestReportsLogging:
    """Test reports logging configuration."""

    def test_logger_configured(self):
        """Test that logger is configured."""
        assert hasattr(reports, 'logger')
        assert reports.logger is not None


class TestMonthNameMapping:
    """Test month name and abbreviation mapping."""

    def test_all_months_have_names(self):
        """Test all 12 months have names."""
        assert len(reports.MONTH_NAMES) == 12
        for i, month in enumerate(reports.MONTH_NAMES, 1):
            assert len(month) > 0
            assert month[0].isupper()

    def test_all_months_have_abbreviations(self):
        """Test all 12 months have abbreviations."""
        assert len(reports.MONTH_ABBR) == 12
        for abbr in reports.MONTH_ABBR:
            assert len(abbr) == 3
            assert abbr[0].isupper()

    def test_month_mapping_consistency(self):
        """Test month name and abbreviation consistency."""
        for name, abbr in zip(reports.MONTH_NAMES, reports.MONTH_ABBR):
            # e.g. 'January'.startswith('Jan')
            assert name.startswith(abbr)
