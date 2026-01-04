"""Tests for VETO logic integration in rest_and_cancellations.py (Sprint R2.1 P0)."""

import pytest

from cyclisme_training_logs.rest_and_cancellations import check_pre_session_veto


class TestVetoIntegration:
    """Tests for check_pre_session_veto() function."""

    @pytest.fixture
    def master_profile(self):
        """Provide standard master athlete profile (54 years)."""
        return {"age": 54, "category": "master", "sleep_dependent": True}

    @pytest.fixture
    def senior_profile(self):
        """Provide standard senior athlete profile."""
        return {"age": 35, "category": "senior", "sleep_dependent": False}

    def test_veto_critical_tsb(self, master_profile):
        """Test VETO triggered by critical TSB (<-25)."""
        wellness = {"ctl": 65.0, "atl": 95.0, "tsb": -30.0, "sleep_hours": 7.0}

        result = check_pre_session_veto(wellness, master_profile, session_intensity=95.0)

        assert result["cancel"] is True
        assert result["veto"] is True
        assert result["risk_level"] == "critical"
        assert "TSB" in result["recommendation"] or any("TSB" in f for f in result["factors"])
        assert "session_intensity" in result
        assert result["session_intensity"] == 95.0

    def test_veto_critical_ratio(self, master_profile):
        """Test VETO triggered by critical ATL/CTL ratio (>1.8)."""
        wellness = {"ctl": 50.0, "atl": 95.0, "tsb": -45.0, "sleep_hours": 7.0}  # ratio = 1.9

        result = check_pre_session_veto(wellness, master_profile)

        assert result["cancel"] is True
        assert result["risk_level"] == "critical"

    def test_veto_sleep_critical(self, master_profile):
        """Test VETO triggered by insufficient sleep (<5.5h for master)."""
        wellness = {
            "ctl": 65.0,
            "atl": 70.0,
            "tsb": -5.0,
            "sleep_hours": 5.0,  # Below 5.5h threshold
        }

        result = check_pre_session_veto(wellness, master_profile)

        assert result["cancel"] is True
        assert result["risk_level"] in ["high", "critical"]  # Can be high or critical
        assert any("sleep" in f.lower() for f in result["factors"])

    def test_veto_combined_sleep_tsb(self, master_profile):
        """Test VETO triggered by combined sleep + TSB stress."""
        wellness = {
            "ctl": 65.0,
            "atl": 82.0,
            "tsb": -17.0,  # Below -15
            "sleep_hours": 5.8,  # Below 6h (with sleep_dependent=True)
        }

        result = check_pre_session_veto(wellness, master_profile)

        assert result["cancel"] is True
        # Should trigger due to combined factors

    def test_no_veto_normal_conditions(self, master_profile):
        """Test no VETO with normal training conditions."""
        wellness = {"ctl": 65.0, "atl": 60.0, "tsb": 5.0, "sleep_hours": 7.5}

        result = check_pre_session_veto(wellness, master_profile)

        assert result["cancel"] is False
        assert result["veto"] is False
        assert result["risk_level"] in ["low", "medium"]

    def test_no_veto_optimal_recovery(self, master_profile):
        """Test no VETO with optimal recovery state."""
        wellness = {"ctl": 65.0, "atl": 55.0, "tsb": 10.0, "sleep_hours": 8.0}

        result = check_pre_session_veto(wellness, master_profile)

        assert result["cancel"] is False
        assert result["risk_level"] == "low"

    def test_veto_without_sleep_data(self, master_profile):
        """Test VETO with missing sleep data (should still work)."""
        wellness = {
            "ctl": 65.0,
            "atl": 95.0,
            "tsb": -30.0,
            # sleep_hours missing
        }

        result = check_pre_session_veto(wellness, master_profile)

        # Should still VETO based on TSB
        assert result["cancel"] is True
        assert result["risk_level"] == "critical"

    def test_tsb_calculated_if_missing(self, master_profile):
        """Test TSB calculation when not provided in wellness data."""
        wellness = {
            "ctl": 65.0,
            "atl": 95.0,
            # tsb missing, should be calculated as -30
            "sleep_hours": 7.0,
        }

        result = check_pre_session_veto(wellness, master_profile)

        # Should calculate TSB = 65 - 95 = -30 and trigger VETO
        assert result["cancel"] is True

    def test_master_vs_senior_thresholds(self, master_profile, senior_profile):
        """Test that master athlete has stricter thresholds than senior."""
        # Borderline wellness for master

        wellness = {"ctl": 65.0, "atl": 85.0, "tsb": -20.0, "sleep_hours": 6.5}

        master_result = check_pre_session_veto(wellness, master_profile)
        senior_result = check_pre_session_veto(wellness, senior_profile)

        # Master should have higher or equal risk level than senior
        # Note: Actual behavior depends on detect_overtraining_risk() implementation
        risk_levels = ["low", "medium", "high", "critical"]
        master_idx = risk_levels.index(master_result["risk_level"])
        senior_idx = risk_levels.index(senior_result["risk_level"])
        assert master_idx >= senior_idx, "Master should have equal or higher risk than senior"

    def test_result_structure(self, master_profile):
        """Test that result has all required keys."""
        wellness = {"ctl": 65.0, "atl": 60.0, "tsb": 5.0, "sleep_hours": 7.5}

        result = check_pre_session_veto(wellness, master_profile)

        # Check all required keys present
        assert "cancel" in result
        assert "veto" in result
        assert "risk_level" in result
        assert "recommendation" in result
        assert "factors" in result

        # Check types
        assert isinstance(result["cancel"], bool)
        assert isinstance(result["veto"], bool)
        assert isinstance(result["risk_level"], str)
        assert isinstance(result["recommendation"], str)
        assert isinstance(result["factors"], list)

        # Backward compatibility: cancel == veto
        assert result["cancel"] == result["veto"]

    def test_session_intensity_logged(self, master_profile):
        """Test that session intensity is included when provided and VETO triggered."""
        wellness = {"ctl": 65.0, "atl": 95.0, "tsb": -30.0, "sleep_hours": 7.0}

        result = check_pre_session_veto(wellness, master_profile, session_intensity=105.0)

        if result["cancel"]:
            assert "session_intensity" in result
            assert result["session_intensity"] == 105.0
