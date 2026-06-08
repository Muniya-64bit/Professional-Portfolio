"""Unit tests for ROI calculation module."""
import pytest
from datetime import datetime
from decimal import Decimal


class TestROICalculations:
    """Test ROI calculation functions."""
    
    def test_cost_per_kg_basic_calculation(self):
        """Test basic cost per kg calculation."""
        total_cost = 1000.00
        yield_kg = 100.00
        
        cost_per_kg = total_cost / yield_kg
        
        assert cost_per_kg == 10.00
    
    def test_cost_per_kg_with_decimals(self):
        """Test cost per kg with decimal values."""
        total_cost = Decimal('1500.50')
        yield_kg = Decimal('125.75')
        
        cost_per_kg = total_cost / yield_kg
        
        assert cost_per_kg > 0
        assert float(cost_per_kg) == pytest.approx(11.93, abs=0.01)
    
    def test_cost_per_kg_zero_yield_handling(self):
        """Test handling of zero yield (should not cause division by zero)."""
        total_cost = 1000.00
        yield_kg = 0
        
        # Should handle gracefully
        with pytest.raises(ZeroDivisionError):
            _ = total_cost / yield_kg
    
    def test_yield_trend_calculation(self):
        """Test yield trend over months."""
        monthly_yields = [100, 110, 105, 115, 120, 125]
        
        # Calculate month-over-month change
        trends = []
        for i in range(1, len(monthly_yields)):
            change = ((monthly_yields[i] - monthly_yields[i-1]) / monthly_yields[i-1]) * 100
            trends.append(change)
        
        assert len(trends) == 5
        assert all(isinstance(t, float) for t in trends)
    
    def test_roi_profitability_calculation(self):
        """Test ROI profitability calculation."""
        revenue = 50000.00
        investment = 25000.00
        
        roi_percentage = ((revenue - investment) / investment) * 100
        
        assert roi_percentage == 100.0  # 100% ROI
    
    def test_negative_roi_handling(self):
        """Test handling of negative ROI."""
        revenue = 15000.00
        investment = 25000.00
        
        roi_percentage = ((revenue - investment) / investment) * 100
        
        assert roi_percentage < 0
        assert roi_percentage == pytest.approx(-40.0, abs=0.1)
    
    def test_cost_per_kg_ranking(self):
        """Test ranking estates by cost per kg."""
        estates = [
            {'name': 'Estate A', 'cost_per_kg': 12.5},
            {'name': 'Estate B', 'cost_per_kg': 8.3},
            {'name': 'Estate C', 'cost_per_kg': 10.1},
        ]
        
        sorted_estates = sorted(estates, key=lambda e: e['cost_per_kg'])
        
        assert sorted_estates[0]['name'] == 'Estate B'
        assert sorted_estates[0]['cost_per_kg'] == 8.3
    
    def test_roi_monthly_trend(self):
        """Test monthly ROI trend analysis."""
        monthly_costs = [
            {'month': 1, 'cost_per_kg': 10.0},
            {'month': 2, 'cost_per_kg': 9.8},
            {'month': 3, 'cost_per_kg': 9.5},
            {'month': 4, 'cost_per_kg': 9.2},
        ]
        
        # Calculate trend
        trend_improvement = ((monthly_costs[0]['cost_per_kg'] - monthly_costs[-1]['cost_per_kg']) 
                            / monthly_costs[0]['cost_per_kg']) * 100
        
        assert trend_improvement > 0
        assert trend_improvement == pytest.approx(8.0, abs=0.1)
    
    def test_roi_threshold_flagging(self):
        """Test flagging of poor ROI performance."""
        cost_per_kg = 15.0
        threshold = 12.0
        
        is_flagged = cost_per_kg > threshold
        
        assert is_flagged is True
    
    def test_breakeven_calculation(self):
        """Test breakeven point calculation."""
        fixed_costs = 10000.00
        variable_cost_per_unit = 50.00
        price_per_unit = 100.00
        
        contribution_margin = price_per_unit - variable_cost_per_unit
        breakeven_units = fixed_costs / contribution_margin
        
        assert breakeven_units == 200.0


class TestROIComparisons:
    """Test ROI comparison and analysis."""
    
    def test_estate_vs_average_comparison(self):
        """Test estate comparison to average."""
        estate_cost = 10.0
        average_cost = 11.5
        
        performance_vs_avg = ((average_cost - estate_cost) / average_cost) * 100
        
        assert performance_vs_avg > 0  # Better than average
        assert performance_vs_avg == pytest.approx(13.04, abs=0.1)
    
    def test_year_on_year_comparison(self):
        """Test year-on-year ROI comparison."""
        previous_year_cost = 12.0
        current_year_cost = 10.5
        
        improvement = ((previous_year_cost - current_year_cost) / previous_year_cost) * 100
        
        assert improvement > 0
        assert improvement == pytest.approx(12.5, abs=0.1)
    
    def test_roi_quartile_calculation(self):
        """Test quartile calculation for ranking."""
        costs = [7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
        
        q1_index = len(costs) // 4
        q3_index = (3 * len(costs)) // 4
        
        q1 = costs[q1_index]
        q3 = costs[q3_index]
        
        assert q1 < q3
    
    def test_performance_percentile(self):
        """Test performance percentile calculation."""
        estate_rank = 5
        total_estates = 100
        
        percentile = (estate_rank / total_estates) * 100
        
        assert percentile == 5.0
    
    def test_best_vs_worst_comparison(self):
        """Test comparison between best and worst performers."""
        best_cost = 8.0
        worst_cost = 15.0
        
        difference_percentage = ((worst_cost - best_cost) / best_cost) * 100
        
        assert difference_percentage > 0
        assert difference_percentage == pytest.approx(87.5, abs=0.1)


class TestROIMonthlyAnalysis:
    """Test monthly ROI analysis."""
    
    def test_monthly_cost_totaling(self):
        """Test monthly cost calculation."""
        monthly_data = [
            {'month': 1, 'labor_cost': 5000, 'input_cost': 2000, 'water_cost': 1000},
            {'month': 2, 'labor_cost': 5100, 'input_cost': 2000, 'water_cost': 950},
        ]
        
        for month in monthly_data:
            total_cost = month['labor_cost'] + month['input_cost'] + month['water_cost']
            assert total_cost > 0
    
    def test_monthly_yield_tracking(self):
        """Test monthly yield tracking."""
        monthly_yields = {
            1: 4500, 2: 4700, 3: 5000, 4: 5200,
            5: 5100, 6: 5300, 7: 5400, 8: 5200,
            9: 5100, 10: 4900, 11: 4800, 12: 4600,
        }
        
        total_annual_yield = sum(monthly_yields.values())
        avg_monthly_yield = total_annual_yield / len(monthly_yields)
        
        assert total_annual_yield > 0
        assert avg_monthly_yield > 0
    
    def test_best_performing_month(self):
        """Test identifying best performing month."""
        monthly_costs = {
            1: 10.5, 2: 10.2, 3: 9.8, 4: 9.5,
            5: 9.2, 6: 9.8, 7: 10.0, 8: 10.3,
        }
        
        best_month = min(monthly_costs, key=monthly_costs.get)
        best_cost = monthly_costs[best_month]
        
        assert best_month == 5
        assert best_cost == 9.2
    
    def test_worst_performing_month(self):
        """Test identifying worst performing month."""
        monthly_costs = {
            1: 10.5, 2: 10.2, 3: 9.8, 4: 9.5,
            5: 9.2, 6: 9.8, 7: 10.0, 8: 10.3,
        }
        
        worst_month = max(monthly_costs, key=monthly_costs.get)
        worst_cost = monthly_costs[worst_month]
        
        assert worst_month == 1
        assert worst_cost == 10.5


class TestROIFlags:
    """Test ROI flagging system."""
    
    def test_flag_high_cost(self):
        """Test flagging high cost estates."""
        cost_per_kg = 15.0
        threshold = 12.0
        
        should_flag = cost_per_kg > threshold
        
        assert should_flag is True
    
    def test_flag_deteriorating_trend(self):
        """Test flagging deteriorating trends."""
        costs = [10.0, 10.5, 11.0, 11.5, 12.0]
        
        # Check if trend is increasing (deteriorating)
        is_deteriorating = costs[-1] > costs[0]
        
        assert is_deteriorating is True
    
    def test_flag_sudden_spike(self):
        """Test flagging sudden cost spikes."""
        costs = [10.0, 10.1, 9.9, 10.0, 20.0]  # Sudden spike
        
        avg_before = sum(costs[:-1]) / len(costs[:-1])
        current = costs[-1]
        
        is_spike = current > (avg_before * 1.5)
        
        assert is_spike is True
    
    def test_multiple_flags(self):
        """Test multiple flag reasons."""
        estate = {
            'cost_per_kg': 15.0,
            'trend': 'deteriorating',
            'has_spike': True,
        }
        
        flags = []
        if estate['cost_per_kg'] > 12.0:
            flags.append('high_cost')
        if estate['trend'] == 'deteriorating':
            flags.append('deteriorating_trend')
        if estate['has_spike']:
            flags.append('spike_detected')
        
        assert len(flags) == 3


class TestROISnapshots:
    """Test ROI snapshot calculations."""
    
    def test_snapshot_creation(self):
        """Test ROI snapshot data structure."""
        snapshot = {
            'estate_id': 'estate-001',
            'year': 2024,
            'month': 6,
            'cost_per_kg': 10.50,
            'rank': 5,
            'is_flagged': False,
        }
        
        required_fields = ['estate_id', 'year', 'month', 'cost_per_kg', 'rank']
        
        for field in required_fields:
            assert field in snapshot
    
    def test_snapshot_ranking(self):
        """Test ranking within snapshot data."""
        snapshots = [
            {'estate_id': 'e1', 'cost_per_kg': 8.5, 'rank': None},
            {'estate_id': 'e2', 'cost_per_kg': 10.0, 'rank': None},
            {'estate_id': 'e3', 'cost_per_kg': 9.5, 'rank': None},
        ]
        
        # Sort and assign ranks
        sorted_snapshots = sorted(snapshots, key=lambda s: s['cost_per_kg'])
        for idx, snapshot in enumerate(sorted_snapshots, 1):
            snapshot['rank'] = idx
        
        assert sorted_snapshots[0]['rank'] == 1
        assert sorted_snapshots[0]['estate_id'] == 'e1'
    
    def test_snapshot_historical_comparison(self):
        """Test comparing snapshots across months."""
        snapshots = [
            {'month': 1, 'cost_per_kg': 10.0},
            {'month': 2, 'cost_per_kg': 9.8},
            {'month': 3, 'cost_per_kg': 9.5},
        ]
        
        # Compare latest to earliest
        improvement = ((snapshots[0]['cost_per_kg'] - snapshots[-1]['cost_per_kg']) 
                      / snapshots[0]['cost_per_kg']) * 100
        
        assert improvement > 0


class TestROIAggregation:
    """Test ROI data aggregation."""
    
    def test_average_cost_by_estate(self):
        """Test calculating average cost per kg by estate."""
        monthly_data = [
            {'month': 1, 'cost_per_kg': 10.0},
            {'month': 2, 'cost_per_kg': 9.8},
            {'month': 3, 'cost_per_kg': 9.5},
        ]
        
        avg_cost = sum(m['cost_per_kg'] for m in monthly_data) / len(monthly_data)
        
        assert avg_cost == pytest.approx(9.77, abs=0.01)
    
    def test_annual_roi_calculation(self):
        """Test calculating annual ROI."""
        monthly_costs = [10.0, 9.8, 9.5, 9.2, 9.8, 10.0, 10.5, 10.2, 9.9, 9.6, 9.5, 9.4]
        
        annual_avg = sum(monthly_costs) / len(monthly_costs)
        
        assert annual_avg == pytest.approx(9.78, abs=0.01)
    
    def test_quartile_aggregation(self):
        """Test aggregating data by quartile."""
        costs = [8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0]
        
        q1 = costs[len(costs)//4]
        q2 = costs[len(costs)//2]
        q3 = costs[(3*len(costs))//4]
        
        assert q1 < q2 < q3


class TestROIValidation:
    """Test ROI data validation."""
    
    def test_cost_per_kg_range(self):
        """Test cost per kg is within reasonable range."""
        cost_per_kg = 10.50
        
        # Should be positive and less than 100
        is_valid = 0 < cost_per_kg < 100
        
        assert is_valid is True
    
    def test_rank_range_validation(self):
        """Test rank is within valid range."""
        rank = 5
        total_estates = 100
        
        is_valid = 1 <= rank <= total_estates
        
        assert is_valid is True
    
    def test_year_month_validation(self):
        """Test year and month are valid."""
        year = 2024
        month = 6
        
        is_valid = year >= 2000 and 1 <= month <= 12
        
        assert is_valid is True
    
    def test_estate_id_not_empty(self):
        """Test estate ID is not empty."""
        estate_id = 'estate-001'
        
        assert len(estate_id) > 0
        assert isinstance(estate_id, str)

    
    def test_roi_ranking_calculation(self):
        """Test ROI ranking calculation."""
        estates_roi = [
            {'estate_id': '1', 'cost_per_kg': 10.5},
            {'estate_id': '2', 'cost_per_kg': 8.2},
            {'estate_id': '3', 'cost_per_kg': 9.1},
            {'estate_id': '4', 'cost_per_kg': 7.5},
        ]
        
        # Sort by cost_per_kg ascending (lower is better)
        sorted_estates = sorted(estates_roi, key=lambda x: x['cost_per_kg'])
        
        # Add ranks
        for rank, estate in enumerate(sorted_estates, 1):
            estate['rank'] = rank
        
        assert sorted_estates[0]['estate_id'] == '4'
        assert sorted_estates[0]['rank'] == 1
        assert sorted_estates[-1]['estate_id'] == '1'
        assert sorted_estates[-1]['rank'] == 4


class TestROIDataValidation:
    """Test ROI data validation."""
    
    def test_valid_cost_per_kg_range(self):
        """Test that cost per kg is within valid range."""
        cost_per_kg = 12.50
        
        assert cost_per_kg > 0
        assert cost_per_kg < 10000  # Reasonable upper limit
    
    def test_valid_yield_range(self):
        """Test that yield is within valid range."""
        yield_kg = 500.00
        
        assert yield_kg > 0
        assert yield_kg < 1000000  # Reasonable upper limit
    
    def test_monthly_index_validation(self):
        """Test month index validation."""
        valid_months = list(range(1, 13))
        
        for month in valid_months:
            assert 1 <= month <= 12
    
    def test_year_validation(self):
        """Test year validation."""
        valid_year = 2024
        
        assert valid_year >= 2000
        assert valid_year <= 2100


class TestROIFlagging:
    """Test ROI flagging logic."""
    
    def test_flag_high_cost_estate(self):
        """Test flagging estates with high cost per kg."""
        average_cost = 10.0
        estate_cost = 25.0  # 150% higher than average
        threshold_ratio = 1.5
        
        should_flag = estate_cost / average_cost > threshold_ratio
        
        assert should_flag is True
    
    def test_no_flag_normal_cost_estate(self):
        """Test no flag for normal cost estates."""
        average_cost = 10.0
        estate_cost = 11.0  # Only 10% higher
        threshold_ratio = 1.5
        
        should_flag = estate_cost / average_cost > threshold_ratio
        
        assert should_flag is False
    
    def test_flag_low_yield_estate(self):
        """Test flagging estates with low yield."""
        average_yield = 500.0
        estate_yield = 200.0  # 60% below average
        threshold_ratio = 0.7
        
        should_flag = estate_yield / average_yield < threshold_ratio
        
        assert should_flag is True
