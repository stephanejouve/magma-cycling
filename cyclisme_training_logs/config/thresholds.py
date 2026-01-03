"""
Training Thresholds Configuration Module.

Centralized training load thresholds loaded from environment variables.
Calibrated for specific athlete profile (54y master, exceptional recovery,
sleep-dependent).

Examples:
    Load thresholds from environment::

        thresholds = TrainingThresholds.from_env()
        print(f"TSB Critical: {thresholds.tsb_critical}")
        print(f"ATL/CTL Warning: {thresholds.atl_ctl_ratio_warning}")

    Check if TSB is in optimal range::

        if thresholds.is_tsb_optimal(tsb=5):
            print("TSB in optimal training zone")

Author: Claude Code
Created: 2026-01-01
"""

import os
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class TrainingThresholds(BaseModel):
    """
    Training load thresholds for overtraining detection.

    These thresholds are calibrated for a 54-year-old master athlete
    with exceptional recovery capacity but sleep-dependent performance.

    Attributes:
        tsb_fresh_min: Minimum TSB for 'fresh' state (TSB > this = fresh)
        tsb_optimal_min: Minimum TSB for 'optimal' state
        tsb_fatigued_min: Minimum TSB for 'fatigued' state
        tsb_critical: Critical TSB threshold (below = critical overreach)
        atl_ctl_ratio_optimal: Optimal ATL/CTL ratio (< this = optimal)
        atl_ctl_ratio_warning: Warning ATL/CTL ratio threshold
        atl_ctl_ratio_critical: Critical ATL/CTL ratio threshold
        recovery_hrv_threshold_percent: HRV threshold as % of baseline
        recovery_sleep_hours_min: Minimum sleep hours for recovery
        recovery_resting_hr_deviation_max: Max resting HR deviation above baseline
    """

    # TSB Thresholds
    tsb_fresh_min: float = Field(description="Minimum TSB for 'fresh' state (TSB > this value)")
    tsb_optimal_min: float = Field(description="Minimum TSB for 'optimal' training state")
    tsb_fatigued_min: float = Field(
        description="Minimum TSB for 'fatigued' state (not yet critical)"
    )
    tsb_critical: float = Field(description="Critical TSB threshold indicating overreach risk")

    # ATL/CTL Ratio Thresholds
    atl_ctl_ratio_optimal: float = Field(
        gt=0, description="Optimal ATL/CTL ratio (< this = optimal)"
    )
    atl_ctl_ratio_warning: float = Field(gt=0, description="Warning ATL/CTL ratio threshold")
    atl_ctl_ratio_critical: float = Field(gt=0, description="Critical ATL/CTL ratio threshold")

    # Recovery Indicators (for RecoveryAnalyzer)
    recovery_hrv_threshold_percent: float = Field(
        gt=0, le=100, description="HRV threshold as % of baseline (90 = 90% of baseline)"
    )
    recovery_sleep_hours_min: float = Field(
        gt=0, description="Minimum sleep hours for adequate recovery"
    )
    recovery_resting_hr_deviation_max: int = Field(
        gt=0, description="Maximum resting HR deviation above baseline (bpm)"
    )

    @classmethod
    def from_env(cls) -> "TrainingThresholds":
        """
        Load training thresholds from environment variables.

        Environment Variables:
            TSB_FRESH_MIN: Minimum TSB for fresh state (float, default: 10)
            TSB_OPTIMAL_MIN: Minimum TSB for optimal state (float, default: -5)
            TSB_FATIGUED_MIN: Minimum TSB for fatigued state (float, default: -15)
            TSB_CRITICAL: Critical TSB threshold (float, default: -25)
            ATL_CTL_RATIO_OPTIMAL: Optimal ratio (float, default: 1.0)
            ATL_CTL_RATIO_WARNING: Warning ratio (float, default: 1.3)
            ATL_CTL_RATIO_CRITICAL: Critical ratio (float, default: 1.8)
            RECOVERY_HRV_THRESHOLD_PERCENT: HRV % threshold (float, default: 90)
            RECOVERY_SLEEP_HOURS_MIN: Min sleep hours (float, default: 7.0)
            RECOVERY_RESTING_HR_DEVIATION_MAX: Max HR deviation (int, default: 10)

        Returns:
            TrainingThresholds: Configured thresholds

        Raises:
            ValueError: If values are invalid
            ValidationError: If values don't meet validation constraints

        Examples:
            >>> thresholds = TrainingThresholds.from_env()
            >>> print(f"Critical TSB: {thresholds.tsb_critical}")
        """
        try:
            return cls(
                tsb_fresh_min=float(os.getenv("TSB_FRESH_MIN", "10")),
                tsb_optimal_min=float(os.getenv("TSB_OPTIMAL_MIN", "-5")),
                tsb_fatigued_min=float(os.getenv("TSB_FATIGUED_MIN", "-15")),
                tsb_critical=float(os.getenv("TSB_CRITICAL", "-25")),
                atl_ctl_ratio_optimal=float(os.getenv("ATL_CTL_RATIO_OPTIMAL", "1.0")),
                atl_ctl_ratio_warning=float(os.getenv("ATL_CTL_RATIO_WARNING", "1.3")),
                atl_ctl_ratio_critical=float(os.getenv("ATL_CTL_RATIO_CRITICAL", "1.8")),
                recovery_hrv_threshold_percent=float(
                    os.getenv("RECOVERY_HRV_THRESHOLD_PERCENT", "90")
                ),
                recovery_sleep_hours_min=float(os.getenv("RECOVERY_SLEEP_HOURS_MIN", "7.0")),
                recovery_resting_hr_deviation_max=int(
                    os.getenv("RECOVERY_RESTING_HR_DEVIATION_MAX", "10")
                ),
            )
        except ValidationError as e:
            raise ValueError(f"Invalid training thresholds configuration: {e}") from e
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError(f"Invalid numeric value in thresholds configuration: {e}") from e
            raise

    def get_tsb_state(self, tsb: float) -> Literal["fresh", "optimal", "fatigued", "overreached"]:
        """
        Determine training state based on TSB value.

        Args:
            tsb: Training Stress Balance value

        Returns:
            str: One of 'fresh', 'optimal', 'fatigued', 'overreached'

        Examples:
            >>> thresholds = TrainingThresholds.from_env()
            >>> thresholds.get_tsb_state(12)
            'fresh'
            >>> thresholds.get_tsb_state(-8)
            'fatigued'
            >>> thresholds.get_tsb_state(-30)
            'overreached'
        """
        if tsb > self.tsb_fresh_min:
            return "fresh"
        elif tsb > self.tsb_optimal_min:
            return "optimal"
        elif tsb > self.tsb_critical:
            return "fatigued"
        else:
            return "overreached"

    def is_tsb_optimal(self, tsb: float) -> bool:
        """
        Check if TSB is in optimal training zone.

        Args:
            tsb: Training Stress Balance value

        Returns:
            bool: True if TSB is in optimal zone

        Examples:
            >>> thresholds = TrainingThresholds.from_env()
            >>> thresholds.is_tsb_optimal(5)
            True
            >>> thresholds.is_tsb_optimal(-30)
            False
        """
        return self.tsb_optimal_min < tsb <= self.tsb_fresh_min

    def get_atl_ctl_ratio_state(self, ratio: float) -> Literal["optimal", "warning", "critical"]:
        """
        Determine training state based on ATL/CTL ratio.

        Args:
            ratio: ATL/CTL ratio value

        Returns:
            str: One of 'optimal', 'warning', 'critical'

        Examples:
            >>> thresholds = TrainingThresholds.from_env()
            >>> thresholds.get_atl_ctl_ratio_state(0.9)
            'optimal'
            >>> thresholds.get_atl_ctl_ratio_state(1.5)
            'warning'
            >>> thresholds.get_atl_ctl_ratio_state(2.0)
            'critical'
        """
        if ratio < self.atl_ctl_ratio_optimal:
            return "optimal"
        elif ratio < self.atl_ctl_ratio_critical:
            return "warning"
        else:
            return "critical"

    def is_overtraining_risk(self, tsb: float, atl_ctl_ratio: float) -> bool:
        """
        Check if athlete is at risk of overtraining.

        Considers both TSB and ATL/CTL ratio to detect overtraining risk.

        Args:
            tsb: Training Stress Balance value
            atl_ctl_ratio: ATL/CTL ratio value

        Returns:
            bool: True if overtraining risk detected

        Examples:
            >>> thresholds = TrainingThresholds.from_env()
            >>> thresholds.is_overtraining_risk(tsb=-30, atl_ctl_ratio=2.0)
            True
            >>> thresholds.is_overtraining_risk(tsb=5, atl_ctl_ratio=0.9)
            False
        """
        critical_tsb = tsb <= self.tsb_critical
        critical_ratio = atl_ctl_ratio >= self.atl_ctl_ratio_critical

        return critical_tsb or critical_ratio
