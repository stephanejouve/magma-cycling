"""Tests for planning_manager module (Sprint R3)."""

from datetime import date

import pytest

from magma_cycling.config.athlete_profile import AthleteProfile
from magma_cycling.planning.planning_manager import (
    ObjectiveType,
    PlanningManager,
    PriorityLevel,
    TrainingObjective,
    TrainingPlan,
)


class TestTrainingObjective:
    """Tests for TrainingObjective dataclass."""

    def test_progress_percent_with_values(self):
        """Test progress calculation when target and current values are set."""
        obj = TrainingObjective(
            name="FTP 260W",
            target_date=date(2026, 6, 1),
            objective_type=ObjectiveType.FTP_TARGET,
            priority=PriorityLevel.HIGH,
            target_value=260.0,
            current_value=220.0,
        )

        progress = obj.progress_percent()
        assert progress is not None
        assert abs(progress - 84.615) < 0.01  # 220/260 * 100 ≈ 84.615%

    def test_progress_percent_without_values(self):
        """Test progress calculation when values not set."""
        obj = TrainingObjective(
            name="Event",
            target_date=date(2026, 6, 1),
            objective_type=ObjectiveType.EVENT,
            priority=PriorityLevel.HIGH,
        )

        assert obj.progress_percent() is None

    def test_days_remaining_future(self):
        """Test days remaining calculation for future date."""
        obj = TrainingObjective(
            name="Event",
            target_date=date(2026, 6, 15),
            objective_type=ObjectiveType.EVENT,
            priority=PriorityLevel.HIGH,
        )

        days = obj.days_remaining(from_date=date(2026, 6, 1))
        assert days == 14

    def test_days_remaining_past(self):
        """Test days remaining calculation for past date (negative)."""
        obj = TrainingObjective(
            name="Event",
            target_date=date(2026, 6, 1),
            objective_type=ObjectiveType.EVENT,
            priority=PriorityLevel.HIGH,
        )

        days = obj.days_remaining(from_date=date(2026, 6, 15))
        assert days == -14


class TestTrainingPlan:
    """Tests for TrainingPlan dataclass."""

    @pytest.fixture
    def sample_profile(self):
        """Sample athlete profile."""
        return AthleteProfile(
            age=54,
            category="master",
            recovery_capacity="good",
            sleep_dependent=True,
            ftp=220,
            ftp_target=240,
            weight=83.8,
        )

    def test_duration_weeks_exact(self):
        """Test duration calculation for exact weeks."""
        plan = TrainingPlan(
            name="Test Plan",
            start_date=date(2026, 1, 1),  # Thursday
            end_date=date(2026, 1, 28),  # Wednesday (28 days = 4 weeks)
            objectives=[],
        )

        assert plan.duration_weeks() == 4

    def test_duration_weeks_partial(self):
        """Test duration calculation rounds up partial weeks."""
        plan = TrainingPlan(
            name="Test Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),  # 31 days = 5 weeks (rounded up)
            objectives=[],
        )

        assert plan.duration_weeks() == 5

    def test_get_objectives_by_priority(self, sample_profile):
        """Test filtering objectives by priority."""
        objectives = [
            TrainingObjective(
                "Event A",
                date(2026, 2, 1),
                ObjectiveType.EVENT,
                PriorityLevel.HIGH,
            ),
            TrainingObjective(
                "Event B",
                date(2026, 2, 15),
                ObjectiveType.EVENT,
                PriorityLevel.LOW,
            ),
            TrainingObjective(
                "Event C",
                date(2026, 3, 1),
                ObjectiveType.EVENT,
                PriorityLevel.HIGH,
            ),
        ]

        plan = TrainingPlan(
            name="Test Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            objectives=objectives,
            athlete_profile=sample_profile,
        )

        high_priority = plan.get_objectives_by_priority(PriorityLevel.HIGH)
        assert len(high_priority) == 2
        assert all(obj.priority == PriorityLevel.HIGH for obj in high_priority)

        low_priority = plan.get_objectives_by_priority(PriorityLevel.LOW)
        assert len(low_priority) == 1

    def test_to_dict_serialization(self):
        """Test plan serialization to dictionary."""
        plan = TrainingPlan(
            name="Test Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            objectives=[
                TrainingObjective(
                    "Event A",
                    date(2026, 1, 15),
                    ObjectiveType.EVENT,
                    PriorityLevel.HIGH,
                    target_value=260.0,
                )
            ],
            weekly_tss_targets=[250, 270, 290, 310],
            notes="Test plan notes",
        )

        data = plan.to_dict()

        assert data["name"] == "Test Plan"
        assert data["start_date"] == "2026-01-01"
        assert data["end_date"] == "2026-02-01"
        assert len(data["objectives"]) == 1
        assert data["objectives"][0]["name"] == "Event A"
        assert data["weekly_tss_targets"] == [250, 270, 290, 310]


class TestPlanningManager:
    """Tests for PlanningManager class."""

    @pytest.fixture
    def sample_profile(self):
        """Sample athlete profile."""
        return AthleteProfile(
            age=54,
            category="master",
            recovery_capacity="good",
            sleep_dependent=True,
            ftp=220,
            ftp_target=240,
            weight=83.8,
        )

    @pytest.fixture
    def manager(self, sample_profile):
        """Planning manager instance."""
        return PlanningManager(athlete_profile=sample_profile)

    def test_create_training_plan_success(self, manager):
        """Test successful plan creation."""
        plan = manager.create_training_plan(
            name="Spring Build",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 5, 15),  # ~11 weeks (within 4-12 limit)
            objectives=[],
            notes="Test plan",
        )

        assert plan.name == "Spring Build"
        assert plan.start_date == date(2026, 3, 1)
        assert plan.end_date == date(2026, 5, 15)
        assert plan.duration_weeks() == 11
        assert "Spring Build" in manager.plans

    def test_create_training_plan_invalid_dates(self, manager):
        """Test plan creation fails with invalid dates."""
        with pytest.raises(ValueError, match="end_date must be after start_date"):
            manager.create_training_plan(
                name="Invalid Plan",
                start_date=date(2026, 5, 31),
                end_date=date(2026, 3, 1),  # Before start
                objectives=[],
            )

    def test_create_training_plan_too_short(self, manager):
        """Test plan creation fails if duration < 4 weeks."""
        with pytest.raises(ValueError, match="too short.*minimum 4 weeks"):
            manager.create_training_plan(
                name="Too Short",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 14),  # Only 2 weeks
                objectives=[],
            )

    def test_create_training_plan_too_long(self, manager):
        """Test plan creation fails if duration > 12 weeks."""
        with pytest.raises(ValueError, match="too long.*maximum 12 weeks"):
            manager.create_training_plan(
                name="Too Long",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 6, 1),  # ~22 weeks
                objectives=[],
            )

    def test_add_deadline_success(self, manager):
        """Test adding deadline to existing plan."""
        plan = manager.create_training_plan(
            name="Spring Build",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 5, 15),  # ~11 weeks
            objectives=[],
        )

        objective = manager.add_deadline(
            plan_name="Spring Build",
            deadline_date=date(2026, 6, 15),
            event_name="Mont Ventoux Century",
            priority=PriorityLevel.HIGH,
            objective_type=ObjectiveType.EVENT,
            target_value=260.0,
            notes="Target FTP 260W",
        )

        assert objective.name == "Mont Ventoux Century"
        assert objective.target_date == date(2026, 6, 15)
        assert objective.priority == PriorityLevel.HIGH
        assert len(plan.objectives) == 1

    def test_add_deadline_plan_not_found(self, manager):
        """Test adding deadline fails if plan doesn't exist."""
        with pytest.raises(KeyError, match="Plan 'Nonexistent' not found"):
            manager.add_deadline(
                plan_name="Nonexistent",
                deadline_date=date(2026, 6, 15),
                event_name="Event",
                priority=PriorityLevel.HIGH,
            )

    def test_add_deadline_before_plan_start(self, manager):
        """Test adding deadline fails if date before plan start."""
        manager.create_training_plan(
            name="Spring Build",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 5, 15),  # ~11 weeks
            objectives=[],
        )

        with pytest.raises(ValueError, match="before plan start"):
            manager.add_deadline(
                plan_name="Spring Build",
                deadline_date=date(2026, 2, 1),  # Before plan start
                event_name="Event",
                priority=PriorityLevel.HIGH,
            )

    def test_get_plan_timeline(self, manager):
        """Test retrieving plan timeline with deadlines."""
        manager.create_training_plan(
            name="Test Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            objectives=[],
        )

        manager.add_deadline(
            "Test Plan",
            date(2026, 1, 15),
            "Checkpoint 1",
            PriorityLevel.MEDIUM,
        )
        manager.add_deadline("Test Plan", date(2026, 1, 28), "Checkpoint 2", PriorityLevel.HIGH)

        timeline = manager.get_plan_timeline("Test Plan")

        assert timeline["plan_summary"]["name"] == "Test Plan"
        assert timeline["plan_summary"]["total_objectives"] == 2
        assert len(timeline["deadlines"]) == 2
        assert timeline["deadlines"][0]["name"] == "Checkpoint 1"  # Sorted by date
        assert len(timeline["weeks_breakdown"]) == 5  # 32 days = 5 weeks

    def test_get_plan_timeline_critical_dates(self, manager):
        """Test timeline extraction of critical priority dates."""
        manager.create_training_plan(
            name="Test Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            objectives=[],
        )

        manager.add_deadline(
            "Test Plan",
            date(2026, 1, 15),
            "Critical Event",
            PriorityLevel.CRITICAL,
        )
        manager.add_deadline("Test Plan", date(2026, 1, 28), "Normal Event", PriorityLevel.MEDIUM)

        timeline = manager.get_plan_timeline("Test Plan")

        assert len(timeline["critical_dates"]) == 1
        assert timeline["critical_dates"][0]["name"] == "Critical Event"

    def test_validate_plan_feasibility_safe_plan(self, manager):
        """Test validation passes for safe plan with no errors."""
        manager.create_training_plan(
            name="Safe Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),  # 32 days (~4.5 weeks)
            objectives=[],
            # Empty TSS targets - validation will skip ramp rate check
            weekly_tss_targets=[],
        )

        result = manager.validate_plan_feasibility("Safe Plan", current_ctl=60.0)

        assert result["feasible"] is True
        assert len(result["errors"]) == 0
        assert len(result["recommendations"]) > 0  # Should have general recommendations

    def test_validate_plan_feasibility_excessive_tss(self, manager):
        """Test validation warns about excessive weekly TSS."""
        manager.create_training_plan(
            name="High TSS Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
            objectives=[],
            weekly_tss_targets=[400, 420, 440, 460, 480],  # Exceeds 380 limit
        )

        result = manager.validate_plan_feasibility("High TSS Plan", current_ctl=60.0)

        # Should have warnings about TSS exceeding limits
        assert len(result["warnings"]) > 0
        assert any("TSS" in w and "exceeds" in w for w in result["warnings"])

    def test_validate_plan_feasibility_excessive_ramp(self, manager):
        """Test validation fails for excessive CTL ramp rate."""
        manager.create_training_plan(
            name="Aggressive Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 29),  # 4 weeks
            objectives=[],
            # Very high TSS progression: ~500 total TSS over 4 weeks
            # CTL increase ≈ 500/7 ≈ 71 points over 4 weeks = ~18 points/week
            weekly_tss_targets=[380, 400, 420, 450],
        )

        result = manager.validate_plan_feasibility("Aggressive Plan", current_ctl=40.0)

        # Should fail feasibility due to excessive ramp rate
        assert result["feasible"] is False
        assert len(result["errors"]) > 0
        assert any("ramp rate" in e.lower() and "exceeds" in e for e in result["errors"])
        assert len(result["recommendations"]) > 0

    def test_validate_plan_feasibility_many_objectives(self, manager):
        """Test validation warns about too many high priority objectives."""
        objectives = [
            TrainingObjective(
                f"Event {i}",
                date(2026, 3, i + 1),
                ObjectiveType.EVENT,
                PriorityLevel.CRITICAL if i < 3 else PriorityLevel.HIGH,
            )
            for i in range(6)  # 3 critical + 3 high
        ]

        manager.create_training_plan(
            name="Busy Plan",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 4, 30),
            objectives=objectives,
        )

        result = manager.validate_plan_feasibility("Busy Plan", current_ctl=60.0)

        # Should warn about too many objectives
        assert len(result["warnings"]) > 0
        assert any("objectives" in w.lower() for w in result["warnings"])
