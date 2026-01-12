"""Tests pour les bugs corrigés dans upload_workouts.py."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from cyclisme_training_logs.upload_workouts import WorkoutUploader


class TestValidationTiretsManquants:
    """Test bug: tirets manquants non détectés (S076)."""

    def test_detect_missing_dashes_in_warmup(self):
        """Test détection tirets manquants dans Warmup."""
        uploader = WorkoutUploader("S076", datetime.now())

        workout = {
            "name": "S076-01-END-Test",
            "description": """Warmup

12m ramp 50-65% 85rpm
3m 65% 90rpm"""
        }

        warnings = uploader.validate_workout_notation(workout)

        # Should detect missing dash in warmup
        critical_warnings = [w for w in warnings if "🚨" in w and "TIRET MANQUANT" in w]
        assert len(critical_warnings) >= 1
        assert "12m ramp" in critical_warnings[0]

    def test_detect_missing_dashes_in_main_set(self):
        """Test détection tirets manquants dans Main set."""
        uploader = WorkoutUploader("S076", datetime.now())

        workout = {
            "name": "S076-01-END-Test",
            "description": """Warmup

- 10m ramp 50-65% 85rpm

Main set

35m 68-70% 88rpm"""
        }

        warnings = uploader.validate_workout_notation(workout)

        # Should detect missing dash in main set
        critical_warnings = [w for w in warnings if "🚨" in w and "TIRET MANQUANT" in w]
        assert len(critical_warnings) >= 1
        assert "35m" in critical_warnings[0]

    def test_detect_missing_dashes_in_cooldown(self):
        """Test détection tirets manquants dans Cooldown."""
        uploader = WorkoutUploader("S076", datetime.now())

        workout = {
            "name": "S076-01-END-Test",
            "description": """Warmup

- 10m ramp 50-65% 85rpm

Main set

- 30m 70% 88rpm

Cooldown

10m ramp 65-50% 85rpm"""
        }

        warnings = uploader.validate_workout_notation(workout)

        # Should detect missing dash in cooldown
        critical_warnings = [w for w in warnings if "🚨" in w and "TIRET MANQUANT" in w]
        assert len(critical_warnings) >= 1
        assert "10m ramp 65-50%" in critical_warnings[0]

    def test_accept_correct_format_with_dashes(self):
        """Test acceptance format correct avec tirets (S075)."""
        uploader = WorkoutUploader("S075", datetime.now())

        workout = {
            "name": "S075-01-END-Test",
            "description": """Warmup

- 12m ramp 50-65% 85rpm
- 3m 65% 90rpm

Main set

- 65m 68-72% 88rpm

Cooldown

- 10m ramp 65-50% 85rpm"""
        }

        warnings = uploader.validate_workout_notation(workout)

        # Should have no critical warnings about dashes
        critical_warnings = [w for w in warnings if "🚨" in w and "TIRET MANQUANT" in w]
        assert len(critical_warnings) == 0


class TestReposDaysUpload:
    """Test bug: jours REPOS ignorés au lieu d'être créés."""

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    def test_repos_creates_event_not_skipped(self, mock_client_class):
        """Test que REPOS crée un événement NOTE au lieu d'être ignoré."""
        uploader = WorkoutUploader("S076", datetime(2026, 1, 12))

        # Mock API
        mock_api = Mock()
        mock_api.create_event.return_value = {"id": "rest_event_123"}
        uploader.api = mock_api

        workouts = [
            {
                "filename": "S076-07-REPOS",
                "day": 7,
                "date": "2026-01-18",
                "name": "S076-07-REPOS",
                "description": "Jour de repos complet",
            }
        ]

        stats = uploader.upload_all(workouts, dry_run=False)

        # Should create event, not skip
        assert stats["success"] == 1
        assert stats["failed"] == 0
        assert "skipped" not in stats  # No more skipped stat

        # Verify API was called with NOTE category
        assert mock_api.create_event.called
        call_args = mock_api.create_event.call_args[0][0]
        assert call_args["category"] == "NOTE"
        assert call_args["name"] == "Repos"

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    def test_repos_dry_run(self, mock_client_class):
        """Test que REPOS fonctionne en dry-run."""
        uploader = WorkoutUploader("S076", datetime(2026, 1, 12))

        workouts = [
            {
                "filename": "S076-07-REPOS",
                "day": 7,
                "date": "2026-01-18",
                "name": "S076-07-REPOS",
                "description": "Jour de repos complet",
            }
        ]

        stats = uploader.upload_all(workouts, dry_run=True)

        # Should succeed in dry-run
        assert stats["success"] == 1
        assert stats["failed"] == 0

    def test_validation_allows_repos_without_warmup_cooldown(self):
        """Test que validation n'exige pas warmup/cooldown pour REPOS."""
        uploader = WorkoutUploader("S076", datetime.now())

        workout = {
            "name": "S076-07-REPOS",
            "description": "Jour de repos complet",
        }

        warnings = uploader.validate_workout_notation(workout)

        # Should not have critical warnings about missing warmup/cooldown
        critical_warnings = [w for w in warnings if "🚨" in w]
        assert len(critical_warnings) == 0


class TestIntegrationS076:
    """Test intégration complète pour S076."""

    def test_s076_planning_validation_would_block(self):
        """Test que S076 (tirets manquants) serait maintenant bloqué."""
        uploader = WorkoutUploader("S076", datetime.now())

        # Simulated S076 workout (missing dashes)
        workout = {
            "name": "S076-01-END-EnduranceLegere-V001",
            "description": """Endurance Legere (60min, 44 TSS)

Warmup

12m ramp 50-65% 85rpm
3m 65% 90rpm

Main set

35m 68-70% 88rpm

Cooldown

10m ramp 65-50% 85rpm"""
        }

        warnings = uploader.validate_workout_notation(workout)

        # Should have multiple critical warnings
        critical_warnings = [w for w in warnings if "🚨" in w]
        assert len(critical_warnings) >= 3  # At least 3 sections with missing dashes

    @patch("cyclisme_training_logs.upload_workouts.IntervalsClient")
    def test_s076_complete_week_with_repos(self, mock_client_class):
        """Test upload semaine complète S076 avec jour repos."""
        uploader = WorkoutUploader("S076", datetime(2026, 1, 12))

        # Mock API
        mock_api = Mock()
        mock_api.create_event.return_value = {"id": "event_123"}
        uploader.api = mock_api

        workouts = [
            {
                "filename": "S076-01-END-Test",
                "day": 1,
                "date": "2026-01-12",
                "name": "S076-01-END-Test",
                "description": "Workout 1",
            },
            {
                "filename": "S076-07-REPOS",
                "day": 7,
                "date": "2026-01-18",
                "name": "S076-07-REPOS",
                "description": "Repos",
            },
        ]

        stats = uploader.upload_all(workouts, dry_run=False)

        # Both should succeed (workout + repos)
        assert stats["success"] == 2
        assert stats["failed"] == 0

        # Verify both events were created
        assert mock_api.create_event.call_count == 2

        # First call: WORKOUT
        first_call = mock_api.create_event.call_args_list[0][0][0]
        assert first_call["category"] == "WORKOUT"
        assert first_call["type"] == "VirtualRide"

        # Second call: NOTE (repos)
        second_call = mock_api.create_event.call_args_list[1][0][0]
        assert second_call["category"] == "NOTE"
        assert second_call["name"] == "Repos"
