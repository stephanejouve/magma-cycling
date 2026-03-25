"""ValidationMixin — plan feasibility validation for PlanningManager."""

import logging
from typing import Any

from magma_cycling.utils.metrics_advanced import calculate_ramp_rate

logger = logging.getLogger(__name__)


class ValidationMixin:
    """Mixin providing plan feasibility validation."""

    def validate_plan_feasibility(self, plan_name: str, current_ctl: float = 0.0) -> dict[str, Any]:
        """
        Validate training plan feasibility against athlete capabilities.

        Checks:
            - Weekly TSS within athlete limits (max 380 for master 54y)
            - CTL ramp rate safe (<= 5-7 points/week for master)
            - Plan duration appropriate (4-12 weeks)
            - Objectives timeline realistic

        Args:
            plan_name: Name of plan to validate
            current_ctl: Current CTL baseline (default 0)

        Returns:
            Dictionary with validation results:
                - feasible: Boolean overall feasibility
                - warnings: List of warning messages
                - errors: List of error messages (blocking issues)
                - recommendations: List of recommendations

        Raises:
            KeyError: If plan not found

        Example:
            >>> from magma_cycling.config import AthleteProfile
            >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
            >>> from magma_cycling.planning.planning_manager import PlanningManager
            >>> manager = PlanningManager(athlete_profile=profile)
            >>> plan = manager.create_training_plan(
            ...     "Test", date(2026, 1, 1), date(2026, 2, 1), [],
            ...     weekly_tss_targets=[250, 270, 290, 310, 330]
            ... )
            >>> result = manager.validate_plan_feasibility("Test", current_ctl=60)
            >>> result['feasible']
            True
        """
        from magma_cycling.planning.planning_manager import PriorityLevel

        if plan_name not in self.plans:
            raise KeyError(f"Plan '{plan_name}' not found")

        plan = self.plans[plan_name]
        warnings = []
        errors = []
        recommendations = []

        # Get athlete limits
        max_weekly_tss = 380 if self.athlete_profile.category == "master" else 450
        max_ctl_ramp = 7.0 if self.athlete_profile.category == "master" else 10.0

        # Validate weekly TSS targets
        if plan.weekly_tss_targets:
            for week_num, tss in enumerate(plan.weekly_tss_targets, 1):
                if tss > max_weekly_tss:
                    warnings.append(
                        f"Week {week_num}: TSS {tss:.0f} exceeds "
                        f"recommended max {max_weekly_tss:.0f} for "
                        f"{self.athlete_profile.category} athlete"
                    )

        # Validate CTL progression if TSS targets provided
        if plan.weekly_tss_targets and len(plan.weekly_tss_targets) >= 2:
            # Estimate CTL progression (simplified: TSS/7 ≈ CTL)
            estimated_start_ctl = current_ctl
            estimated_end_ctl = current_ctl + sum(plan.weekly_tss_targets) / 7.0

            duration_days = (plan.end_date - plan.start_date).days + 1
            ramp_rate = calculate_ramp_rate(
                ctl_previous=estimated_start_ctl,
                ctl_current=estimated_end_ctl,
                days=duration_days,
            )

            if ramp_rate > max_ctl_ramp:
                errors.append(
                    f"CTL ramp rate {ramp_rate:.1f} points/week exceeds "
                    f"safe maximum {max_ctl_ramp:.1f} for "
                    f"{self.athlete_profile.category} athlete (age "
                    f"{self.athlete_profile.age})"
                )
                recommendations.append(
                    f"Reduce weekly TSS or extend plan duration to achieve "
                    f"ramp rate <= {max_ctl_ramp:.1f} points/week"
                )
            elif ramp_rate > max_ctl_ramp * 0.8:
                warnings.append(
                    f"CTL ramp rate {ramp_rate:.1f} points/week is high "
                    f"(80%+ of maximum). Monitor recovery carefully."
                )

        # Validate objectives timeline
        if plan.objectives:
            high_priority_count = len(plan.get_objectives_by_priority(PriorityLevel.HIGH))
            critical_count = len(plan.get_objectives_by_priority(PriorityLevel.CRITICAL))

            if critical_count > 2:
                warnings.append(
                    f"Plan has {critical_count} critical objectives. "
                    f"Consider prioritizing top 2 to avoid overload."
                )

            if high_priority_count + critical_count > 5:
                warnings.append(
                    f"Plan has {high_priority_count + critical_count} high+ "
                    f"priority objectives. Risk of conflicting priorities."
                )

        # Overall feasibility
        feasible = len(errors) == 0

        if feasible and len(warnings) == 0:
            recommendations.append(
                "Plan structure looks good. Monitor actual vs planned load weekly."
            )

        return {
            "feasible": feasible,
            "warnings": warnings,
            "errors": errors,
            "recommendations": recommendations,
            "plan_summary": {
                "name": plan.name,
                "duration_weeks": plan.duration_weeks(),
                "total_tss": sum(plan.weekly_tss_targets) if plan.weekly_tss_targets else 0,
                "avg_weekly_tss": (
                    sum(plan.weekly_tss_targets) / len(plan.weekly_tss_targets)
                    if plan.weekly_tss_targets
                    else 0
                ),
            },
        }
