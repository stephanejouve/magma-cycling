"""Tests for calendar module (Sprint R3 Module 2)."""

from datetime import date

import pytest

from cyclisme_training_logs.config.athlete_profile import AthleteProfile
from cyclisme_training_logs.planning.calendar import (
    TrainingCalendar,
    TrainingSession,
    WeeklySummary,
    WorkoutType,
)


class TestTrainingSession:
    """Tests for TrainingSession dataclass."""

    def test_get_effective_tss_completed(self):
        """Test effective TSS returns actual TSS when completed."""
        session = TrainingSession(
            date=date(2026, 1, 15),
            workout_type=WorkoutType.ENDURANCE,
            planned_tss=50.0,
            completed=True,
            actual_tss=48.0,
        )

        assert session.get_effective_tss() == 48.0

    def test_get_effective_tss_not_completed(self):
        """Test effective TSS returns planned TSS when not completed."""
        session = TrainingSession(
            date=date(2026, 1, 15),
            workout_type=WorkoutType.THRESHOLD,
            planned_tss=85.0,
            completed=False,
        )

        assert session.get_effective_tss() == 85.0

    def test_to_dict_serialization(self):
        """Test session serialization to dictionary."""
        session = TrainingSession(
            date=date(2026, 1, 15),
            workout_type=WorkoutType.VO2MAX,
            planned_tss=95.0,
            duration_min=60,
            intensity_pct=110.0,
            notes="Hard intervals",
        )

        data = session.to_dict()

        assert data["date"] == "2026-01-15"
        assert data["workout_type"] == "vo2max"
        assert data["planned_tss"] == 95.0
        assert data["duration_min"] == 60
        assert data["intensity_pct"] == 110.0
        assert data["notes"] == "Hard intervals"


class TestWeeklySummary:
    """Tests for WeeklySummary dataclass."""

    def test_to_dict_serialization(self):
        """Test summary serialization to dictionary."""
        summary = WeeklySummary(
            week_num=3,
            year=2026,
            start_date=date(2026, 1, 13),
            end_date=date(2026, 1, 19),
            total_tss=285.0,
            sessions_count=5,
            rest_days_count=2,
            tss_by_type={"endurance": 120.0, "threshold": 85.0, "vo2max": 80.0},
            avg_intensity=85.5,
        )

        data = summary.to_dict()

        assert data["week_num"] == 3
        assert data["year"] == 2026
        assert data["total_tss"] == 285.0
        assert data["sessions_count"] == 5
        assert data["rest_days_count"] == 2
        assert len(data["tss_by_type"]) == 3


class TestTrainingCalendar:
    """Tests for TrainingCalendar class."""

    @pytest.fixture
    def master_profile(self):
        """Master athlete profile (54 years)."""
        return AthleteProfile(
            age=54,
            category="master",
            recovery_capacity="good",
            sleep_dependent=True,
            ftp=220,
            weight=83.8,
        )

    @pytest.fixture
    def senior_profile(self):
        """Senior athlete profile."""
        return AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="good",
            sleep_dependent=False,
            ftp=250,
            weight=75.0,
        )

    @pytest.fixture
    def calendar(self, master_profile):
        """Training calendar for 2026."""
        return TrainingCalendar(year=2026, athlete_profile=master_profile)

    def test_initialization_master_athlete(self, master_profile):
        """Test calendar initialization with master athlete defaults."""
        calendar = TrainingCalendar(year=2026, athlete_profile=master_profile)

        assert calendar.year == 2026
        assert calendar.start_week == 1
        assert calendar.rest_days == [6]  # Sunday for master
        assert len(calendar.sessions) == 0

    def test_initialization_senior_athlete(self, senior_profile):
        """Test calendar initialization with senior athlete (no mandatory rest)."""
        calendar = TrainingCalendar(year=2026, athlete_profile=senior_profile)

        assert calendar.year == 2026
        assert calendar.rest_days == []  # No mandatory rest for senior

    def test_generate_weekly_calendar_week_3(self, calendar):
        """Test generating week 3 (ISO week) calendar."""
        week_dates = calendar.generate_weekly_calendar(week_num=3)

        assert len(week_dates) == 7
        assert week_dates[0].weekday() == 0  # Monday
        assert week_dates[6].weekday() == 6  # Sunday

        # Verify ISO week consistency
        year, week, _ = week_dates[0].isocalendar()
        assert year == 2026
        assert week == 3

    def test_generate_weekly_calendar_week_1(self, calendar):
        """Test generating week 1 calendar (contains Jan 4)."""
        week_dates = calendar.generate_weekly_calendar(week_num=1)

        assert len(week_dates) == 7
        # Week 1 must contain January 4
        assert any(d.month == 1 and d.day == 4 for d in week_dates)

    def test_generate_weekly_calendar_invalid_week(self, calendar):
        """Test error on invalid week number."""
        with pytest.raises(ValueError, match="Invalid week_num"):
            calendar.generate_weekly_calendar(week_num=0)

        with pytest.raises(ValueError, match="Invalid week_num"):
            calendar.generate_weekly_calendar(week_num=54)

    def test_mark_rest_days_single_day(self, calendar):
        """Test marking single rest day."""
        calendar.mark_rest_days([6])  # Sunday only

        assert calendar.rest_days == [6]

    def test_mark_rest_days_multiple_days(self, calendar):
        """Test marking multiple rest days."""
        calendar.mark_rest_days([3, 6])  # Wednesday + Sunday

        assert calendar.rest_days == [3, 6]

    def test_mark_rest_days_invalid_weekday(self, calendar):
        """Test error on invalid weekday number."""
        with pytest.raises(ValueError, match="Invalid weekday number"):
            calendar.mark_rest_days([7])  # Invalid (0-6 only)

        with pytest.raises(ValueError, match="Invalid weekday number"):
            calendar.mark_rest_days([-1])

    def test_mark_rest_days_removes_duplicates(self, calendar):
        """Test marking rest days removes duplicates."""
        calendar.mark_rest_days([6, 3, 6, 3])  # Duplicates

        assert calendar.rest_days == [3, 6]  # Sorted, no duplicates

    def test_add_session_success(self, calendar):
        """Test adding session to calendar."""
        session = calendar.add_session(
            session_date=date(2026, 1, 12),  # Monday, Week 3
            workout_type=WorkoutType.THRESHOLD,
            planned_tss=85.0,
            duration_min=90,
            intensity_pct=95.0,
            notes="FTP intervals",
        )

        assert session.date == date(2026, 1, 12)
        assert session.workout_type == WorkoutType.THRESHOLD
        assert session.planned_tss == 85.0
        assert date(2026, 1, 12) in calendar.sessions

    def test_add_session_on_rest_day_fails(self, calendar):
        """Test adding session on configured rest day fails."""
        calendar.mark_rest_days([6])  # Sunday

        with pytest.raises(ValueError, match="configured as rest day"):
            calendar.add_session(
                session_date=date(2026, 1, 18),  # Sunday of week 3
                workout_type=WorkoutType.ENDURANCE,
                planned_tss=50.0,
            )

    def test_add_session_overwrites_existing(self, calendar):
        """Test adding session on same date overwrites existing."""
        # Add first session

        calendar.add_session(
            session_date=date(2026, 1, 12),
            workout_type=WorkoutType.ENDURANCE,
            planned_tss=60.0,
        )

        # Overwrite with second session
        calendar.add_session(
            session_date=date(2026, 1, 12),
            workout_type=WorkoutType.THRESHOLD,
            planned_tss=85.0,
        )

        assert len(calendar.sessions) == 1
        assert calendar.sessions[date(2026, 1, 12)].planned_tss == 85.0
        assert calendar.sessions[date(2026, 1, 12)].workout_type == WorkoutType.THRESHOLD

    def test_get_week_summary_empty_week(self, calendar):
        """Test getting summary for week with no sessions."""
        summary = calendar.get_week_summary(week_num=3)

        assert summary.week_num == 3
        assert summary.year == 2026
        assert summary.total_tss == 0.0
        assert summary.sessions_count == 0
        assert summary.avg_intensity == 0.0
        assert len(summary.tss_by_type) == 0

    def test_get_week_summary_with_sessions(self, calendar):
        """Test getting summary for week with sessions."""
        calendar.mark_rest_days([6])  # Sunday

        # Add sessions to week 3 (Jan 12-18)
        calendar.add_session(date(2026, 1, 12), WorkoutType.ENDURANCE, 60.0, 90, 70.0)  # Monday
        calendar.add_session(date(2026, 1, 14), WorkoutType.THRESHOLD, 85.0, 90, 95.0)  # Wednesday
        calendar.add_session(date(2026, 1, 16), WorkoutType.VO2MAX, 95.0, 60, 110.0)  # Friday

        summary = calendar.get_week_summary(week_num=3)

        assert summary.total_tss == 240.0  # 60 + 85 + 95
        assert summary.sessions_count == 3
        assert summary.rest_days_count == 1  # Sunday
        assert summary.tss_by_type["endurance"] == 60.0
        assert summary.tss_by_type["threshold"] == 85.0
        assert summary.tss_by_type["vo2max"] == 95.0
        assert abs(summary.avg_intensity - 91.67) < 0.1  # (70+95+110)/3

    def test_get_week_summary_completed_sessions(self, calendar):
        """Test summary uses actual TSS for completed sessions."""
        # Add session

        calendar.add_session(date(2026, 1, 12), WorkoutType.ENDURANCE, 60.0, 90, 70.0)

        # Mark as completed with different actual TSS
        session = calendar.sessions[date(2026, 1, 12)]
        session.completed = True
        session.actual_tss = 55.0  # Slightly less than planned

        summary = calendar.get_week_summary(week_num=3)

        assert summary.total_tss == 55.0  # Actual, not planned

    def test_get_week_summary_dates_correct(self, calendar):
        """Test summary has correct start/end dates."""
        summary = calendar.get_week_summary(week_num=3)

        # Week 3 of 2026 should start on Monday Jan 12
        assert summary.start_date == date(2026, 1, 12)
        assert summary.end_date == date(2026, 1, 18)
        assert summary.start_date.weekday() == 0  # Monday
        assert summary.end_date.weekday() == 6  # Sunday
