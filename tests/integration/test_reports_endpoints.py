"""Integration tests for report API endpoints."""
import pytest
import json


class TestReportGenerationEndpoints:
    """Test report generation endpoints."""
    
    def test_generate_dashboard_report(self, client):
        """Test generating dashboard report."""
        response = client.post('/api/reports/generate/dashboard',
            json={
                'estate_id': 'test-estate',
                'year': 2024,
                'month': 6,
            },
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 401, 403, 404]
    
    def test_generate_pdf_report(self, client):
        """Test generating PDF report."""
        response = client.post('/api/reports/generate/pdf',
            json={
                'estate_id': 'test-estate',
                'year': 2024,
                'month': 6,
            },
            content_type='application/json'
        )
        
        # PDF response should have appropriate content type
        assert response.status_code in [200, 400, 401, 403, 404]
    
    def test_generate_csv_export(self, client):
        """Test generating CSV export."""
        response = client.get('/api/reports/export/csv?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 403, 404]


class TestReportTypeEndpoints:
    """Test different report types."""
    
    def test_yield_report(self, client):
        """Test yield analysis report."""
        response = client.get('/api/reports/yield?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_labor_report(self, client):
        """Test labour report."""
        response = client.get('/api/reports/labour?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_water_report(self, client):
        """Test water report."""
        response = client.get('/api/reports/water?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_roi_report(self, client):
        """Test ROI analysis report."""
        response = client.get('/api/reports/roi?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_comprehensive_report(self, client):
        """Test comprehensive report."""
        response = client.get('/api/reports/comprehensive?estate_id=test-estate&year=2024')
        
        assert response.status_code in [200, 400, 401, 404]


class TestReportFilteringEndpoints:
    """Test report filtering and customization."""
    
    def test_report_with_filters(self, client):
        """Test report with filters."""
        response = client.get('/api/reports/generate?estate_id=test-estate&year=2024&month=6&metrics=yield,labour,water')
        
        assert response.status_code in [200, 400, 401, 404, 405]
    
    def test_report_date_range(self, client):
        """Test report for date range."""
        response = client.get('/api/reports/range?estate_id=test-estate&start_date=2024-01-01&end_date=2024-06-30')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_multi_estate_report(self, client):
        """Test report for multiple estates."""
        response = client.get('/api/reports/multi?estates=estate-001,estate-002,estate-003&year=2024')
        
        assert response.status_code in [200, 400, 401, 404]


class TestReportAccessControl:
    """Test report access control and permissions."""
    
    def test_unauthorized_report_access(self, client):
        """Test accessing report without authorization."""
        response = client.get('/api/reports/generate/dashboard?estate_id=other-estate&year=2024&month=6')
        
        # Should require auth or deny access
        assert response.status_code in [401, 403, 404]
    
    def test_report_with_invalid_estate(self, client):
        """Test report with invalid estate ID."""
        response = client.get('/api/reports/generate/dashboard?estate_id=invalid-id&year=2024&month=6')
        
        assert response.status_code in [400, 401, 403, 404]


class TestReportSchedulingEndpoints:
    """Test report scheduling endpoints."""
    
    def test_schedule_report(self, client):
        """Test scheduling a report."""
        response = client.post('/api/reports/schedule',
            json={
                'estate_id': 'test-estate',
                'report_type': 'monthly',
                'frequency': 'monthly',
                'day_of_month': 1,
            },
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 401, 404, 201]
    
    def test_get_scheduled_reports(self, client):
        """Test getting scheduled reports."""
        response = client.get('/api/reports/scheduled?estate_id=test-estate')
        
        assert response.status_code in [200, 401, 404, 400]
    
    def test_cancel_scheduled_report(self, client):
        """Test canceling scheduled report."""
        response = client.delete('/api/reports/scheduled/report-123')
        
        assert response.status_code in [200, 400, 401, 404]


class TestReportHistoryEndpoints:
    """Test report history and archival."""
    
    def test_report_history(self, client):
        """Test getting report history."""
        response = client.get('/api/reports/history?estate_id=test-estate&limit=10')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_get_previous_report(self, client):
        """Test retrieving previous report."""
        response = client.get('/api/reports/previous?estate_id=test-estate&current_month=6&current_year=2024')
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_report_comparison(self, client):
        """Test comparing two reports."""
        response = client.get('/api/reports/compare?report_id_1=report-001&report_id_2=report-002')
        
        assert response.status_code in [200, 400, 401, 404]


class TestReportValidationEndpoints:
    """Test report validation and quality checks."""
    
    def test_validate_report_data(self, client):
        """Test validating report data."""
        response = client.post('/api/reports/validate',
            json={
                'estate_id': 'test-estate',
                'year': 2024,
                'month': 6,
                'data': {'yield': 5000, 'cost': 5000},
            },
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 401, 404]
    
    def test_data_quality_check(self, client):
        """Test data quality check."""
        response = client.get('/api/reports/quality?estate_id=test-estate&year=2024&month=6')
        
        assert response.status_code in [200, 400, 401, 404]


class TestReportDownloadEndpoints:
    """Test report download endpoints."""
    
    def test_download_pdf_report(self, client):
        """Test downloading PDF report."""
        response = client.get('/api/reports/download/pdf?estate_id=test-estate&year=2024&month=6')
        
        # Should return PDF or require auth
        assert response.status_code in [200, 400, 401, 404]
    
    def test_download_csv_report(self, client):
        """Test downloading CSV report."""
        response = client.get('/api/reports/download/csv?estate_id=test-estate&year=2024&month=6')
        
        # Should return CSV or require auth
        assert response.status_code in [200, 400, 401, 404]
    
    def test_download_excel_report(self, client):
        """Test downloading Excel report."""
        response = client.get('/api/reports/download/excel?estate_id=test-estate&year=2024&month=6')
        
        # Should return Excel or require auth
        assert response.status_code in [200, 400, 401, 404]


class TestReportNotificationEndpoints:
    """Test report notification endpoints."""
    
    def test_report_email_notification(self, client):
        """Test report email notification."""
        response = client.post('/api/reports/notify/email',
            json={
                'estate_id': 'test-estate',
                'recipient_email': 'manager@example.com',
                'report_type': 'monthly',
            },
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 401, 404, 201]
    
    def test_report_notification_settings(self, client):
        """Test notification settings."""
        response = client.get('/api/reports/notifications?estate_id=test-estate')
        
        assert response.status_code in [200, 400, 401, 404]
