import pytest
from slo.calculator import SLOCalculator

def test_healthy_slo():
    """Service with 1 error in 10000 requests should be healthy"""
    calc = SLOCalculator(target_availability=0.999)
    result = calc.calculate_availability(total_requests=10000, total_errors=1)
    
    assert result.slo_met == True
    assert result.status == "healthy"
    assert result.current_pct > 99.9
    assert result.error_budget_remaining_pct > 0

def test_violated_slo():
    """Service with 500 errors in 10000 requests should violate SLO"""
    calc = SLOCalculator(target_availability=0.999)
    result = calc.calculate_availability(total_requests=10000, total_errors=500)
    
    assert result.slo_met == False
    assert result.status == "violated"
    assert result.current_pct < 99.9

def test_zero_requests():
    """Calculator should handle zero requests gracefully"""
    calc = SLOCalculator()
    result = calc.calculate_availability(total_requests=0, total_errors=0)
    
    assert result.status == "no_data"

def test_error_budget_math():
    """Verify error budget calculation is correct"""
    calc = SLOCalculator(target_availability=0.999)
    # 99.9% SLO means 0.1% error budget
    assert calc.error_budget_pct == pytest.approx(0.001)

def test_at_risk_status():
    """Service consuming >50% error budget should be at_risk"""
    calc = SLOCalculator(target_availability=0.999)
    # 0.06% error rate on a 0.1% budget = 60% consumed
    result = calc.calculate_availability(total_requests=10000, total_errors=6)
    
    assert result.status == "at_risk"
    assert result.error_budget_consumed_pct > 50