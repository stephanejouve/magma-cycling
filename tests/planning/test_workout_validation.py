#!/usr/bin/env python3
"""
Tests for workout_validation module (Peaks Coaching pre-prescription validation).

Author: Stéphane Jouve
Created: 2026-02-14
"""

import pytest

from magma_cycling.planning.workout_validation import (
    ValidationResult,
    format_validation_report,
    validate_workout,
)


class TestValidateWorkoutTSB:
    """Tests for TSB appropriateness validation."""

    def test_vo2_tsb_insufficient_fail(self):
        """Test VO2 workout fails when TSB < 5."""
        validation = validate_workout(
            workout_name="VO2-intervals",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=65,
            athlete_state={"tsb": 3.0, "sleep_hours": 8.0},
        )

        assert validation.overall_result == ValidationResult.FAIL
        assert not validation.safe_to_prescribe
        assert any("TSB" in check.check_name for check in validation.checks)
        assert any("Sweet-Spot" in rec for rec in validation.recommendations)

    def test_vo2_tsb_warning(self):
        """Test VO2 workout warning when TSB 5-10."""
        validation = validate_workout(
            workout_name="VO2-intervals",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=65,
            athlete_state={"tsb": 7.0, "sleep_hours": 8.0},
        )

        assert validation.overall_result == ValidationResult.WARNING
        assert validation.safe_to_prescribe  # WARNING still safe
        assert any("limite" in check.message.lower() for check in validation.checks)

    def test_vo2_tsb_optimal_pass(self):
        """Test VO2 workout passes when TSB >= 10."""
        validation = validate_workout(
            workout_name="VO2-intervals",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=65,
            athlete_state={"tsb": 12.0, "sleep_hours": 8.0},
        )

        assert validation.overall_result == ValidationResult.PASS
        assert validation.safe_to_prescribe
        tsb_checks = [c for c in validation.checks if "TSB" in c.check_name]
        assert any("optimal" in c.message.lower() for c in tsb_checks)

    def test_ftp_tsb_too_negative_fail(self):
        """Test FTP workout fails when TSB < -10."""
        validation = validate_workout(
            workout_name="FTP-intervals",
            intensity_zone="FTP",
            duration_minutes=60,
            tss=80,
            athlete_state={"tsb": -12.0, "sleep_hours": 7.5},
        )

        assert validation.overall_result == ValidationResult.FAIL
        assert not validation.safe_to_prescribe
        assert any("récupération" in rec.lower() for rec in validation.recommendations)

    def test_ftp_tsb_negative_warning(self):
        """Test FTP workout warning when TSB -10 to 0."""
        validation = validate_workout(
            workout_name="FTP-intervals",
            intensity_zone="FTP",
            duration_minutes=60,
            tss=80,
            athlete_state={"tsb": -5.0, "sleep_hours": 7.5},
        )

        assert validation.overall_result == ValidationResult.WARNING
        assert validation.safe_to_prescribe

    def test_ftp_tsb_positive_pass(self):
        """Test FTP workout passes when TSB >= 0."""
        validation = validate_workout(
            workout_name="FTP-intervals",
            intensity_zone="FTP",
            duration_minutes=60,
            tss=80,
            athlete_state={"tsb": 2.0, "sleep_hours": 7.5},
        )

        assert validation.overall_result == ValidationResult.PASS
        assert validation.safe_to_prescribe


class TestValidateWorkoutSleep:
    """Tests for sleep sufficiency validation."""

    def test_high_intensity_insufficient_sleep_fail(self):
        """Test high intensity fails when sleep < 7h."""
        for zone in ["VO2", "AC", "FTP"]:
            validation = validate_workout(
                workout_name=f"{zone}-workout",
                intensity_zone=zone,
                duration_minutes=45,
                tss=60,
                athlete_state={"tsb": 5.0, "sleep_hours": 6.5},
            )

            assert validation.overall_result == ValidationResult.FAIL
            assert not validation.safe_to_prescribe
            sleep_checks = [c for c in validation.checks if "Sommeil" in c.check_name]
            assert len(sleep_checks) > 0
            assert any("Reporter" in rec for rec in validation.recommendations)

    def test_high_intensity_sufficient_sleep_pass(self):
        """Test high intensity passes when sleep >= 7h."""
        validation = validate_workout(
            workout_name="VO2-intervals",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=60,
            athlete_state={"tsb": 10.0, "sleep_hours": 7.5},
        )

        # Should have sleep check that passes
        sleep_checks = [c for c in validation.checks if "Sommeil" in c.check_name]
        assert len(sleep_checks) > 0
        assert all(c.result == ValidationResult.PASS for c in sleep_checks)

    def test_low_intensity_no_sleep_check(self):
        """Test low intensity zones don't require sleep check."""
        validation = validate_workout(
            workout_name="Endurance-ride",
            intensity_zone="Endurance",
            duration_minutes=120,
            tss=85,
            athlete_state={"tsb": 0.0, "sleep_hours": 6.0},  # Low sleep but low intensity
        )

        # Should not have sleep check for Endurance
        sleep_checks = [c for c in validation.checks if "Sommeil" in c.check_name]
        assert len(sleep_checks) == 0


class TestValidateWorkoutRecentIntensity:
    """Tests for recent high-intensity validation (48h rule)."""

    def test_vo2_with_recent_high_intensity_warning(self):
        """Test VO2 workout warning when high intensity < 48h."""
        recent_workouts = [
            {"intensity_zone": "FTP", "hours_ago": 24},
            {"intensity_zone": "Tempo", "hours_ago": 40},
        ]

        validation = validate_workout(
            workout_name="VO2-intervals",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=60,
            athlete_state={"tsb": 10.0, "sleep_hours": 8.0},
            recent_workouts=recent_workouts,
        )

        recovery_checks = [c for c in validation.checks if "48h" in c.check_name]
        assert len(recovery_checks) > 0
        assert recovery_checks[0].result == ValidationResult.WARNING
        assert any("Surveiller fatigue" in rec for rec in validation.recommendations)

    def test_vo2_no_recent_high_intensity_pass(self):
        """Test VO2 workout passes when no high intensity < 48h."""
        recent_workouts = [
            {"intensity_zone": "Endurance", "hours_ago": 24},
            {"intensity_zone": "FTP", "hours_ago": 72},  # >48h ago
        ]

        validation = validate_workout(
            workout_name="VO2-intervals",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=60,
            athlete_state={"tsb": 10.0, "sleep_hours": 8.0},
            recent_workouts=recent_workouts,
        )

        recovery_checks = [c for c in validation.checks if "48h" in c.check_name]
        # Should not trigger warning if high intensity >48h
        assert len(recovery_checks) == 0


class TestValidateWorkoutDecoupling:
    """Tests for expected decoupling thresholds."""

    def test_sweet_spot_decoupling_threshold(self):
        """Test Sweet-Spot decoupling threshold check for long workouts."""
        validation = validate_workout(
            workout_name="Sweet-Spot-90min",
            intensity_zone="Sweet-Spot",
            duration_minutes=90,
            tss=80,
            athlete_state={"tsb": 0.0},
        )

        decoupling_checks = [c for c in validation.checks if "Découplage" in c.check_name]
        assert len(decoupling_checks) > 0
        assert "5.0%" in decoupling_checks[0].message or "7.5%" in decoupling_checks[0].message

    def test_ftp_decoupling_threshold(self):
        """Test FTP decoupling threshold check for long workouts."""
        validation = validate_workout(
            workout_name="FTP-intervals-90min",
            intensity_zone="FTP",
            duration_minutes=90,
            tss=95,
            athlete_state={"tsb": 2.0},
        )

        decoupling_checks = [c for c in validation.checks if "Découplage" in c.check_name]
        assert len(decoupling_checks) > 0
        assert "8.0%" in decoupling_checks[0].message or "10%" in decoupling_checks[0].message

    def test_short_workout_no_decoupling_check(self):
        """Test short workouts (<60min) don't get decoupling check."""
        validation = validate_workout(
            workout_name="Sweet-Spot-45min",
            intensity_zone="Sweet-Spot",
            duration_minutes=45,
            tss=40,
            athlete_state={"tsb": 0.0},
        )

        decoupling_checks = [c for c in validation.checks if "Découplage" in c.check_name]
        assert len(decoupling_checks) == 0


class TestValidateWorkoutPlacement:
    """Tests for workout placement in week validation."""

    def test_recovery_midweek_warning(self):
        """Test recovery workout Wednesday triggers warning."""
        validation = validate_workout(
            workout_name="Recovery-spin",
            intensity_zone="Recovery",
            duration_minutes=30,
            tss=15,
            athlete_state={"tsb": 5.0, "day_of_week": "Wednesday"},
        )

        placement_checks = [c for c in validation.checks if "Placement" in c.check_name]
        assert len(placement_checks) > 0
        assert placement_checks[0].result == ValidationResult.WARNING

    def test_vo2_non_optimal_day_warning(self):
        """Test VO2 workout not on Tuesday/Thursday triggers warning."""
        validation = validate_workout(
            workout_name="VO2-intervals",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=60,
            athlete_state={"tsb": 10.0, "sleep_hours": 8.0, "day_of_week": "Monday"},
        )

        placement_checks = [c for c in validation.checks if "Placement" in c.check_name]
        assert len(placement_checks) > 0
        assert "mardi/jeudi" in placement_checks[0].message.lower()

    def test_vo2_optimal_day_no_warning(self):
        """Test VO2 workout on Tuesday passes placement check."""
        validation = validate_workout(
            workout_name="VO2-intervals",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=60,
            athlete_state={"tsb": 10.0, "sleep_hours": 8.0, "day_of_week": "Tuesday"},
        )

        placement_checks = [c for c in validation.checks if "Placement" in c.check_name]
        # Should not trigger warning on Tuesday
        assert len(placement_checks) == 0 or all(
            c.result != ValidationResult.WARNING for c in placement_checks
        )


class TestValidateWorkoutVolume:
    """Tests for volume coherence validation."""

    def test_large_workout_warning(self):
        """Test workout >30% weekly TSS triggers warning."""
        validation = validate_workout(
            workout_name="Long-ride",
            intensity_zone="Endurance",
            duration_minutes=180,
            tss=120,
            athlete_state={"tsb": 0.0, "weekly_tss_target": 350},
        )

        volume_checks = [c for c in validation.checks if "Volume" in c.check_name]
        assert len(volume_checks) > 0
        assert volume_checks[0].result == ValidationResult.WARNING
        assert "34%" in volume_checks[0].message  # 120/350 = 34%

    def test_normal_workout_no_volume_warning(self):
        """Test workout <30% weekly TSS passes."""
        validation = validate_workout(
            workout_name="Normal-ride",
            intensity_zone="Tempo",
            duration_minutes=60,
            tss=60,
            athlete_state={"tsb": 0.0, "weekly_tss_target": 350},
        )

        volume_checks = [c for c in validation.checks if "Volume" in c.check_name]
        # 60/350 = 17% < 30% threshold
        assert len(volume_checks) == 0


class TestValidateWorkoutJunkMiles:
    """Tests for 'junk miles' prevention validation."""

    def test_long_low_tss_warning(self):
        """Test long duration + low TSS triggers junk miles warning."""
        validation = validate_workout(
            workout_name="Easy-spin",
            intensity_zone="Endurance",
            duration_minutes=120,
            tss=45,  # Very low TSS for 2h
            athlete_state={"tsb": 0.0},
        )

        junk_checks = [c for c in validation.checks if "junk miles" in c.check_name.lower()]
        assert len(junk_checks) > 0
        assert junk_checks[0].result == ValidationResult.WARNING
        assert any("Tempo/Sweet-Spot" in rec for rec in validation.recommendations)

    def test_long_adequate_tss_pass(self):
        """Test long duration + adequate TSS passes."""
        validation = validate_workout(
            workout_name="Endurance-ride",
            intensity_zone="Endurance",
            duration_minutes=120,
            tss=85,  # Adequate TSS
            athlete_state={"tsb": 0.0},
        )

        junk_checks = [c for c in validation.checks if "junk miles" in c.check_name.lower()]
        assert len(junk_checks) == 0


class TestFormatValidationReport:
    """Tests for validation report formatting."""

    def test_format_pass_workout(self):
        """Test formatting of passing workout validation."""
        validation = validate_workout(
            workout_name="Sweet-Spot-intervals",
            intensity_zone="Sweet-Spot",
            duration_minutes=60,
            tss=65,
            athlete_state={"tsb": 2.0, "sleep_hours": 8.0},
        )

        report = format_validation_report(validation)

        assert "## Validation Séance" in report
        assert "Sweet-Spot-intervals" in report
        assert "✅" in report  # PASS icon
        assert "Oui" in report  # safe_to_prescribe = True

    def test_format_fail_workout(self):
        """Test formatting of failing workout validation."""
        validation = validate_workout(
            workout_name="VO2-intervals",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=65,
            athlete_state={"tsb": 2.0, "sleep_hours": 6.0},  # Insufficient sleep
        )

        report = format_validation_report(validation)

        assert "❌" in report  # FAIL icon
        assert "Non" in report  # safe_to_prescribe = False
        assert "Recommandations" in report
        assert len(validation.recommendations) > 0

    def test_format_warning_workout(self):
        """Test formatting of workout with warnings."""
        validation = validate_workout(
            workout_name="FTP-intervals",
            intensity_zone="FTP",
            duration_minutes=60,
            tss=80,
            athlete_state={"tsb": -5.0},  # Negative TSB = warning
        )

        report = format_validation_report(validation)

        assert "⚠️" in report  # WARNING icon


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_missing_optional_fields(self):
        """Test validation works with missing optional fields."""
        validation = validate_workout(
            workout_name="Basic-workout",
            intensity_zone="Tempo",
            duration_minutes=45,
            tss=40,
            athlete_state={"tsb": 0.0},  # No sleep, day_of_week, weekly_tss_target
        )

        # Should not crash, just skip checks that require missing data
        assert validation is not None
        assert validation.workout_name == "Basic-workout"

    def test_zero_tsb(self):
        """Test validation with TSB exactly at 0."""
        validation = validate_workout(
            workout_name="Neutral-workout",
            intensity_zone="Tempo",
            duration_minutes=60,
            tss=50,
            athlete_state={"tsb": 0.0},
        )

        assert validation.overall_result == ValidationResult.PASS

    def test_multiple_failures(self):
        """Test workout with multiple failure conditions."""
        validation = validate_workout(
            workout_name="Risky-VO2",
            intensity_zone="VO2",
            duration_minutes=45,
            tss=65,
            athlete_state={"tsb": 2.0, "sleep_hours": 5.5},  # TSB low + sleep insufficient
            recent_workouts=[{"intensity_zone": "VO2", "hours_ago": 24}],  # Recent VO2
        )

        assert validation.overall_result == ValidationResult.FAIL
        assert not validation.safe_to_prescribe
        # Should have multiple checks failing/warning
        failed_checks = [c for c in validation.checks if c.result == ValidationResult.FAIL]
        assert len(failed_checks) >= 1  # At least sleep failure


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
