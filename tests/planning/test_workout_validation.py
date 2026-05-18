#!/usr/bin/env python3
"""
Tests for workout_validation module (Peaks Coaching pre-prescription validation).

Author: Stéphane Jouve
Created: 2026-02-14
"""

import pytest

from magma_cycling.planning.workout_validation import (
    ValidationResult,
    compute_intensity_factor,
    format_validation_report,
    validate_intensity_coherence,
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


class TestComputeIntensityFactor:
    """Tests for IF computation from (TSS, duration)."""

    def test_if_60min_at_threshold(self):
        """1h à FTP = 100 TSS = IF 1.00 par définition."""
        assert compute_intensity_factor(tss=100, duration_minutes=60) == pytest.approx(1.0)

    def test_if_s094_01_regression(self):
        """S094-01 régression : REC 18 TSS / 15min → IF ≈ 0.849."""
        assert compute_intensity_factor(tss=18, duration_minutes=15) == pytest.approx(
            0.849, abs=0.01
        )

    def test_if_s094_05_regression(self):
        """S094-05 régression : REC 16 TSS / 10min → IF ≈ 0.980."""
        assert compute_intensity_factor(tss=16, duration_minutes=10) == pytest.approx(
            0.980, abs=0.01
        )

    def test_if_zero_tss_returns_none(self):
        assert compute_intensity_factor(tss=0, duration_minutes=60) is None

    def test_if_zero_duration_returns_none(self):
        assert compute_intensity_factor(tss=100, duration_minutes=0) is None


class TestValidateIntensityCoherence:
    """Tests for IF/type coherence validation."""

    def test_rec_in_window_pass(self):
        """REC 60min / 36 TSS → IF 0.60 ∈ [0.55-0.65]."""
        check = validate_intensity_coherence("REC", tss=36, duration_minutes=60)
        assert check.result == ValidationResult.PASS

    def test_end_in_window_pass(self):
        """END 120min / 98 TSS → IF 0.70 ∈ [0.65-0.75]."""
        check = validate_intensity_coherence("END", tss=98, duration_minutes=120)
        assert check.result == ValidationResult.PASS

    def test_tmp_in_window_pass(self):
        """TMP 60min / 64 TSS → IF 0.80 ∈ [0.75-0.85]."""
        check = validate_intensity_coherence("TMP", tss=64, duration_minutes=60)
        assert check.result == ValidationResult.PASS

    def test_ss_in_window_pass(self):
        """SS 60min / 81 TSS → IF 0.90 ∈ [0.85-0.94]."""
        check = validate_intensity_coherence("SS", tss=81, duration_minutes=60)
        assert check.result == ValidationResult.PASS

    def test_ftp_in_window_pass(self):
        """FTP 60min / 100 TSS → IF 1.00 ∈ [0.95-1.04]."""
        check = validate_intensity_coherence("FTP", tss=100, duration_minutes=60)
        assert check.result == ValidationResult.PASS

    def test_vo2_in_window_pass(self):
        """VO2 30min / 60 TSS → IF ≈ 1.095 ∈ [1.05-1.14]."""
        check = validate_intensity_coherence("VO2", tss=60, duration_minutes=30)
        assert check.result == ValidationResult.PASS

    def test_s094_01_rec_to_ss_fail(self):
        """Régression S094-01 : REC 15min / 18 TSS → IF 0.85 = zone SS → FAIL."""
        check = validate_intensity_coherence("REC", tss=18, duration_minutes=15)
        assert check.result == ValidationResult.FAIL
        assert check.severity == "critical"
        assert "SS" in check.message

    def test_s094_05_rec_to_ftp_fail(self):
        """Régression S094-05 : REC 10min / 16 TSS → IF 0.98 = zone FTP → FAIL."""
        check = validate_intensity_coherence("REC", tss=16, duration_minutes=10)
        assert check.result == ValidationResult.FAIL
        assert check.severity == "critical"
        assert "FTP" in check.message

    def test_vo2_too_high_no_zone_match_fail(self):
        """VO2 60min / 169 TSS → IF ≈ 1.30 hors window, pas dans autre zone → FAIL."""
        check = validate_intensity_coherence("VO2", tss=169, duration_minutes=60)
        assert check.result == ValidationResult.FAIL
        assert check.severity == "critical"

    def test_rec_just_below_window_warning(self):
        """REC 60min / 26 TSS → IF ≈ 0.510, écart 0.04 < tolérance 0.05, no zone match → WARNING."""
        check = validate_intensity_coherence("REC", tss=26, duration_minutes=60)
        assert check.result == ValidationResult.WARNING
        assert check.severity == "warning"

    def test_vo2_just_above_window_warning(self):
        """VO2 60min / 134 TSS → IF ≈ 1.158, écart 0.018 < tolérance 0.05, no zone match → WARNING."""
        check = validate_intensity_coherence("VO2", tss=134, duration_minutes=60)
        assert check.result == ValidationResult.WARNING

    def test_adjacent_zone_drift_warning(self):
        """END 60min / 65 TSS → IF ≈ 0.806 dans zone TMP adjacente → WARNING (pas FAIL).

        Drift d'une seule zone (rank distance = 1) accepté en WARNING : sync continue,
        on flagge mais on ne bloque pas. Évite de rejeter des sessions END légèrement
        teintées de Tempo ou Recovery.
        """
        check = validate_intensity_coherence("END", tss=65, duration_minutes=60)
        assert check.result == ValidationResult.WARNING
        assert "TMP" in check.message
        assert "adjacente" in check.message

    def test_end_just_below_window_to_rec_warning(self):
        """END 90min / 55 TSS → IF ≈ 0.605 dans REC adjacente → WARNING.

        Cas test_session_ids_filter (fixture historique) : la séance END légère
        ne doit pas être bloquée, juste flaggée.
        """
        check = validate_intensity_coherence("END", tss=55, duration_minutes=90)
        assert check.result == ValidationResult.WARNING
        assert "REC" in check.message

    def test_distant_zone_drift_fail(self):
        """REC déclaré + IF tombant 2+ zones plus haut → FAIL (cas S094-01/05)."""
        check = validate_intensity_coherence("REC", tss=18, duration_minutes=15)
        assert check.result == ValidationResult.FAIL

    def test_int_skip_validation(self):
        check = validate_intensity_coherence("INT", tss=18, duration_minutes=15)
        assert check.result == ValidationResult.PASS
        assert "non-applicable" in check.message

    def test_race_skip_validation(self):
        check = validate_intensity_coherence("RACE", tss=200, duration_minutes=60)
        assert check.result == ValidationResult.PASS

    def test_mix_skip_validation(self):
        check = validate_intensity_coherence("MIX", tss=100, duration_minutes=60)
        assert check.result == ValidationResult.PASS

    def test_unknown_type_skip_validation(self):
        check = validate_intensity_coherence("XYZ", tss=100, duration_minutes=60)
        assert check.result == ValidationResult.PASS
        assert "pas de window IF référence" in check.message

    def test_zero_tss_skip(self):
        check = validate_intensity_coherence("REC", tss=0, duration_minutes=60)
        assert check.result == ValidationResult.PASS
        assert "non-calculable" in check.message

    def test_zero_duration_skip(self):
        check = validate_intensity_coherence("REC", tss=36, duration_minutes=0)
        assert check.result == ValidationResult.PASS

    def test_clm_aliases_to_ftp_window_pass(self):
        check = validate_intensity_coherence("CLM", tss=100, duration_minutes=60)
        assert check.result == ValidationResult.PASS

    def test_tt_aliases_to_ftp_window_pass(self):
        check = validate_intensity_coherence("TT", tss=100, duration_minutes=60)
        assert check.result == ValidationResult.PASS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
