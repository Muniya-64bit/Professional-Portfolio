"""Tests for scheduler module."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

import scheduler


class TestSchedulerModule:
    """Test scheduler module constants and functions."""

    def test_scheduler_importable(self):
        """Scheduler module can be imported."""
        assert scheduler is not None

    def test_scheduler_has_start_scheduler(self):
        """start_scheduler function is available."""
        assert hasattr(scheduler, 'start_scheduler')
        assert callable(scheduler.start_scheduler)

    def test_scheduler_has_run_monthly_job(self):
        """_run_monthly_job function is available."""
        assert hasattr(scheduler, '_run_monthly_job')

    def test_scheduler_global_initially_none(self):
        """_scheduler global starts as None (or already started in tests)."""
        # Just verify the attribute exists
        assert hasattr(scheduler, '_scheduler')

    @patch('scheduler.generate_monthly_plans')
    @patch('scheduler._next_month')
    def test_run_monthly_job_success(self, mock_next_month, mock_gen):
        """_run_monthly_job calls generate_monthly_plans."""
        mock_next_month.return_value = date(2024, 7, 1)
        mock_gen.return_value = ({'plans_created': 3}, 200)

        # Should not raise
        scheduler._run_monthly_job()

        mock_gen.assert_called_once_with(2024, 7)

    @patch('scheduler.generate_monthly_plans')
    @patch('scheduler._next_month')
    def test_run_monthly_job_handles_exception(self, mock_next_month, mock_gen):
        """_run_monthly_job handles generate_monthly_plans raising an exception."""
        mock_next_month.return_value = date(2024, 7, 1)
        mock_gen.side_effect = Exception("DB error")

        # Should not raise (exception is caught internally)
        scheduler._run_monthly_job()

    @patch('scheduler.BackgroundScheduler')
    def test_start_scheduler_creates_scheduler(self, mock_bg):
        """start_scheduler creates a BackgroundScheduler when not already started."""
        # Reset global
        scheduler._scheduler = None

        mock_instance = MagicMock()
        mock_bg.return_value = mock_instance

        result = scheduler.start_scheduler()

        assert result is mock_instance
        mock_instance.add_job.assert_called_once()
        mock_instance.start.assert_called_once()

    @patch('scheduler.BackgroundScheduler')
    def test_start_scheduler_idempotent(self, mock_bg):
        """start_scheduler is idempotent - returns existing scheduler."""
        existing = MagicMock()
        scheduler._scheduler = existing

        result = scheduler.start_scheduler()

        assert result is existing
        mock_bg.assert_not_called()  # Should not create a new one

        # Clean up
        scheduler._scheduler = None
