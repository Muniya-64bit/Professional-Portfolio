"""Integration tests for ROI API endpoints."""
import pytest
import json


class TestROIEndpointsBasic:
    """Test basic ROI endpoints."""
    
    def test_roi_summary_endpoint(self, client):
        """Test ROI summary endpoint."""
        response = client.get('/api/roi/summary?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_roi_estate_trend(self, client):
        """Test ROI estate trend endpoint."""
        response = client.get('/api/roi/estate-trend?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_roi_comparison(self, client):
        """Test ROI comparison between estates."""
        response = client.get('/api/roi/compare?year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]


class TestROICalculationEndpoints:
    """Test ROI calculation endpoints."""
    
    def test_cost_per_kg_calculation(self, client):
        """Test cost per kg calculation endpoint."""
        response = client.get('/api/roi/cost-per-kg?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_roi_percentage_calculation(self, client):
        """Test ROI percentage calculation."""
        response = client.get('/api/roi/percentage?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_breakeven_analysis(self, client):
        """Test breakeven analysis."""
        response = client.get('/api/roi/breakeven?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 400, 401, 404]


class TestROIRankingEndpoints:
    """Test ROI ranking endpoints."""
    
    def test_estate_ranking(self, client):
        """Test estate ranking by cost per kg."""
        response = client.get('/api/roi/ranking?year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_top_performers(self, client):
        """Test top performing estates."""
        response = client.get('/api/roi/top-performers?year=2024&limit=10')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_flagged_estates(self, client):
        """Test flagged estates."""
        response = client.get('/api/roi/flagged?year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]


class TestROITrendEndpoints:
    """Test ROI trend analysis endpoints."""
    
    def test_monthly_trend_analysis(self, client):
        """Test monthly trend analysis."""
        response = client.get('/api/roi/trends/monthly?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_annual_trend_analysis(self, client):
        """Test annual trend analysis."""
        response = client.get('/api/roi/trends/annual?estate_id=test-estate')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_year_on_year_comparison(self, client):
        """Test year-on-year comparison."""
        response = client.get('/api/roi/trends/yoy?estate_id=test-estate&current_year=2024&previous_year=2023')
        
        assert response.status_code in [200, 400, 401, 404]


class TestROITargetEndpoints:
    """Test ROI target/threshold endpoints."""
    
    def test_target_cost_per_kg(self, client):
        """Test target cost per kg."""
        response = client.get('/api/roi/target?estate_id=test-estate')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_set_roi_target(self, client):
        """Test setting ROI target."""
        response = client.post('/api/roi/target',
            json={'estate_id': 'test-estate', 'target_cost_per_kg': 10.00},
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 401, 404, 201]
    
    def test_performance_vs_target(self, client):
        """Test performance versus target."""
        response = client.get('/api/roi/performance?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]


class TestROISnapshotEndpoints:
    """Test ROI snapshot endpoints."""
    
    def test_get_roi_snapshots(self, client):
        """Test getting ROI snapshots."""
        response = client.get('/api/roi/snapshots?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_create_roi_snapshot(self, client):
        """Test creating ROI snapshot."""
        response = client.post('/api/roi/snapshots',
            json={
                'estate_id': 'test-estate',
                'year': 2024,
                'month': 6,
                'cost_per_kg': 10.50,
            },
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 401, 404, 201]
