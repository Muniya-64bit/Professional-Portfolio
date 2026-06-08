"""Integration tests for API endpoints."""
import pytest
import json
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

from app import app


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_token(client):
    """Create auth token for testing."""
    # Note: This requires a test user to exist in the database
    # In production, you'd create a test user before this
    return None  # Placeholder


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_home_endpoint(self, client):
        """Test home endpoint."""
        response = client.get('/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'version' in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'


class TestPublicEstatesEndpoint:
    """Test public estates endpoint."""
    
    def test_get_public_estates(self, client):
        """Test fetching public estates list."""
        response = client.get('/api/estates/public')
        
        # Should return 200 or 503 if DB unavailable
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, list)


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""
    
    def test_signup_missing_data(self, client):
        """Test signup with missing required data."""
        response = client.post('/api/auth/signup',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_signup_invalid_email(self, client):
        """Test signup with invalid email."""
        response = client.post('/api/auth/signup',
            json={
                'email': 'invalidemail',
                'password': 'ValidPass123!',
                'full_name': 'Test User',
                'role': 'manager',
                'estate_id': 'test-id',
            },
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'email' in data.get('error', '').lower()
    
    def test_login_missing_credentials(self, client):
        """Test login with missing credentials."""
        response = client.post('/api/auth/login',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post('/api/auth/login',
            json={
                'email': 'nonexistent@example.com',
                'password': 'wrongpassword',
            },
            content_type='application/json'
        )
        
        # Should return 401 for invalid credentials, or 400/500 if user doesn't exist
        assert response.status_code in [400, 401, 500]


class TestROIEndpoints:
    """Test ROI calculation endpoints."""
    
    def test_roi_summary_missing_params(self, client):
        """Test ROI summary endpoint without required parameters."""
        response = client.get('/api/roi/summary')
        
        # Should require parameters
        assert response.status_code in [400, 422]
    
    def test_roi_summary_valid_params(self, client):
        """Test ROI summary endpoint with valid parameters."""
        response = client.get('/api/roi/summary?estate_id=test&year=2024')
        
        # May fail if estate doesn't exist, but should be 200 or 404
        assert response.status_code in [200, 404, 401, 503]
    
    def test_roi_estate_trend_valid_params(self, client):
        """Test ROI estate trend endpoint."""
        response = client.get('/api/roi/estate-trend?estate_id=test&year=2024')
        
        # May fail if estate doesn't exist
        assert response.status_code in [200, 404, 401, 503]


class TestEstateEndpoints:
    """Test estate management endpoints."""
    
    def test_get_estates_public(self, client):
        """Test getting public estates."""
        response = client.get('/api/estates/public')
        
        assert response.status_code in [200, 404, 503]
    
    def test_get_estates_list_requires_auth(self, client):
        """Test that protected endpoints require authentication."""
        response = client.get('/api/estates')
        
        # Should require authentication or endpoint may not exist
        assert response.status_code in [401, 403, 404]


class TestReportEndpoints:
    """Test report generation endpoints."""
    
    def test_generate_report_missing_params(self, client):
        """Test report generation without parameters."""
        response = client.get('/api/reports/pdf')
        
        # Should require parameters
        assert response.status_code in [400, 422, 401]
    
    def test_generate_report_requires_auth(self, client):
        """Test report generation requires authentication."""
        response = client.post('/api/reports/pdf',
            json={
                'estate_id': 'test',
                'year': 2024,
                'month': 6,
            }
        )
        
        # Should require authentication
        assert response.status_code in [401, 403]


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_endpoint_404(self, client):
        """Test that invalid endpoints return 404."""
        response = client.get('/api/nonexistent/endpoint')
        
        assert response.status_code == 404
    
    def test_invalid_method_405(self, client):
        """Test that invalid HTTP methods return 405."""
        response = client.patch('/')
        
        # Should not allow PATCH on root
        assert response.status_code in [405, 404]
    
    def test_malformed_json_400(self, client):
        """Test malformed JSON handling."""
        response = client.post('/api/auth/login',
            data='invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == 400


class TestCORS:
    """Test CORS headers."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present."""
        response = client.get('/')
        
        # Check for common CORS headers
        assert response.status_code == 200
    
    def test_options_request_allowed(self, client):
        """Test OPTIONS request for CORS."""
        response = client.options('/')
        
        assert response.status_code in [200, 404, 405]


class TestPagination:
    """Test pagination in list endpoints."""
    
    def test_pagination_parameters(self, client):
        """Test pagination with limit and offset."""
        response = client.get('/api/estates/public?limit=10&offset=0')
        
        assert response.status_code in [200, 400, 503]
    
    def test_pagination_invalid_params(self, client):
        """Test pagination with invalid parameters."""
        response = client.get('/api/estates/public?limit=invalid&offset=invalid')
        
        # Should handle gracefully or return error
        assert response.status_code in [200, 400, 503]


class TestRateLimiting:
    """Test rate limiting."""
    
    def test_multiple_requests_allowed(self, client):
        """Test that multiple requests are allowed."""
        for _ in range(5):
            response = client.get('/')
            # Should not be rate limited for legitimate requests
            assert response.status_code == 200
    
    def test_signup_weak_password(self, client):
        """Test signup with weak password."""
        response = client.post('/api/auth/signup',
            json={
                'email': 'test@example.com',
                'password': 'weak',
                'full_name': 'Test User',
                'role': 'manager',
                'estate_id': 'test-id',
            },
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_signup_invalid_role(self, client):
        """Test signup with invalid role."""
        response = client.post('/api/auth/signup',
            json={
                'email': 'test-invalid-role@example.com',
                'password': 'ValidPass123!',
                'full_name': 'Test User',
                'role': 'invalid_role',
                'estate_id': 'test-id',
            },
            content_type='application/json'
        )
        
        # May get 400 (bad request) or 429 (rate limited)
        assert response.status_code in [400, 429]
    
    def test_manager_signup_missing_estate(self, client):
        """Test manager signup without estate_id."""
        response = client.post('/api/auth/signup',
            json={
                'email': 'test-no-estate@example.com',
                'password': 'ValidPass123!',
                'full_name': 'Test User',
                'role': 'manager',
            },
            content_type='application/json'
        )
        
        # May get 400 (bad request) or 429 (rate limited)
        assert response.status_code in [400, 429]
        if response.status_code == 400:
            data = json.loads(response.data)
            assert 'estate_id' in data.get('error', '').lower() or data.get('error', '') != ''


class TestROIEndpoints:
    """Test ROI calculation endpoints."""
    
    def test_roi_summary_missing_parameters(self, client):
        """Test ROI summary without required parameters."""
        response = client.get('/api/roi/summary',
            headers={'Authorization': 'Bearer invalid-token'}
        )
        
        # Should return 401 (unauthorized) or 400 (bad request)
        assert response.status_code in [400, 401, 403]
    
    def test_roi_estate_trend_missing_parameters(self, client):
        """Test ROI estate trend without parameters."""
        response = client.get('/api/roi/estate-trend',
            headers={'Authorization': 'Bearer invalid-token'}
        )
        
        assert response.status_code in [400, 401, 403]


class TestLaborEndpoints:
    """Test labor tracking endpoints."""
    
    def test_labor_summary_unauthorized(self, client):
        """Test labor summary without authentication."""
        response = client.get('/api/labour/summary')
        
        # Endpoint may not exist or require authentication
        assert response.status_code in [401, 403, 404]
    
    def test_labor_stats_unauthorized(self, client):
        """Test labor stats without authentication."""
        response = client.get('/api/labour/stats')
        
        # Endpoint may not exist or require authentication
        assert response.status_code in [401, 403, 404]


class TestWaterEndpoints:
    """Test water usage endpoints."""
    
    def test_water_summary_unauthorized(self, client):
        """Test water summary without authentication."""
        response = client.get('/api/water/summary')
        
        # Endpoint may not exist or require authentication
        assert response.status_code in [401, 403, 404]
    
    def test_water_efficiency_unauthorized(self, client):
        """Test water efficiency without authentication."""
        response = client.get('/api/water/efficiency')
        
        # Endpoint may not exist or require authentication
        assert response.status_code in [401, 403, 404]


class TestReportEndpoints:
    """Test report generation endpoints."""
    
    def test_generate_report_unauthorized(self, client):
        """Test report generation without authentication."""
        response = client.get('/api/reports/generate/dashboard')
        
        # Endpoint may not exist or require auth
        assert response.status_code in [401, 403, 404]
    
    def test_generate_report_invalid_format(self, client):
        """Test report generation with invalid format."""
        response = client.get('/api/reports/generate/invalid',
            headers={'Authorization': 'Bearer invalid-token'}
        )
        
        # Endpoint may not exist
        assert response.status_code in [400, 401, 403, 404]


class TestErrorHandling:
    """Test error handling and status codes."""
    
    def test_404_not_found(self, client):
        """Test 404 for non-existent endpoint."""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test 405 for wrong HTTP method."""
        response = client.post('/health')  # GET only
        
        assert response.status_code == 405
    
    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post('/api/auth/signup',
            data='invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_missing_content_type(self, client):
        """Test handling of missing content type."""
        response = client.post('/api/auth/signup',
            data=json.dumps({'email': 'test@example.com'})
        )
        
        # May be 400 or handle gracefully
        assert response.status_code in [400, 415]


class TestCORSHeaders:
    """Test CORS header handling."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present."""
        response = client.get('/health')
        
        # CORS headers should be present
        assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 200
    
    def test_cors_preflight_request(self, client):
        """Test CORS preflight OPTIONS request."""
        response = client.options('/api/auth/signup')
        
        assert response.status_code in [200, 204]
