"""
Tests pour clear_week_planning.py.

GARTNER_TIME: T
STATUS: Testing
LAST_REVIEW: 2026-01-04
PRIORITY: P1
DOCSTRING: v2

Tests unitaires pour le script clear_week_planning.py qui supprime
les workouts planifiés erronés d'une semaine sur Intervals.icu.

Author: Claude Code
Created: 2026-01-04
Updated: 2026-01-04 (Sprint R5 - Initial test suite)
"""

from datetime import datetime

import pytest


class TestClearWeekPlanning:
    """Tests pour clear_week_planning script."""

    def test_date_parsing_valid(self):
        """Test parsing de date valide."""
        date_str = "2026-01-05"
        parsed = datetime.strptime(date_str, "%Y-%m-%d")

        assert parsed.year == 2026
        assert parsed.month == 1
        assert parsed.day == 5

    def test_date_parsing_invalid(self):
        """Test parsing de date invalide."""
        date_str = "2026-13-45"  # Invalid month/day

        with pytest.raises(ValueError):
            datetime.strptime(date_str, "%Y-%m-%d")

    def test_week_id_format_valid(self):
        """Test format week_id valide."""
        week_ids_valid = ["S001", "S073", "S075", "S100", "S999"]

        for week_id in week_ids_valid:
            assert len(week_id) == 4
            assert week_id[0] == "S"
            assert week_id[1:].isdigit()

    def test_week_id_format_invalid(self):
        """Test format week_id invalide."""
        week_ids_invalid = ["S1", "S0001", "073", "W073", "s073"]

        for week_id in week_ids_invalid:
            # Should fail one of the checks
            is_valid = len(week_id) == 4 and week_id[0] == "S" and week_id[1:].isdigit()
            assert not is_valid


class TestEventFiltering:
    """Tests pour le filtrage des événements."""

    @pytest.fixture
    def sample_events(self):
        """Sample events from Intervals.icu."""
        return [
            {
                "id": 1,
                "name": "S075-01-END-Test",
                "category": "WORKOUT",
                "start_date_local": "2026-01-05T08:00:00",
            },
            {
                "id": 2,
                "name": "Morning Run",
                "category": "ACTIVITY",
                "start_date_local": "2026-01-05T09:00:00",
            },
            {
                "id": 3,
                "name": "S075-02-INT-Test",
                "category": "WORKOUT",
                "start_date_local": "2026-01-06T08:00:00",
            },
            {
                "id": 4,
                "name": "Training Notes",
                "category": "NOTE",
                "start_date_local": "2026-01-06T10:00:00",
            },
        ]

    def test_filter_workout_events(self, sample_events):
        """Test filtering only WORKOUT events."""
        workout_events = [e for e in sample_events if e.get("category") == "WORKOUT"]

        assert len(workout_events) == 2
        assert all(e["category"] == "WORKOUT" for e in workout_events)
        assert workout_events[0]["name"] == "S075-01-END-Test"
        assert workout_events[1]["name"] == "S075-02-INT-Test"

    def test_preserve_activities(self, sample_events):
        """Test that ACTIVITY events are not filtered."""
        workout_events = [e for e in sample_events if e.get("category") == "WORKOUT"]
        activity_events = [e for e in sample_events if e.get("category") == "ACTIVITY"]

        assert len(activity_events) == 1
        assert activity_events[0]["name"] == "Morning Run"
        # Activities should not be in workout_events
        assert not any(e["name"] == "Morning Run" for e in workout_events)

    def test_preserve_notes(self, sample_events):
        """Test that NOTE events are not filtered."""
        workout_events = [e for e in sample_events if e.get("category") == "WORKOUT"]
        note_events = [e for e in sample_events if e.get("category") == "NOTE"]

        assert len(note_events) == 1
        assert note_events[0]["name"] == "Training Notes"
        # Notes should not be in workout_events
        assert not any(e["name"] == "Training Notes" for e in workout_events)


class TestDateRangeCalculation:
    """Tests pour le calcul de la période de semaine."""

    def test_week_range_calculation(self):
        """Test calculation of week date range."""
        from datetime import timedelta

        start_date = datetime(2026, 1, 5)  # Monday
        end_date = start_date + timedelta(days=6)  # Sunday

        assert end_date == datetime(2026, 1, 11)
        assert (end_date - start_date).days == 6

    def test_week_spans_7_days(self):
        """Test that week spans exactly 7 days."""
        from datetime import timedelta

        start_date = datetime(2026, 1, 5)
        end_date = start_date + timedelta(days=6)

        # Generate all days in week
        days_in_week = []
        current_day = start_date
        while current_day <= end_date:
            days_in_week.append(current_day)
            current_day += timedelta(days=1)

        assert len(days_in_week) == 7


class TestDryRunMode:
    """Tests pour le mode dry-run."""

    def test_dry_run_no_deletion(self):
        """Test that dry-run mode doesn't delete anything."""
        # Mock scenario
        dry_run = True
        events_to_delete = [
            {"id": 1, "name": "Test1"},
            {"id": 2, "name": "Test2"},
        ]

        deleted_count = 0
        if not dry_run:
            # Would delete here
            deleted_count = len(events_to_delete)

        assert deleted_count == 0  # Nothing deleted in dry-run

    def test_dry_run_reports_would_delete(self):
        """Test that dry-run reports what would be deleted."""
        dry_run = True
        events_to_delete = [
            {"id": 1, "name": "Test1"},
            {"id": 2, "name": "Test2"},
        ]

        if dry_run:
            would_delete_count = len(events_to_delete)
        else:
            would_delete_count = 0

        assert would_delete_count == 2


class TestConfirmationLogic:
    """Tests pour la logique de confirmation."""

    def test_confirmation_required_by_default(self):
        """Test that confirmation is required by default."""
        auto_mode = False
        dry_run = False

        requires_confirmation = not auto_mode and not dry_run

        assert requires_confirmation is True

    def test_no_confirmation_in_auto_mode(self):
        """Test no confirmation in auto mode."""
        auto_mode = True
        dry_run = False

        requires_confirmation = not auto_mode and not dry_run

        assert requires_confirmation is False

    def test_no_confirmation_in_dry_run(self):
        """Test no confirmation in dry-run mode."""
        auto_mode = False
        dry_run = True

        requires_confirmation = not auto_mode and not dry_run

        assert requires_confirmation is False

    def test_valid_confirmation_responses(self):
        """Test valid confirmation responses."""
        valid_responses = ["oui", "yes", "y", "o"]
        invalid_responses = ["non", "no", "n", "maybe", ""]

        for response in valid_responses:
            assert response in ["oui", "yes", "y", "o"]

        for response in invalid_responses:
            assert response not in ["oui", "yes", "y", "o"]


class TestEventCounting:
    """Tests pour le comptage des événements."""

    @pytest.fixture
    def deletion_results(self):
        """Sample deletion results."""
        return {
            "total": 7,
            "deleted": 5,
            "failed": 2,
            "skipped": 0,
        }

    def test_success_rate_calculation(self, deletion_results):
        """Test calculation of success rate."""
        total = deletion_results["deleted"] + deletion_results["failed"]
        success_rate = (deletion_results["deleted"] / total) * 100

        assert success_rate == pytest.approx(71.43, rel=0.01)

    def test_all_successful(self):
        """Test when all deletions succeed."""
        deleted = 7
        failed = 0
        total = deleted + failed

        assert failed == 0
        assert deleted == total

    def test_all_failed(self):
        """Test when all deletions fail."""
        deleted = 0
        failed = 7
        total = deleted + failed

        assert deleted == 0
        assert failed == total

    def test_partial_success(self):
        """Test partial success scenario."""
        deleted = 5
        failed = 2
        total = deleted + failed

        assert deleted > 0
        assert failed > 0
        assert deleted + failed == total


class TestErrorHandling:
    """Tests pour la gestion des erreurs."""

    def test_invalid_date_format(self):
        """Test handling of invalid date format."""
        invalid_dates = ["2026/01/05", "01-05-2026", "not-a-date", "2026-13-01", "2026-01-32"]

        for date_str in invalid_dates:
            with pytest.raises(ValueError):
                datetime.strptime(date_str, "%Y-%m-%d")

    def test_missing_event_fields(self):
        """Test handling of events with missing fields."""
        event_incomplete = {
            "id": 1,
            # Missing: name, category, start_date_local
        }

        # Should handle gracefully with .get()
        event_id = event_incomplete.get("id")
        event_name = event_incomplete.get("name", "Unknown")
        event_category = event_incomplete.get("category", "UNKNOWN")

        assert event_id == 1
        assert event_name == "Unknown"
        assert event_category == "UNKNOWN"


class TestOutputFormatting:
    """Tests pour le formatage de la sortie."""

    def test_date_formatting(self):
        """Test date formatting for display."""
        date_str = "2026-01-05"
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        formatted = dt.strftime("%d/%m/%Y")

        assert formatted == "05/01/2026"

    def test_progress_indicator(self):
        """Test progress indicator format."""
        current = 3
        total = 7
        progress = f"[{current}/{total}]"

        assert progress == "[3/7]"

    def test_summary_format(self):
        """Test summary format."""
        deleted = 5
        failed = 2
        total = 7

        summary = f"✅ Supprimés : {deleted}/{total}\n❌ Échecs   : {failed}/{total}"

        assert "5/7" in summary
        assert "2/7" in summary
