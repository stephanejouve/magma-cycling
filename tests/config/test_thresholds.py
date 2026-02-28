"""Tests for thresholds module (Sprint R2)."""

import os

import pytest

from magma_cycling.config.thresholds import TrainingThresholds


class TestTrainingThresholdsFromEnv:
    """Tests for TrainingThresholds.from_env() method."""

    def test_from_env_with_all_fields(self, monkeypatch):
        """Test loading thresholds with all environment variables set."""
        monkeypatch.setenv("TSB_FRESH_MIN", "10")

        monkeypatch.setenv("TSB_OPTIMAL_MIN", "-5")
        monkeypatch.setenv("TSB_FATIGUED_MIN", "-15")
        monkeypatch.setenv("TSB_CRITICAL", "-25")
        monkeypatch.setenv("ATL_CTL_RATIO_OPTIMAL", "1.0")
        monkeypatch.setenv("ATL_CTL_RATIO_WARNING", "1.3")
        monkeypatch.setenv("ATL_CTL_RATIO_CRITICAL", "1.8")
        monkeypatch.setenv("RECOVERY_HRV_THRESHOLD_PERCENT", "90")
        monkeypatch.setenv("RECOVERY_SLEEP_HOURS_MIN", "7.0")
        monkeypatch.setenv("RECOVERY_RESTING_HR_DEVIATION_MAX", "10")

        thresholds = TrainingThresholds.from_env()

        assert thresholds.tsb_fresh_min == 10
        assert thresholds.tsb_optimal_min == -5
        assert thresholds.tsb_fatigued_min == -15
        assert thresholds.tsb_critical == -25
        assert thresholds.atl_ctl_ratio_optimal == 1.0
        assert thresholds.atl_ctl_ratio_warning == 1.3
        assert thresholds.atl_ctl_ratio_critical == 1.8
        assert thresholds.recovery_hrv_threshold_percent == 90
        assert thresholds.recovery_sleep_hours_min == 7.0
        assert thresholds.recovery_resting_hr_deviation_max == 10

    def test_from_env_with_defaults(self, monkeypatch):
        """Test loading thresholds with default values when env vars not set."""
        # Clear all relevant env vars

        for key in os.environ.copy():
            if key.startswith("TSB_") or key.startswith("ATL_") or key.startswith("RECOVERY_"):
                monkeypatch.delenv(key, raising=False)

        thresholds = TrainingThresholds.from_env()

        # Check defaults
        assert thresholds.tsb_fresh_min == 10
        assert thresholds.tsb_optimal_min == -5
        assert thresholds.tsb_fatigued_min == -15
        assert thresholds.tsb_critical == -25


class TestTrainingThresholdsMethods:
    """Tests for TrainingThresholds helper methods."""

    @pytest.fixture
    def thresholds(self):
        """Provide standard thresholds fixture."""
        return TrainingThresholds(
            tsb_fresh_min=10,
            tsb_optimal_min=-5,
            tsb_fatigued_min=-15,
            tsb_critical=-25,
            atl_ctl_ratio_optimal=1.0,
            atl_ctl_ratio_warning=1.3,
            atl_ctl_ratio_critical=1.8,
            recovery_hrv_threshold_percent=90,
            recovery_sleep_hours_min=7.0,
            recovery_resting_hr_deviation_max=10,
        )

    def test_get_tsb_state(self, thresholds):
        """Test TSB state classification."""
        assert thresholds.get_tsb_state(12) == "fresh"

        assert thresholds.get_tsb_state(5) == "optimal"
        assert thresholds.get_tsb_state(-8) == "fatigued"
        assert thresholds.get_tsb_state(-30) == "overreached"

        # Edge cases
        assert thresholds.get_tsb_state(10) == "optimal"  # Exactly at threshold
        assert thresholds.get_tsb_state(-5) == "fatigued"  # Exactly at threshold
        assert thresholds.get_tsb_state(-25) == "overreached"  # Exactly at critical

    def test_is_tsb_optimal(self, thresholds):
        """Test TSB optimal range check."""
        assert thresholds.is_tsb_optimal(5) is True

        assert thresholds.is_tsb_optimal(0) is True
        assert thresholds.is_tsb_optimal(-4) is True

        # Outside optimal range
        assert thresholds.is_tsb_optimal(12) is False  # Too fresh
        assert thresholds.is_tsb_optimal(-10) is False  # Too fatigued

    def test_get_atl_ctl_ratio_state(self, thresholds):
        """Test ATL/CTL ratio state classification."""
        assert thresholds.get_atl_ctl_ratio_state(0.9) == "optimal"

        assert thresholds.get_atl_ctl_ratio_state(1.0) == "warning"
        assert thresholds.get_atl_ctl_ratio_state(1.5) == "warning"
        assert thresholds.get_atl_ctl_ratio_state(2.0) == "critical"

        # Edge cases
        assert thresholds.get_atl_ctl_ratio_state(1.0) == "warning"  # At threshold
        assert thresholds.get_atl_ctl_ratio_state(1.8) == "critical"  # At critical

    def test_is_overtraining_risk(self, thresholds):
        """Test overtraining risk detection."""
        # No risk scenarios

        assert thresholds.is_overtraining_risk(tsb=5, atl_ctl_ratio=0.9) is False
        assert thresholds.is_overtraining_risk(tsb=0, atl_ctl_ratio=1.0) is False

        # Risk from TSB only
        assert thresholds.is_overtraining_risk(tsb=-30, atl_ctl_ratio=0.9) is True

        # Risk from ratio only
        assert thresholds.is_overtraining_risk(tsb=5, atl_ctl_ratio=2.0) is True

        # Risk from both
        assert thresholds.is_overtraining_risk(tsb=-30, atl_ctl_ratio=2.0) is True

        # Edge cases
        assert thresholds.is_overtraining_risk(tsb=-25, atl_ctl_ratio=1.8) is True


class TestTrainingThresholdsValidation:
    """Tests for Pydantic validation."""

    def test_valid_creation(self):
        """Test creating thresholds with valid values."""
        thresholds = TrainingThresholds(
            tsb_fresh_min=10,
            tsb_optimal_min=-5,
            tsb_fatigued_min=-15,
            tsb_critical=-25,
            atl_ctl_ratio_optimal=1.0,
            atl_ctl_ratio_warning=1.3,
            atl_ctl_ratio_critical=1.8,
            recovery_hrv_threshold_percent=90,
            recovery_sleep_hours_min=7.0,
            recovery_resting_hr_deviation_max=10,
        )
        assert thresholds.tsb_critical == -25

    def test_invalid_hrv_percent(self):
        """Test validation for HRV percent > 100."""
        with pytest.raises(ValueError):
            TrainingThresholds(
                tsb_fresh_min=10,
                tsb_optimal_min=-5,
                tsb_fatigued_min=-15,
                tsb_critical=-25,
                atl_ctl_ratio_optimal=1.0,
                atl_ctl_ratio_warning=1.3,
                atl_ctl_ratio_critical=1.8,
                recovery_hrv_threshold_percent=150,  # Invalid > 100
                recovery_sleep_hours_min=7.0,
                recovery_resting_hr_deviation_max=10,
            )

    def test_invalid_ratio(self):
        """Test validation for ratio <= 0."""
        with pytest.raises(ValueError):
            TrainingThresholds(
                tsb_fresh_min=10,
                tsb_optimal_min=-5,
                tsb_fatigued_min=-15,
                tsb_critical=-25,
                atl_ctl_ratio_optimal=0,  # Invalid <= 0
                atl_ctl_ratio_warning=1.3,
                atl_ctl_ratio_critical=1.8,
                recovery_hrv_threshold_percent=90,
                recovery_sleep_hours_min=7.0,
                recovery_resting_hr_deviation_max=10,
            )


class TestTrainingThresholdsFromEnvErrors:
    """Tests for error handling in from_env() method."""

    def test_from_env_with_pydantic_validation_error(self, monkeypatch):
        """Test from_env() raises ValueError on Pydantic ValidationError.

        Covers lines 121-122: ValidationError exception handling.

        Scenario:
        - Set HRV threshold > 100 (violates Pydantic validator)
        - from_env() should catch ValidationError and raise ValueError
        """
        monkeypatch.setenv("TSB_FRESH_MIN", "10")
        monkeypatch.setenv("TSB_OPTIMAL_MIN", "-5")
        monkeypatch.setenv("TSB_FATIGUED_MIN", "-15")
        monkeypatch.setenv("TSB_CRITICAL", "-25")
        monkeypatch.setenv("ATL_CTL_RATIO_OPTIMAL", "1.0")
        monkeypatch.setenv("ATL_CTL_RATIO_WARNING", "1.3")
        monkeypatch.setenv("ATL_CTL_RATIO_CRITICAL", "1.8")
        monkeypatch.setenv("RECOVERY_HRV_THRESHOLD_PERCENT", "150")  # Invalid > 100
        monkeypatch.setenv("RECOVERY_SLEEP_HOURS_MIN", "7.0")
        monkeypatch.setenv("RECOVERY_RESTING_HR_DEVIATION_MAX", "10")

        with pytest.raises(ValueError) as exc_info:
            TrainingThresholds.from_env()

        # Verify error message mentions validation failure
        assert "Invalid training thresholds configuration" in str(exc_info.value)

    def test_from_env_with_invalid_numeric_literal(self, monkeypatch):
        """Test from_env() raises ValueError on invalid numeric conversion.

        Covers lines 124-126: ValueError handling for numeric conversion.

        Scenario:
        - Set environment variable to non-numeric string
        - float() conversion fails with ValueError
        - Python ≤3.12: message contains "invalid literal" → line 125 (custom message)
        - Python 3.13+: message is "could not convert..." → line 126 (re-raise)

        Both paths should raise ValueError with meaningful message.
        """
        monkeypatch.setenv("TSB_FRESH_MIN", "not_a_number")  # Invalid numeric string
        monkeypatch.setenv("TSB_OPTIMAL_MIN", "-5")
        monkeypatch.setenv("TSB_FATIGUED_MIN", "-15")
        monkeypatch.setenv("TSB_CRITICAL", "-25")
        monkeypatch.setenv("ATL_CTL_RATIO_OPTIMAL", "1.0")
        monkeypatch.setenv("ATL_CTL_RATIO_WARNING", "1.3")
        monkeypatch.setenv("ATL_CTL_RATIO_CRITICAL", "1.8")
        monkeypatch.setenv("RECOVERY_HRV_THRESHOLD_PERCENT", "90")
        monkeypatch.setenv("RECOVERY_SLEEP_HOURS_MIN", "7.0")
        monkeypatch.setenv("RECOVERY_RESTING_HR_DEVIATION_MAX", "10")

        with pytest.raises(ValueError) as exc_info:
            TrainingThresholds.from_env()

        # Verify error message is meaningful (either custom or original)
        error_msg = str(exc_info.value)
        assert (
            "Invalid numeric value in thresholds configuration" in error_msg  # Line 125
            or "could not convert" in error_msg  # Line 126 (Python 3.13+)
            or "invalid literal" in error_msg  # Line 126 (Python ≤3.12)
        )

    def test_from_env_with_invalid_literal_python_312_behavior(self, monkeypatch):
        """Test from_env() custom error message with 'invalid literal' (Python ≤3.12).

        Covers line 125: Custom error message for "invalid literal" case.

        Scenario:
        - Simulate Python ≤3.12 behavior where float() raises ValueError
          with "invalid literal for float()" in the message
        - from_env() should catch this and wrap with custom message
        - This ensures line 125 is covered even when running on Python 3.13+

        Note: Python 3.13+ changed the ValueError message from float(),
        so we need to explicitly test the old behavior.
        """
        import builtins
        from unittest.mock import patch

        # Mock float() to simulate Python ≤3.12 behavior
        original_float = builtins.float

        def mock_float(value):
            if value == "old_style_error":
                raise ValueError("invalid literal for float() with base 10: 'old_style_error'")
            return original_float(value)

        monkeypatch.setenv("TSB_FRESH_MIN", "old_style_error")  # Triggers mock
        monkeypatch.setenv("TSB_OPTIMAL_MIN", "-5")
        monkeypatch.setenv("TSB_FATIGUED_MIN", "-15")
        monkeypatch.setenv("TSB_CRITICAL", "-25")
        monkeypatch.setenv("ATL_CTL_RATIO_OPTIMAL", "1.0")
        monkeypatch.setenv("ATL_CTL_RATIO_WARNING", "1.3")
        monkeypatch.setenv("ATL_CTL_RATIO_CRITICAL", "1.8")
        monkeypatch.setenv("RECOVERY_HRV_THRESHOLD_PERCENT", "90")
        monkeypatch.setenv("RECOVERY_SLEEP_HOURS_MIN", "7.0")
        monkeypatch.setenv("RECOVERY_RESTING_HR_DEVIATION_MAX", "10")

        with patch("builtins.float", side_effect=mock_float):
            with pytest.raises(ValueError) as exc_info:
                TrainingThresholds.from_env()

            # Verify custom error message (line 125)
            assert "Invalid numeric value in thresholds configuration" in str(exc_info.value)
