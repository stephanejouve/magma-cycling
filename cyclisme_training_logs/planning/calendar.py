"""
Training calendar with weekly structure and session management.

This module provides tools for generating weekly training calendars,
managing rest days, adding sessions, and calculating weekly TSS summaries.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any

from cyclisme_training_logs.config.athlete_profile import AthleteProfile

logger = logging.getLogger(__name__)


class WorkoutType(Enum):
    """Types of training workouts."""

    ENDURANCE = "endurance"  # Z2 base training
    TEMPO = "tempo"  # Z3 sustained efforts
    THRESHOLD = "threshold"  # Z4 FTP intervals
    VO2MAX = "vo2max"  # Z5 high intensity
    RECOVERY = "recovery"  # Z1 active recovery
    REST = "rest"  # Complete rest day


@dataclass
class TrainingSession:
    """
    Single training session with workout details.

    Attributes:
        date: Session date
        workout_type: Type of workout
        planned_tss: Planned Training Stress Score
        duration_min: Planned duration in minutes
        intensity_pct: Target intensity (% FTP)
        completed: Whether session was completed
        actual_tss: Actual TSS if completed
        notes: Additional session notes

    Example:
        >>> session = TrainingSession(
        ...     date=date(2026, 1, 15),
        ...     workout_type=WorkoutType.THRESHOLD,
        ...     planned_tss=85.0,
        ...     duration_min=90,
        ...     intensity_pct=95.0
        ... )
        >>> print(f"{session.workout_type.value}: {session.planned_tss} TSS")
        threshold: 85.0 TSS
    """

    date: date
    workout_type: WorkoutType
    planned_tss: float
    duration_min: int = 60
    intensity_pct: float = 70.0
    completed: bool = False
    actual_tss: float | None = None
    notes: str = ""

    def get_effective_tss(self) -> float:
        """
        Get effective TSS (actual if completed, planned otherwise).

        Returns:
            Actual TSS if completed, planned TSS otherwise

        Example:
            >>> session = TrainingSession(
            ...     date=date(2026, 1, 15), workout_type=WorkoutType.ENDURANCE,
            ...     planned_tss=50.0, completed=True, actual_tss=48.0
            ... )
            >>> session.get_effective_tss()
            48.0
        """
        return self.actual_tss if self.completed and self.actual_tss else self.planned_tss

    def to_dict(self) -> dict[str, Any]:
        """
        Convert session to dictionary for serialization.

        Returns:
            Dictionary representation

        Example:
            >>> session = TrainingSession(
            ...     date=date(2026, 1, 15), workout_type=WorkoutType.TEMPO,
            ...     planned_tss=65.0, duration_min=75
            ... )
            >>> data = session.to_dict()
            >>> data['workout_type']
            'tempo'
        """
        return {
            "date": self.date.isoformat(),
            "workout_type": self.workout_type.value,
            "planned_tss": self.planned_tss,
            "duration_min": self.duration_min,
            "intensity_pct": self.intensity_pct,
            "completed": self.completed,
            "actual_tss": self.actual_tss,
            "notes": self.notes,
        }


@dataclass
class WeeklySummary:
    """
    Weekly training summary with TSS breakdown.

    Attributes:
        week_num: ISO week number
        year: Year
        start_date: Week start date (Monday)
        end_date: Week end date (Sunday)
        total_tss: Total TSS for week
        sessions_count: Number of sessions
        rest_days_count: Number of rest days
        tss_by_type: TSS breakdown by workout type
        avg_intensity: Average intensity (% FTP)

    Example:
        >>> summary = WeeklySummary(
        ...     week_num=3, year=2026, start_date=date(2026, 1, 13),
        ...     end_date=date(2026, 1, 19), total_tss=285.0,
        ...     sessions_count=5, rest_days_count=2,
        ...     tss_by_type={"endurance": 120.0, "threshold": 85.0, "vo2max": 80.0}
        ... )
        >>> print(f"Week {summary.week_num}: {summary.total_tss} TSS")
        Week 3: 285.0 TSS
    """

    week_num: int
    year: int
    start_date: date
    end_date: date
    total_tss: float = 0.0
    sessions_count: int = 0
    rest_days_count: int = 0
    tss_by_type: dict[str, float] = field(default_factory=dict)
    avg_intensity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert summary to dictionary.

        Returns:
            Dictionary representation

        Example:
            >>> summary = WeeklySummary(3, 2026, date(2026, 1, 13),
            ...                         date(2026, 1, 19), total_tss=250.0)
            >>> data = summary.to_dict()
            >>> data['week_num']
            3
        """
        return {
            "week_num": self.week_num,
            "year": self.year,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_tss": self.total_tss,
            "sessions_count": self.sessions_count,
            "rest_days_count": self.rest_days_count,
            "tss_by_type": self.tss_by_type,
            "avg_intensity": self.avg_intensity,
        }


class TrainingCalendar:
    """
    Training calendar with weekly structure and session management.

    Manages training sessions across weeks with automatic rest day handling,
    TSS tracking, and weekly summaries.

    Example:
        >>> from cyclisme_training_logs.config import AthleteProfile
        >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
        >>> calendar = TrainingCalendar(year=2026, athlete_profile=profile)
        >>> calendar.mark_rest_days([6])  # Sunday
        >>> week_dates = calendar.generate_weekly_calendar(week_num=3)
        >>> len(week_dates)
        7
    """

    def __init__(
        self,
        year: int,
        start_week: int = 1,
        athlete_profile: AthleteProfile | None = None,
    ):
        """
        Initialize training calendar.

        Args:
            year: Calendar year
            start_week: Starting ISO week number (default: 1)
            athlete_profile: Athlete characteristics (optional, loads from env)

        Example:
            >>> from cyclisme_training_logs.config import AthleteProfile
            >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
            >>> calendar = TrainingCalendar(year=2026, athlete_profile=profile)
            >>> calendar.year
            2026
        """
        self.year = year
        self.start_week = start_week
        self.athlete_profile = athlete_profile or AthleteProfile.from_env()

        # In-memory storage for sessions (date -> TrainingSession)
        self.sessions: dict[date, TrainingSession] = {}

        # Rest days configuration (0=Monday, 6=Sunday)
        # Master athletes: Sunday (6) mandatory
        self.rest_days: list[int] = [6] if self.athlete_profile.category == "master" else []

        logger.info(
            f"TrainingCalendar initialized for {year} "
            f"({self.athlete_profile.category} athlete, "
            f"rest days: {self.rest_days})"
        )

    def generate_weekly_calendar(self, week_num: int) -> list[date]:
        """
        Generate list of dates for a specific ISO week.

        Args:
            week_num: ISO week number (1-53)

        Returns:
            List of 7 dates (Monday to Sunday) for the week

        Raises:
            ValueError: If week_num invalid for year

        Example:
            >>> from cyclisme_training_logs.config import AthleteProfile
            >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
            >>> calendar = TrainingCalendar(year=2026, athlete_profile=profile)
            >>> week_dates = calendar.generate_weekly_calendar(week_num=3)
            >>> len(week_dates)
            7
            >>> week_dates[0].weekday()  # Monday
            0
            >>> week_dates[6].weekday()  # Sunday
            6
        """
        if week_num < 1 or week_num > 53:
            raise ValueError(f"Invalid week_num: {week_num} (must be 1-53)")

        # Find first day of ISO week 1 for this year
        jan4 = date(self.year, 1, 4)  # ISO week 1 always contains Jan 4
        week1_monday = jan4 - timedelta(days=jan4.weekday())

        # Calculate Monday of target week
        target_monday = week1_monday + timedelta(weeks=week_num - 1)

        # Verify year consistency
        target_year, target_week, _ = target_monday.isocalendar()
        if target_year != self.year or target_week != week_num:
            raise ValueError(f"Week {week_num} does not exist in year {self.year}")

        # Generate 7 days (Monday to Sunday)
        week_dates = [target_monday + timedelta(days=i) for i in range(7)]

        logger.debug(
            f"Generated week {week_num}/{self.year}: " f"{week_dates[0]} to {week_dates[6]}"
        )

        return week_dates

    def mark_rest_days(self, days: list[int] | None = None) -> None:
        """
        Configure rest days for calendar.

        Args:
            days: List of weekday numbers (0=Monday, 6=Sunday).
                  If None, uses defaults (Sunday for master athletes).

        Raises:
            ValueError: If invalid weekday number (not 0-6)

        Example:
            >>> from cyclisme_training_logs.config import AthleteProfile
            >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
            >>> calendar = TrainingCalendar(year=2026, athlete_profile=profile)
            >>> calendar.mark_rest_days([6])  # Sunday only
            >>> calendar.rest_days
            [6]
            >>> calendar.mark_rest_days([3, 6])  # Wednesday + Sunday
            >>> calendar.rest_days
            [3, 6]
        """
        if days is None:
            # Defaults: Sunday for master athletes
            days = [6] if self.athlete_profile.category == "master" else []

        # Validate weekday numbers
        for day in days:
            if day < 0 or day > 6:
                raise ValueError(
                    f"Invalid weekday number: {day} (must be 0-6, " f"0=Monday, 6=Sunday)"
                )

        self.rest_days = sorted(set(days))  # Remove duplicates, sort

        logger.info(
            f"Rest days configured: {self.rest_days} "
            f"({', '.join(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d] for d in self.rest_days)})"
        )

    def add_session(
        self,
        session_date: date,
        workout_type: WorkoutType,
        planned_tss: float,
        duration_min: int = 60,
        intensity_pct: float = 70.0,
        notes: str = "",
    ) -> TrainingSession:
        """
        Add training session to calendar.

        Args:
            session_date: Date of session
            workout_type: Type of workout
            planned_tss: Planned TSS
            duration_min: Duration in minutes (default: 60)
            intensity_pct: Target intensity % FTP (default: 70)
            notes: Additional notes

        Returns:
            Created TrainingSession

        Raises:
            ValueError: If session_date is a configured rest day

        Example:
            >>> from cyclisme_training_logs.config import AthleteProfile
            >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
            >>> calendar = TrainingCalendar(year=2026, athlete_profile=profile)
            >>> calendar.mark_rest_days([6])
            >>> session = calendar.add_session(
            ...     session_date=date(2026, 1, 13),  # Monday
            ...     workout_type=WorkoutType.THRESHOLD,
            ...     planned_tss=85.0,
            ...     duration_min=90,
            ...     intensity_pct=95.0
            ... )
            >>> session.planned_tss
            85.0
        """
        # Check if date is configured rest day
        weekday = session_date.weekday()
        if weekday in self.rest_days:
            raise ValueError(
                f"Cannot add session on {session_date.strftime('%A')} "
                f"({session_date}): configured as rest day"
            )

        # Create session
        session = TrainingSession(
            date=session_date,
            workout_type=workout_type,
            planned_tss=planned_tss,
            duration_min=duration_min,
            intensity_pct=intensity_pct,
            notes=notes,
        )

        # Store in calendar (overwrites if already exists)
        self.sessions[session_date] = session

        logger.info(
            f"Added session: {session_date} - {workout_type.value} "
            f"({planned_tss} TSS, {duration_min}min)"
        )

        return session

    def get_week_summary(self, week_num: int) -> WeeklySummary:
        """
        Calculate weekly training summary with TSS breakdown.

        Args:
            week_num: ISO week number

        Returns:
            WeeklySummary with totals and breakdown

        Example:
            >>> from cyclisme_training_logs.config import AthleteProfile
            >>> profile = AthleteProfile(age=54, category="master", ftp=220, weight=83.8)
            >>> calendar = TrainingCalendar(year=2026, athlete_profile=profile)
            >>> calendar.add_session(
            ...     date(2026, 1, 13), WorkoutType.ENDURANCE, 60.0, 90, 70.0
            ... )
            <cyclisme_training_logs.planning.calendar.TrainingSession object at ...>
            >>> calendar.add_session(
            ...     date(2026, 1, 15), WorkoutType.THRESHOLD, 85.0, 90, 95.0
            ... )
            <cyclisme_training_logs.planning.calendar.TrainingSession object at ...>
            >>> summary = calendar.get_week_summary(week_num=3)
            >>> summary.total_tss
            145.0
            >>> summary.sessions_count
            2
        """
        # Generate week dates
        week_dates = self.generate_weekly_calendar(week_num)
        start_date = week_dates[0]
        end_date = week_dates[6]

        # Initialize summary
        total_tss = 0.0
        sessions_count = 0
        rest_days_count = 0
        tss_by_type: dict[str, float] = {}
        total_intensity = 0.0

        # Collect sessions for this week
        for day_date in week_dates:
            if day_date in self.sessions:
                session = self.sessions[day_date]
                effective_tss = session.get_effective_tss()

                total_tss += effective_tss
                sessions_count += 1
                total_intensity += session.intensity_pct

                # Accumulate by type
                workout_type_key = session.workout_type.value
                tss_by_type[workout_type_key] = (
                    tss_by_type.get(workout_type_key, 0.0) + effective_tss
                )
            elif day_date.weekday() in self.rest_days:
                rest_days_count += 1

        # Calculate average intensity
        avg_intensity = total_intensity / sessions_count if sessions_count > 0 else 0.0

        summary = WeeklySummary(
            week_num=week_num,
            year=self.year,
            start_date=start_date,
            end_date=end_date,
            total_tss=total_tss,
            sessions_count=sessions_count,
            rest_days_count=rest_days_count,
            tss_by_type=tss_by_type,
            avg_intensity=avg_intensity,
        )

        logger.info(
            f"Week {week_num} summary: {total_tss:.1f} TSS, "
            f"{sessions_count} sessions, {rest_days_count} rest days"
        )

        return summary
