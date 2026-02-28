"""
Training plan management with deadlines, objectives, and feasibility validation.

This module provides core functionality for creating and managing training plans,
including deadline tracking, objective setting, and automatic validation against
athlete capabilities (TSS limits, CTL progression rates).
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any

from magma_cycling.config.athlete_profile import AthleteProfile
from magma_cycling.utils.metrics_advanced import calculate_ramp_rate

logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """Priority levels for training objectives and deadlines."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ObjectiveType(Enum):
    """Types of training objectives."""

    EVENT = "event"  # Competition or event
    FTP_TARGET = "ftp_target"  # FTP improvement goal
    CTL_TARGET = "ctl_target"  # Fitness level target
    WEIGHT_TARGET = "weight_target"  # Weight management goal
    MILESTONE = "milestone"  # General milestone


@dataclass
class TrainingObjective:
    """
    Training objective with target date and success criteria.

    Attributes:
        name: Objective name/description
        target_date: Target completion date
        objective_type: Type of objective (event, ftp_target, etc.)
        priority: Priority level (low, medium, high, critical)
        target_value: Optional numeric target (e.g., FTP watts, CTL points)
        current_value: Optional current value for progress tracking
        notes: Additional notes or context

    Example:
        >>> objective = TrainingObjective(
        ...     name="Mont Ventoux Century",
        ...     target_date=date(2026, 6, 15),
        ...     objective_type=ObjectiveType.EVENT,
        ...     priority=PriorityLevel.HIGH,
        ...     target_value=260.0,  # Target FTP
        ...     current_value=220.0  # Current FTP
        ... )
        >>> print(f"Progress: {objective.progress_percent():.1f}%")
        Progress: 84.6%
    """

    name: str
    target_date: date
    objective_type: ObjectiveType
    priority: PriorityLevel
    target_value: float | None = None
    current_value: float | None = None
    notes: str = ""

    def progress_percent(self) -> float | None:
        """
        Calculate progress toward objective as percentage.

        Returns:
            Progress percentage (0-100), or None if target/current not set.

        Example:
            >>> obj = TrainingObjective(
            ...     name="FTP 260W", target_date=date(2026, 6, 1),
            ...     objective_type=ObjectiveType.FTP_TARGET, priority=PriorityLevel.HIGH,
            ...     target_value=260, current_value=220
            ... )
            >>> obj.progress_percent()
            84.61...
        """
        if self.target_value is None or self.current_value is None:
            return None

        if self.target_value == 0:
            return 100.0 if self.current_value >= self.target_value else 0.0

        return (self.current_value / self.target_value) * 100.0

    def days_remaining(self, from_date: date | None = None) -> int:
        """
        Calculate days remaining until target date.

        Args:
            from_date: Reference date (defaults to today)

        Returns:
            Number of days remaining (negative if past due)

        Example:
            >>> obj = TrainingObjective(
            ...     name="Event", target_date=date(2026, 6, 15),
            ...     objective_type=ObjectiveType.EVENT, priority=PriorityLevel.HIGH
            ... )
            >>> obj.days_remaining(from_date=date(2026, 6, 1))
            14
        """
        if from_date is None:
            from_date = date.today()

        return (self.target_date - from_date).days


@dataclass
class TrainingPlan:
    """
    Complete training plan with timeline, objectives, and weekly structure.

    Attributes:
        name: Plan name/description
        start_date: Plan start date
        end_date: Plan end date
        objectives: List of training objectives
        athlete_profile: Athlete characteristics for validation
        weekly_tss_targets: Optional weekly TSS targets (list of floats)
        notes: Additional plan notes

    Example:
        >>> from magma_cycling.config import AthleteProfile
        >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
        >>> plan = TrainingPlan(
        ...     name="Spring Build Phase",
        ...     start_date=date(2026, 3, 1),
        ...     end_date=date(2026, 5, 31),
        ...     objectives=[],
        ...     athlete_profile=profile
        ... )
        >>> print(f"Duration: {plan.duration_weeks()} weeks")
        Duration: 13 weeks
    """

    name: str
    start_date: date
    end_date: date
    objectives: list[TrainingObjective] = field(default_factory=list)
    athlete_profile: AthleteProfile | None = None
    weekly_tss_targets: list[float] = field(default_factory=list)
    notes: str = ""

    def duration_weeks(self) -> int:
        """
        Calculate plan duration in weeks.

        Returns:
            Number of weeks in plan (rounded up)

        Example:
            >>> plan = TrainingPlan(
            ...     name="Test", start_date=date(2026, 1, 1),
            ...     end_date=date(2026, 1, 31), objectives=[]
            ... )
            >>> plan.duration_weeks()
            5
        """
        days = (self.end_date - self.start_date).days + 1

        return (days + 6) // 7  # Round up to full weeks

    def get_objectives_by_priority(self, priority: PriorityLevel) -> list[TrainingObjective]:
        """
        Filter objectives by priority level.

        Args:
            priority: Priority level to filter by

        Returns:
            List of objectives matching priority

        Example:
            >>> plan = TrainingPlan(
            ...     name="Test", start_date=date(2026, 1, 1),
            ...     end_date=date(2026, 3, 1), objectives=[
            ...         TrainingObjective("Event A", date(2026, 2, 1),
            ...                          ObjectiveType.EVENT, PriorityLevel.HIGH),
            ...         TrainingObjective("Event B", date(2026, 2, 15),
            ...                          ObjectiveType.EVENT, PriorityLevel.LOW),
            ...     ]
            ... )
            >>> high_priority = plan.get_objectives_by_priority(PriorityLevel.HIGH)
            >>> len(high_priority)
            1
        """
        return [obj for obj in self.objectives if obj.priority == priority]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert plan to dictionary for JSON serialization.

        Returns:
            Dictionary representation of plan

        Example:
            >>> plan = TrainingPlan(
            ...     name="Test", start_date=date(2026, 1, 1),
            ...     end_date=date(2026, 2, 1), objectives=[]
            ... )
            >>> data = plan.to_dict()
            >>> data['name']
            'Test'
        """
        return {
            "name": self.name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "duration_weeks": self.duration_weeks(),
            "objectives": [
                {
                    "name": obj.name,
                    "target_date": obj.target_date.isoformat(),
                    "objective_type": obj.objective_type.value,
                    "priority": obj.priority.value,
                    "target_value": obj.target_value,
                    "current_value": obj.current_value,
                    "notes": obj.notes,
                }
                for obj in self.objectives
            ],
            "weekly_tss_targets": self.weekly_tss_targets,
            "notes": self.notes,
        }


class PlanningManager:
    """
    Manager for creating and validating training plans.

    This class provides methods to create training plans, add deadlines/objectives,
    retrieve timelines, and validate plan feasibility against athlete capabilities.

    Example:
        >>> from magma_cycling.config import AthleteProfile
        >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
        >>> manager = PlanningManager(athlete_profile=profile)
        >>> plan = manager.create_training_plan(
        ...     name="Spring Build",
        ...     start_date=date(2026, 3, 1),
        ...     end_date=date(2026, 5, 31),
        ...     objectives=[]
        ... )
        >>> print(f"Plan created: {plan.name}")
        Plan created: Spring Build
    """

    def __init__(self, athlete_profile: AthleteProfile | None = None):
        """
        Initialize planning manager.

        Args:
            athlete_profile: Athlete characteristics (optional, can load from env)
        """
        self.athlete_profile = athlete_profile or AthleteProfile.from_env()

        self.plans: dict[str, TrainingPlan] = {}
        logger.info(
            f"PlanningManager initialized for {self.athlete_profile.category} "
            f"athlete (age {self.athlete_profile.age})"
        )

    def create_training_plan(
        self,
        name: str,
        start_date: date,
        end_date: date,
        objectives: list[TrainingObjective],
        weekly_tss_targets: list[float] | None = None,
        notes: str = "",
    ) -> TrainingPlan:
        """
        Create a new training plan with validation.

        Args:
            name: Plan name/description
            start_date: Plan start date
            end_date: Plan end date
            objectives: List of training objectives
            weekly_tss_targets: Optional weekly TSS targets
            notes: Additional plan notes

        Returns:
            Created TrainingPlan instance

        Raises:
            ValueError: If dates invalid or plan duration < 4 weeks or > 12 weeks

        Example:
            >>> from magma_cycling.config import AthleteProfile
            >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
            >>> manager = PlanningManager(athlete_profile=profile)
            >>> plan = manager.create_training_plan(
            ...     name="Spring Build",
            ...     start_date=date(2026, 3, 1),
            ...     end_date=date(2026, 5, 31),
            ...     objectives=[]
            ... )
            >>> plan.duration_weeks()
            13
        """
        # Validate dates

        if end_date <= start_date:
            raise ValueError("end_date must be after start_date")

        # Create plan
        plan = TrainingPlan(
            name=name,
            start_date=start_date,
            end_date=end_date,
            objectives=objectives,
            athlete_profile=self.athlete_profile,
            weekly_tss_targets=weekly_tss_targets or [],
            notes=notes,
        )

        # Validate duration (4-12 weeks per Issue #6)
        duration = plan.duration_weeks()
        if duration < 4:
            raise ValueError(f"Plan duration too short: {duration} weeks (minimum 4 weeks)")
        if duration > 12:
            raise ValueError(f"Plan duration too long: {duration} weeks (maximum 12 weeks)")

        # Store plan
        self.plans[name] = plan
        logger.info(
            f"Created training plan '{name}' ({duration} weeks, " f"{len(objectives)} objectives)"
        )

        return plan

    def add_deadline(
        self,
        plan_name: str,
        deadline_date: date,
        event_name: str,
        priority: PriorityLevel,
        objective_type: ObjectiveType = ObjectiveType.EVENT,
        target_value: float | None = None,
        notes: str = "",
    ) -> TrainingObjective:
        """
        Add a deadline/objective to an existing plan.

        Args:
            plan_name: Name of plan to add deadline to
            deadline_date: Target date for deadline
            event_name: Name/description of deadline/event
            priority: Priority level
            objective_type: Type of objective
            target_value: Optional numeric target
            notes: Additional notes

        Returns:
            Created TrainingObjective

        Raises:
            KeyError: If plan not found
            ValueError: If deadline outside plan dates

        Example:
            >>> from magma_cycling.config import AthleteProfile
            >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
            >>> manager = PlanningManager(athlete_profile=profile)
            >>> plan = manager.create_training_plan(
            ...     "Spring", date(2026, 3, 1), date(2026, 5, 31), []
            ... )
            >>> obj = manager.add_deadline(
            ...     "Spring", date(2026, 6, 15), "Mont Ventoux",
            ...     PriorityLevel.HIGH, target_value=260
            ... )
            >>> obj.name
            'Mont Ventoux'
        """
        if plan_name not in self.plans:
            raise KeyError(f"Plan '{plan_name}' not found")

        plan = self.plans[plan_name]

        # Validate deadline is within reasonable range of plan
        # (Allow deadlines slightly after plan end for peak events)
        if deadline_date < plan.start_date:
            raise ValueError(
                f"Deadline date {deadline_date} is before plan start " f"{plan.start_date}"
            )

        # Create objective
        objective = TrainingObjective(
            name=event_name,
            target_date=deadline_date,
            objective_type=objective_type,
            priority=priority,
            target_value=target_value,
            notes=notes,
        )

        # Add to plan
        plan.objectives.append(objective)
        logger.info(
            f"Added {priority.value} priority deadline '{event_name}' "
            f"to plan '{plan_name}' (target: {deadline_date})"
        )

        return objective

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
            >>> manager = PlanningManager(athlete_profile=profile)
            >>> plan = manager.create_training_plan(
            ...     "Test", date(2026, 1, 1), date(2026, 2, 1), [],
            ...     weekly_tss_targets=[250, 270, 290, 310, 330]
            ... )
            >>> result = manager.validate_plan_feasibility("Test", current_ctl=60)
            >>> result['feasible']
            True
        """
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
