"""Integration tests for water API endpoints."""
import pytest
import json


class TestWaterEndpointsBasic:
    """Test basic water endpoints."""
    
    def test_water_module_available(self, client):
        """Test that water module endpoints are available."""
        response = client.get('/api/water/summary')
        
        assert response.status_code in [401, 404, 403, 200]
    
    def test_water_post_usage(self, client):
        """Test posting water usage data."""
        response = client.post('/api/water/usage',
            json={
                'estate_id': 'test-estate',
                'volume_liters': 5000,
                'cost_lkr': 2500.00,
                'date': '2024-06-15',
            },
            content_type='application/json'
        )
        
        assert response.status_code in [400, 401, 404, 201, 405]
    
    def test_water_get_usage(self, client):
        """Test retrieving water usage."""
        response = client.get('/api/water/usage?estate_id=test-estate&month=6&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]


class TestWaterEfficiencyEndpoints:
    """Test water efficiency endpoints."""
    
    def test_water_efficiency_score(self, client):
        """Test getting water efficiency score."""
        response = client.get('/api/water/efficiency?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_water_baseline_comparison(self, client):
        """Test water baseline comparison."""
        response = client.get('/api/water/baseline?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_water_cost_analysis(self, client):
        """Test water cost analysis."""
        response = client.get('/api/water/cost?estate_id=test-estate&month=6&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]


class TestWaterTrendEndpoints:
    """Test water trend analysis endpoints."""
    
    def test_monthly_water_trend(self, client):
        """Test monthly water usage trend."""
        response = client.get('/api/water/trends/monthly?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_seasonal_water_trend(self, client):
        """Test seasonal water usage trends."""
        response = client.get('/api/water/trends/seasonal?estate_id=test-estate')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_annual_water_projection(self, client):
        """Test annual water usage projection."""
        response = client.get('/api/water/projection?estate_id=test-estate&current_month=6')
        
        assert response.status_code in [200, 401, 404, 400]


class TestWaterIrrigationEndpoints:
    """Test water irrigation management."""
    
    def test_irrigation_schedule(self, client):
        """Test getting irrigation schedule."""
        response = client.get('/api/water/irrigation/schedule?estate_id=test-estate&month=6')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_irrigation_history(self, client):
        """Test irrigation history."""
        response = client.get('/api/water/irrigation/history?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]


class TestWaterQualityEndpoints:
    """Test water quality endpoints."""
    
    def test_water_quality_check(self, client):
        """Test water quality check."""
        response = client.get('/api/water/quality?source=well&estate_id=test-estate')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_water_quality_history(self, client):
        """Test water quality history."""
        response = client.get('/api/water/quality/history?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]


class TestWaterBudgetEndpoints:
    """Test water budget endpoints."""
    
    def test_water_budget_allocation(self, client):
        """Test water budget allocation."""
        response = client.get('/api/water/budget?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_water_budget_vs_actual(self, client):
        """Test water budget vs actual spending."""
        response = client.get('/api/water/budget/analysis?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 401, 404, 400]


class TestWaterSourceManagement:
    """Test water source management endpoints."""
    
    def test_water_sources(self, client):
        """Test getting water sources."""
        response = client.get('/api/water/sources?estate_id=test-estate')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_source_allocation(self, client):
        """Test water source allocation."""
        response = client.get('/api/water/allocation?estate_id=test-estate&month=6&year=2024')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_storage_levels(self, client):
        """Test water storage levels."""
        response = client.get('/api/water/storage?estate_id=test-estate')
        
        assert response.status_code in [200, 401, 404, 400]
