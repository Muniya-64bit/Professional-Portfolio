# Backend Test Suite

This directory contains comprehensive unit and integration tests for the backend application.

## Structure

```
tests/
├── unit/                          # Unit tests
│   ├── test_auth.py              # Authentication tests
│   ├── test_validation.py        # Data validation tests
│   ├── test_calculations.py      # Calculation logic tests
│   ├── test_roi.py               # ROI calculation tests
│   └── conftest.py               # Unit test fixtures
├── integration/                   # Integration tests
│   ├── test_api_endpoints.py     # API endpoint tests
│   └── conftest.py               # Integration test fixtures
├── requirements-test.txt         # Test dependencies
├── conftest.py                   # Global test configuration
└── README.md                     # This file
```

## Test Coverage

### Unit Tests

#### `test_auth.py`
- Password hashing and verification
- Password strength validation
- JWT token generation and verification
- Token blacklist functionality

#### `test_validation.py`
- Email validation
- UUID validation
- Date range validation
- Numeric precision
- String format validation
- DateTime validation

#### `test_calculations.py`
- Labor cost calculations (daily, hourly, overtime)
- Labor productivity metrics
- Water usage calculations
- Water cost calculations
- Water efficiency metrics
- Yield calculations
- Estate-level metrics and comparisons

#### `test_roi.py`
- Cost per kg calculations
- ROI profitability calculations
- Monthly trend analysis
- Estate ranking and comparison
- Year-over-year comparisons
- Quartile calculations

### Integration Tests

#### `test_api_endpoints.py`
- Health check endpoints
- Public estates endpoint
- Authentication endpoints (signup, login)
- ROI endpoints
- Estate management endpoints
- Report generation endpoints
- Error handling (404, 405, 400)
- CORS headers
- Pagination
- Rate limiting

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -r tests/requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_roi.py -v

# Run specific test class
pytest tests/unit/test_roi.py::TestROICalculations -v

# Run specific test function
pytest tests/unit/test_roi.py::TestROICalculations::test_cost_per_kg_basic_calculation -v
```

### Run Tests with Coverage Report

```bash
pytest --cov=backend --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run Tests with Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run all except slow tests
pytest -m "not slow"
```

### Run Tests in Verbose Mode

```bash
pytest -v
```

### Run Tests with Detailed Output

```bash
pytest -v --tb=long
```

### Run Tests Matching a Pattern

```bash
pytest -k "auth"  # Runs all tests with "auth" in the name
```

## Test Configuration

### pytest.ini

The `pytest.ini` file contains configuration for:
- Test discovery patterns
- Test paths and Python path
- Output options (verbosity, coverage)
- Test markers
- Logging configuration
- Timeout settings

### conftest.py

Global fixtures and configuration:
- Backend path setup
- Environment variable loading
- Shared fixtures

### unit/conftest.py

Unit test fixtures:
- Mock user data
- Mock ROI data
- Mock labor data
- Mock water data
- Mock input cost data
- Mock yield data

### integration/conftest.py

Integration test fixtures:
- Flask app context
- Test client
- CLI runner
- Authentication headers
- Sample IDs

## Best Practices

### Writing Tests

1. **Test Naming**: Use descriptive names that indicate what is being tested
   ```python
   def test_cost_per_kg_basic_calculation(self):
   ```

2. **Test Organization**: Group related tests in classes
   ```python
   class TestROICalculations:
       def test_cost_per_kg_basic_calculation(self):
           ...
   ```

3. **Use Fixtures**: Leverage pytest fixtures for setup/teardown
   ```python
   def test_something(self, mock_roi_data):
       assert mock_roi_data['cost_per_kg'] == 12.50
   ```

4. **Test One Thing**: Each test should verify a single behavior
   ```python
   def test_cost_per_kg_basic_calculation(self):
       total_cost = 1000.00
       yield_kg = 100.00
       cost_per_kg = total_cost / yield_kg
       assert cost_per_kg == 10.00
   ```

5. **Use Meaningful Assertions**: Make assertions clear and specific
   ```python
   assert response.status_code == 200
   assert 'email' in data.get('error', '').lower()
   ```

### Test Markers

Mark tests for categorization:

```python
@pytest.mark.unit
def test_something():
    ...

@pytest.mark.integration
def test_api_endpoint():
    ...

@pytest.mark.slow
def test_long_running():
    ...
```

## Environment Setup

### Test Environment Variables

Create a `.env.test` file (optional) with test-specific settings:

```
DATABASE_URL=postgresql://user:password@localhost/kvpl_db_test
SECRET_KEY=test-secret-key
TESTING=True
```

If `.env.test` doesn't exist, tests use `.env` with `kvpl_db` replaced by `kvpl_db_test`.

## Troubleshooting

### Import Errors

If you get import errors, ensure:
1. Backend path is in `sys.path` (handled by conftest.py)
2. `.env` file exists in project root
3. Backend dependencies are installed

### Database Errors

For integration tests:
1. Ensure PostgreSQL is running
2. Test database exists or can be created
3. DATABASE_URL in `.env` is correct

### Fixture Not Found

Ensure fixtures are defined in the appropriate `conftest.py`:
- Global fixtures → `tests/conftest.py`
- Unit fixtures → `tests/unit/conftest.py`
- Integration fixtures → `tests/integration/conftest.py`

## Continuous Integration

Tests can be run in CI/CD pipelines:

```bash
# Run all tests with coverage
pytest --cov=backend --cov-report=xml

# Run with specific markers
pytest -m unit -v

# Generate JUnit XML for CI systems
pytest --junit-xml=test-results.xml
```

## Contributing Tests

When adding new features:

1. Write tests first (TDD)
2. Place unit tests in `tests/unit/`
3. Place integration tests in `tests/integration/`
4. Use appropriate fixtures
5. Add docstrings to test functions
6. Ensure tests are independent
7. Run full test suite before committing

```bash
pytest -v --cov=backend
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/testing/)
- [pytest-flask Documentation](https://pytest-flask.readthedocs.io/)
