"""Fixtures for unit tests."""
import pytest
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / 'backend'
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Load environment
env_file = Path(__file__).parent.parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)


@pytest.fixture
def mock_user_data():
    """Fixture for mock user data."""
    return {
        'email': 'test@example.com',
        'password': 'TestPassword123!',
        'full_name': 'Test User',
        'role': 'manager',
        'estate_id': 'test-estate-id',
    }


@pytest.fixture
def mock_roi_data():
    """Fixture for mock ROI data."""
    return {
        'estate_id': 'estate-123',
        'year': 2024,
        'month': 6,
        'cost_per_kg': 12.50,
        'yield_kg': 500,
        'total_cost': 6250,
        'rank': 5,
        'is_flagged': False,
        'flag_reason': None,
    }


@pytest.fixture
def mock_labor_data():
    """Fixture for mock labor data."""
    return {
        'estate_id': 'estate-123',
        'date': '2024-06-15',
        'worker_count': 10,
        'daily_wage_lkr': 1200.00,
        'total_cost': 12000.00,
        'hours_worked': 8,
        'work_type': 'Harvesting',
    }


@pytest.fixture
def mock_water_data():
    """Fixture for mock water data."""
    return {
        'estate_id': 'estate-123',
        'date': '2024-06-15',
        'volume_liters': 5000,
        'cost_lkr': 2500.00,
        'method': 'Drip Irrigation',
        'purpose': 'Irrigation',
    }


@pytest.fixture
def mock_input_cost_data():
    """Fixture for mock input cost data."""
    return {
        'estate_id': 'estate-123',
        'month': 6,
        'year': 2024,
        'fertilizer_cost': 5000.00,
        'pesticide_cost': 2000.00,
        'seed_cost': 1000.00,
        'other_cost': 500.00,
        'total_cost': 8500.00,
    }


@pytest.fixture
def mock_yield_data():
    """Fixture for mock yield data."""
    return {
        'estate_id': 'estate-123',
        'harvest_date': '2024-06-15',
        'yield_kg': 500,
        'area_hectares': 2,
        'yield_per_hectare': 250,
        'quality_grade': 'A',
    }
