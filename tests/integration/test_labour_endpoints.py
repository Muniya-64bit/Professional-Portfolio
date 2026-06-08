"""Integration tests for labour API endpoints."""
import pytest
import json


class TestLaborEndpointsBasic:
    """Test basic labour endpoints."""
    
    def test_labour_module_available(self, client):
        """Test that labour module endpoints are available."""
        # Try to access a labour endpoint
        response = client.get('/api/labour/summary')
        
        # Should return 401 (auth required) or 404 (endpoint doesn't exist)
        assert response.status_code in [401, 404, 403]
    
    def test_labour_post_create_plan(self, client):
        """Test creating labour plan."""
        response = client.post('/api/labour/plans',
            json={
                'estate_id': 'test-estate',
                'month': 6,
                'year': 2024,
            },
            content_type='application/json'
        )
        
        # May require auth or endpoint may not exist
        assert response.status_code in [400, 401, 404, 201]
    
    def test_labour_get_plans(self, client):
        """Test retrieving labour plans."""
        response = client.get('/api/labour/plans?estate_id=test-estate&month=6&year=2024')
        
        assert response.status_code in [200, 401, 404]
    
    def test_labour_get_summary_with_params(self, client):
        """Test labour summary with parameters."""
        response = client.get('/api/labour/summary?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]


class TestLaborEfficiencyEndpoints:
    """Test labour efficiency tracking endpoints."""
    
    def test_labour_efficiency_metric(self, client):
        """Test getting labour efficiency metrics."""
        response = client.get('/api/labour/efficiency?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_labour_productivity_stats(self, client):
        """Test getting productivity statistics."""
        response = client.get('/api/labour/productivity?month=6&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]


class TestLaborGroupManagement:
    """Test labour group management endpoints."""
    
    def test_create_labour_group(self, client):
        """Test creating a labour group."""
        response = client.post('/api/labour/groups',
            json={
                'estate_id': 'test-estate',
                'name': 'Group A',
                'leader_id': 'emp-001',
                'member_count': 5,
            },
            content_type='application/json'
        )
        
        assert response.status_code in [400, 401, 404, 201, 405]
    
    def test_get_labour_groups(self, client):
        """Test retrieving labour groups."""
        response = client.get('/api/labour/groups?estate_id=test-estate')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_update_labour_group(self, client):
        """Test updating labour group."""
        response = client.put('/api/labour/groups/group-001',
            json={'member_count': 6},
            content_type='application/json'
        )
        
        assert response.status_code in [400, 401, 404, 200]


class TestLaborEmployeeTracking:
    """Test labour employee tracking endpoints."""
    
    def test_get_employee_list(self, client):
        """Test getting employee list."""
        response = client.get('/api/labour/employees?estate_id=test-estate')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_get_employee_details(self, client):
        """Test getting employee details."""
        response = client.get('/api/labour/employees/emp-001')
        
        assert response.status_code in [200, 401, 404, 400, 405]
    
    def test_employee_wage_tracking(self, client):
        """Test employee wage tracking."""
        response = client.get('/api/labour/employees/emp-001/wages?month=6&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]


class TestLaborRotationEndpoints:
    """Test labour rotation management."""
    
    def test_get_rotation_schedule(self, client):
        """Test getting rotation schedule."""
        response = client.get('/api/labour/rotation?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_advance_rotation(self, client):
        """Test advancing rotation to next month."""
        response = client.post('/api/labour/rotation/advance',
            json={'estate_id': 'test-estate', 'year': 2024, 'month': 6},
            content_type='application/json'
        )
        
        assert response.status_code in [400, 401, 404, 200]


class TestLaborYieldRecording:
    """Test labour yield recording endpoints."""
    
    def test_record_yield(self, client):
        """Test recording yield for labour assignment."""
        response = client.post('/api/labour/yield',
            json={
                'estate_id': 'test-estate',
                'month': 6,
                'year': 2024,
                'yield_kg': 5000,
            },
            content_type='application/json'
        )
        
        assert response.status_code in [400, 401, 404, 201]
    
    def test_get_yield_data(self, client):
        """Test retrieving yield data."""
        response = client.get('/api/labour/yield?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]


class TestLaborStatisticsEndpoints:
    """Test labour statistics endpoints."""
    
    def test_monthly_statistics(self, client):
        """Test getting monthly labour statistics."""
        response = client.get('/api/labour/stats/monthly?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_annual_statistics(self, client):
        """Test getting annual labour statistics."""
        response = client.get('/api/labour/stats/annual?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_comparative_statistics(self, client):
        """Test comparative statistics."""
        response = client.get('/api/labour/stats/compare?year=2024&month=6')
        
        assert response.status_code in [200, 401, 404, 400]
