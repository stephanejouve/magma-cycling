"""TimelineMixin — plan timeline generation for PlanningManager."""

from datetime import timedelta
from typing import Any


class TimelineMixin:
    """Mixin providing plan timeline generation."""

    def get_plan_timeline(self, plan_name: str) -> dict[str, Any]:
        """
        Get timeline of deadlines and milestones for a plan.

        Args:
            plan_name: Name of plan

        Returns:
            Dictionary with timeline information including:
                - plan_summary: Basic plan info
                - deadlines: List of objectives sorted by date
                - critical_dates: Dates with critical priority objectives
                - weeks_breakdown: Weekly structure with objectives

        Raises:
            KeyError: If plan not found

        Example:
            >>> from magma_cycling.config import AthleteProfile
            >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
            >>> from magma_cycling.planning.planning_manager import PlanningManager
            >>> manager = PlanningManager(athlete_profile=profile)
            >>> plan = manager.create_training_plan(
            ...     "Test", date(2026, 1, 1), date(2026, 2, 1), []
            ... )
            >>> manager.add_deadline(
            ...     "Test", date(2026, 1, 15), "Checkpoint",
            ...     PriorityLevel.MEDIUM
            ... )
            <magma_cycling.planning.planning_manager.TrainingObjective object at ...>
            >>> timeline = manager.get_plan_timeline("Test")
            >>> len(timeline['deadlines'])
            1
        """
        from magma_cycling.planning.planning_manager import PriorityLevel

        if plan_name not in self.plans:
            raise KeyError(f"Plan '{plan_name}' not found")

        plan = self.plans[plan_name]

        # Sort objectives by date
        sorted_objectives = sorted(plan.objectives, key=lambda x: x.target_date)

        # Group objectives by week
        weeks_breakdown = []
        current_date = plan.start_date
        week_num = 1

        while current_date <= plan.end_date:
            week_end = current_date + timedelta(days=6)

            # Find objectives in this week
            week_objectives = [
                obj for obj in sorted_objectives if current_date <= obj.target_date <= week_end
            ]

            weeks_breakdown.append(
                {
                    "week_num": week_num,
                    "start_date": current_date.isoformat(),
                    "end_date": week_end.isoformat(),
                    "objectives": [
                        {
                            "name": obj.name,
                            "date": obj.target_date.isoformat(),
                            "priority": obj.priority.value,
                            "type": obj.objective_type.value,
                        }
                        for obj in week_objectives
                    ],
                }
            )

            current_date = week_end + timedelta(days=1)
            week_num += 1

        # Extract critical dates
        critical_dates = [
            {
                "date": obj.target_date.isoformat(),
                "name": obj.name,
                "type": obj.objective_type.value,
            }
            for obj in sorted_objectives
            if obj.priority == PriorityLevel.CRITICAL
        ]

        return {
            "plan_summary": {
                "name": plan.name,
                "start_date": plan.start_date.isoformat(),
                "end_date": plan.end_date.isoformat(),
                "duration_weeks": plan.duration_weeks(),
                "total_objectives": len(plan.objectives),
            },
            "deadlines": [
                {
                    "name": obj.name,
                    "date": obj.target_date.isoformat(),
                    "priority": obj.priority.value,
                    "type": obj.objective_type.value,
                    "days_remaining": obj.days_remaining(),
                }
                for obj in sorted_objectives
            ],
            "critical_dates": critical_dates,
            "weeks_breakdown": weeks_breakdown,
        }
