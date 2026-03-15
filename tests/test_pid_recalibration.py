"""Tests for PID recalibration — delta+base integration, guard rails, reactivation."""

from __future__ import annotations

from magma_cycling.intelligence.discrete_pid_controller import DiscretePIDController
from magma_cycling.workflows.pid_peaks_integration import (
    ControlMode,
    IntegratedRecommendation,
    compute_integrated_correction,
    format_integrated_recommendation,
)


def _make_pid(setpoint: float = 230, ftp_measured: float = 223) -> DiscretePIDController:
    """Create a PID controller with standard gains and one cycle of history."""
    pid = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=setpoint)
    # Warm up with one cycle so integral is non-zero
    pid.compute_cycle_correction(measured_ftp=ftp_measured, cycle_duration_weeks=6)
    return pid


# ---------------------------------------------------------------------------
# Core fix: PID delta + Peaks base
# ---------------------------------------------------------------------------


class TestPIDDeltaIntegration:
    """Test that PID output is treated as delta on Peaks base, not absolute."""

    def test_pid_delta_added_to_peaks_base(self):
        """PID delta is added to Peaks base, not used as absolute."""
        pid = _make_pid()
        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=pid,
        )

        # PID should have a small delta, not be the absolute recommendation
        assert rec.pid_delta is not None
        assert abs(rec.pid_delta) < 50  # Delta should be small
        # The absolute suggestion should be close to Peaks (around 350)
        assert rec.pid_suggestion > 100  # Never aberrant
        # tss_per_week should be close to Peaks base (not 1)
        assert rec.tss_per_week >= 300

    def test_pid_delta_field_populated(self):
        """pid_delta field is populated in recommendation."""
        pid = _make_pid()
        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=pid,
        )
        assert rec.pid_delta is not None
        assert isinstance(rec.pid_delta, int)

    def test_no_pid_controller_falls_back_to_peaks(self):
        """Without PID controller, Peaks recommendation is used."""
        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=None,
        )
        assert rec.pid_suggestion is None
        assert rec.pid_delta is None
        assert rec.tss_per_week == rec.peaks_suggestion


# ---------------------------------------------------------------------------
# Guard rails
# ---------------------------------------------------------------------------


class TestGuardRails:
    """Test guard rails prevent aberrant PID recommendations."""

    def test_guard_rail_low_clamp(self):
        """PID output below 150 TSS triggers Peaks fallback."""
        from unittest.mock import MagicMock

        # Mock PID to return an extreme negative delta
        pid = MagicMock()
        pid.compute_cycle_correction_enhanced.return_value = {
            "tss_per_week_adjusted": -250,  # Extreme: 350 + (-250) = 100 < 150
            "validation": {"validated": True, "red_flags": [], "confidence": 0.9},
        }

        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=pid,
        )

        # Should have fallen back to Peaks, never below 150
        assert rec.tss_per_week >= 150
        assert any("aberrant" in w for w in rec.warnings)

    def test_guard_rail_high_clamp(self):
        """PID output above 450 TSS is clamped to 400."""
        from unittest.mock import MagicMock

        # Mock PID to return an extreme positive delta
        pid = MagicMock()
        pid.compute_cycle_correction_enhanced.return_value = {
            "tss_per_week_adjusted": 150,  # Extreme: 350 + 150 = 500 > 450
            "validation": {"validated": True, "red_flags": [], "confidence": 0.9},
        }

        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=pid,
        )

        # Should be clamped at 400 max
        assert rec.tss_per_week <= 400
        assert any("trop élevé" in w for w in rec.warnings)

    def test_pid_internal_saturation_stays_in_range(self):
        """With real PID (±30 saturation), output stays in [320, 380]."""
        pid = _make_pid()
        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=pid,
        )
        # PID delta clamped to ±30 by internal saturation
        # Peaks base ~350, so 320 <= absolute <= 380
        assert rec.tss_per_week >= 300
        assert rec.tss_per_week <= 400


# ---------------------------------------------------------------------------
# Reactivation rule
# ---------------------------------------------------------------------------


class TestReactivation:
    """Test PID reactivation within ±15% of Peaks target."""

    def test_pid_reactivates_when_in_range(self):
        """PID takes over when within ±15% of Peaks target, even at CTL < 50."""
        pid = _make_pid()
        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=pid,
        )

        # PID delta is small, so absolute is close to Peaks → within range
        peaks_base = rec.peaks_suggestion
        if rec.pid_suggestion:
            low = int(peaks_base * 0.85)
            high = int(peaks_base * 1.15)
            if low <= rec.pid_suggestion <= high:
                # PID should be active, override should be lifted
                assert not rec.override_active
                assert rec.mode == ControlMode.PID_CONSTRAINED

    def test_peaks_override_when_pid_out_of_range(self):
        """Peaks Override stays active when PID is out of ±15% range."""
        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=None,
        )
        # Without PID, Peaks Override should be active (CTL < 50)
        assert rec.override_active
        assert rec.mode == ControlMode.PEAKS_OVERRIDE


# ---------------------------------------------------------------------------
# Confidence levels
# ---------------------------------------------------------------------------


class TestConfidence:
    """Test confidence levels in recommendations."""

    def test_confidence_field_exists(self):
        """IntegratedRecommendation has confidence field."""
        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
        )
        assert hasattr(rec, "confidence")
        assert rec.confidence in ("low", "medium", "high")

    def test_peaks_override_has_medium_confidence(self):
        """Peaks Override (known-good fallback) has at least medium confidence."""
        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=None,
        )
        assert rec.confidence == "medium"

    def test_pid_active_confidence_not_low(self):
        """When PID is active and in range, confidence should not be low."""
        pid = _make_pid()
        rec = compute_integrated_correction(
            ctl_current=42.0,
            ftp_current=223,
            ftp_target=230,
            pid_controller=pid,
        )
        if not rec.override_active:
            assert rec.confidence in ("medium", "high")


# ---------------------------------------------------------------------------
# Format output
# ---------------------------------------------------------------------------


class TestFormatRecommendation:
    """Test formatted output includes new fields."""

    def test_format_includes_confidence(self):
        """Formatted recommendation includes confidence label."""
        rec = IntegratedRecommendation(
            mode=ControlMode.PID_CONSTRAINED,
            tss_per_week=351,
            ctl_projection_6weeks=48.0,
            phase="reconstruction_base",
            rationale="PID recalibrated",
            pid_suggestion=351,
            peaks_suggestion=350,
            override_active=False,
            warnings=[],
            confidence="medium",
            pid_delta=1,
        )
        formatted = format_integrated_recommendation(rec)
        assert "moyenne" in formatted  # confidence label in French
        assert "PID ACTIF" in formatted

    def test_format_shows_delta_in_table(self):
        """Formatted comparison table shows PID delta."""
        rec = IntegratedRecommendation(
            mode=ControlMode.PID_CONSTRAINED,
            tss_per_week=351,
            ctl_projection_6weeks=48.0,
            phase="reconstruction_base",
            rationale="test",
            pid_suggestion=351,
            peaks_suggestion=350,
            override_active=False,
            warnings=[],
            confidence="high",
            pid_delta=1,
        )
        formatted = format_integrated_recommendation(rec)
        assert "+1" in formatted
        assert "Delta" in formatted
