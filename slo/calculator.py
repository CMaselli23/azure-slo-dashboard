from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class SLOStatus:
    """
    Represents the current state of an SLO.
    
    SRE concept: An SLO has three key states:
    - Met: availability >= target, error budget intact
    - At risk: budget >50% consumed, need to slow feature work  
    - Violated: budget exhausted, freeze deployments, focus on reliability
    """
    slo_name: str
    target_pct: float           # e.g. 99.9
    current_pct: float          # e.g. 99.7
    slo_met: bool
    error_budget_total_pct: float    # e.g. 0.1 (the 0.1% you're allowed to fail)
    error_budget_consumed_pct: float # e.g. 0.08 (how much you've used)
    error_budget_remaining_pct: float
    burn_rate: float            # How fast you're consuming budget vs normal
    status: str                 # "healthy" | "at_risk" | "violated"
    total_requests: int
    total_errors: int

class SLOCalculator:
    """
    Calculates SLO metrics from raw request/error counts.
    
    Usage:
        calc = SLOCalculator(target_availability=0.999)
        status = calc.calculate(total_requests=10000, total_errors=8)
    """

    def __init__(
        self,
        target_availability: float = 0.999,
        target_latency_ms: int = 200,
        slo_window_days: int = 30
    ):
        self.target_availability = target_availability
        self.target_latency_ms = target_latency_ms
        self.slo_window_days = slo_window_days

        # Error budget = the amount of failure you're ALLOWED per window
        # For 99.9% SLO: error budget = 0.1% of requests can fail
        self.error_budget_pct = 1 - target_availability

    def calculate_availability(
        self,
        total_requests: int,
        total_errors: int
    ) -> SLOStatus:
        """
        Calculate availability SLO status.
        
        SRE concept: Availability = (good requests) / (total requests)
        Error budget = how much of your allowed failure you've consumed.
        Burn rate = current consumption rate vs sustainable rate.
        A burn rate of 1.0 = exactly consuming budget at the right pace.
        A burn rate of 2.0 = consuming budget 2x too fast, will run out early.
        """
        if total_requests == 0:
            logger.warning("No requests to calculate SLO from")
            return self._empty_status()

        good_requests = total_requests - total_errors
        current_availability = good_requests / total_requests
        current_pct = round(current_availability * 100, 4)

        # How much of our error budget have we consumed?
        actual_error_rate = 1 - current_availability
        budget_consumed = actual_error_rate / self.error_budget_pct
        budget_consumed_pct = round(budget_consumed * 100, 2)
        budget_remaining_pct = round((1 - budget_consumed) * 100, 2)

        # Burn rate: >1 means burning too fast
        # Sustained burn rate of 14.4 = budget exhausted in 2 hours
        burn_rate = round(budget_consumed * self.slo_window_days, 2)

        # Determine status
        if current_availability >= self.target_availability:
            if budget_consumed_pct < 50:
                status = "healthy"
            else:
                status = "at_risk"
        else:
            status = "violated"

        return SLOStatus(
            slo_name="availability",
            target_pct=round(self.target_availability * 100, 4),
            current_pct=current_pct,
            slo_met=current_availability >= self.target_availability,
            error_budget_total_pct=round(self.error_budget_pct * 100, 4),
            error_budget_consumed_pct=budget_consumed_pct,
            error_budget_remaining_pct=budget_remaining_pct,
            burn_rate=burn_rate,
            status=status,
            total_requests=total_requests,
            total_errors=total_errors
        )

    def calculate_latency(
        self,
        total_requests: int,
        slow_requests: int
    ) -> SLOStatus:
        """
        Calculate latency SLO status.
        
        SRE concept: Latency SLO is typically expressed as a percentile.
        "99% of requests must complete in under 200ms"
        slow_requests = requests that exceeded the latency target.
        """
        if total_requests == 0:
            return self._empty_status()

        fast_requests = total_requests - slow_requests
        current_availability = fast_requests / total_requests
        current_pct = round(current_availability * 100, 4)

        actual_error_rate = 1 - current_availability
        budget_consumed = actual_error_rate / self.error_budget_pct
        budget_consumed_pct = round(budget_consumed * 100, 2)
        budget_remaining_pct = round((1 - budget_consumed) * 100, 2)
        burn_rate = round(budget_consumed * self.slo_window_days, 2)

        if current_availability >= self.target_availability:
            status = "healthy" if budget_consumed_pct < 50 else "at_risk"
        else:
            status = "violated"

        return SLOStatus(
            slo_name="latency",
            target_pct=round(self.target_availability * 100, 4),
            current_pct=current_pct,
            slo_met=current_availability >= self.target_availability,
            error_budget_total_pct=round(self.error_budget_pct * 100, 4),
            error_budget_consumed_pct=budget_consumed_pct,
            error_budget_remaining_pct=budget_remaining_pct,
            burn_rate=burn_rate,
            status=status,
            total_requests=total_requests,
            total_errors=slow_requests
        )

    def _empty_status(self) -> SLOStatus:
        return SLOStatus(
            slo_name="unknown", target_pct=0, current_pct=0,
            slo_met=False, error_budget_total_pct=0,
            error_budget_consumed_pct=0, error_budget_remaining_pct=0,
            burn_rate=0, status="no_data", total_requests=0, total_errors=0
        )