"""Tests for pre-session VETO check (P0 CRITICAL safety function).

Validates check_pre_session_veto() wrapper:
- TSB fallback calculation
- Result dict structure
- VETO triggers (TSB, sleep, ATL/CTL ratio, combined)
- Session intensity context
- Missing data handling
"""

from magma_cycling.workflows.rest.veto_check import check_pre_session_veto

# Standard master athlete profile for tests
MASTER_PROFILE = {"age": 54, "category": "master", "sleep_dependent": True}


class TestVetoTriggeredCriticalTSB:
    """TSB < -25 must trigger VETO."""

    def test_veto_triggered_critical_tsb(self):
        """TSB < -25 triggers cancel=True."""
        wellness = {"ctl": 65, "atl": 95, "tsb": -30, "sleep_hours": 7.5}
        result = check_pre_session_veto(wellness, MASTER_PROFILE)

        assert result["cancel"] is True
        assert result["veto"] is True
        assert result["risk_level"] == "critical"
        assert any("TSB" in f for f in result["factors"])


class TestVetoTriggeredBadSleep:
    """Sleep < 5.5h must trigger VETO."""

    def test_veto_triggered_bad_sleep(self):
        """Sleep < 5.5h triggers veto."""
        wellness = {"ctl": 65, "atl": 60, "tsb": 5, "sleep_hours": 5.0}
        result = check_pre_session_veto(wellness, MASTER_PROFILE)

        assert result["cancel"] is True
        assert result["veto"] is True
        assert any("leep" in f.lower() for f in result["factors"])


class TestVetoTriggeredHighATLRatio:
    """ATL/CTL > 1.8 must trigger VETO."""

    def test_veto_triggered_high_atl_ratio(self):
        """ATL/CTL ratio > 1.8 triggers veto."""
        wellness = {"ctl": 50, "atl": 100, "tsb": -10, "sleep_hours": 7.5}
        result = check_pre_session_veto(wellness, MASTER_PROFILE)

        assert result["cancel"] is True
        assert result["risk_level"] == "critical"
        assert any("ratio" in f.lower() for f in result["factors"])


class TestVetoTriggeredCombinedSleepTSB:
    """Sleep < 6h + TSB < -15 must trigger VETO."""

    def test_veto_triggered_combined_sleep_tsb(self):
        """Combined low sleep + fatigued TSB triggers veto."""
        wellness = {"ctl": 65, "atl": 82, "tsb": -17, "sleep_hours": 5.8}
        result = check_pre_session_veto(wellness, MASTER_PROFILE)

        assert result["cancel"] is True
        assert result["risk_level"] == "critical"
        assert any("ombined" in f or "ombined" in f.lower() for f in result["factors"])


class TestNoVetoHealthyAthlete:
    """Normal data must NOT trigger VETO."""

    def test_no_veto_healthy_athlete(self):
        """Healthy metrics produce cancel=False."""
        wellness = {"ctl": 65, "atl": 60, "tsb": 5, "sleep_hours": 7.5}
        result = check_pre_session_veto(wellness, MASTER_PROFILE)

        assert result["cancel"] is False
        assert result["veto"] is False
        assert result["risk_level"] == "low"


class TestTSBFallback:
    """TSB fallback calculation when TSB is None."""

    def test_tsb_fallback_from_ctl_atl(self):
        """TSB=None + CTL>0 calculates TSB as CTL-ATL."""
        # CTL=65, ATL=95 → TSB = 65-95 = -30 → should veto (< -25)
        wellness = {"ctl": 65, "atl": 95, "sleep_hours": 7.5}
        result = check_pre_session_veto(wellness, MASTER_PROFILE)

        assert result["cancel"] is True
        assert result["risk_level"] == "critical"

    def test_tsb_fallback_zero_no_ctl(self):
        """TSB=None + CTL=0 defaults TSB to 0 (no crash, no veto)."""
        wellness = {"ctl": 0, "atl": 0, "sleep_hours": 7.5}
        result = check_pre_session_veto(wellness, MASTER_PROFILE)

        assert result["cancel"] is False


class TestResultDictKeys:
    """Result dict must contain all expected keys."""

    def test_result_dict_keys(self):
        """All expected keys present in result."""
        wellness = {"ctl": 65, "atl": 60, "tsb": 5, "sleep_hours": 7.5}
        result = check_pre_session_veto(wellness, MASTER_PROFILE)

        expected_keys = {"cancel", "veto", "risk_level", "recommendation", "factors"}
        assert expected_keys.issubset(result.keys())
        assert isinstance(result["factors"], list)
        assert isinstance(result["recommendation"], str)


class TestSessionIntensityInResult:
    """Session intensity added to result when veto triggered."""

    def test_session_intensity_in_result(self):
        """With intensity + veto, session_intensity key is added."""
        wellness = {"ctl": 65, "atl": 95, "tsb": -30, "sleep_hours": 7.5}
        result = check_pre_session_veto(wellness, MASTER_PROFILE, session_intensity=95.0)

        assert result["cancel"] is True
        assert result["session_intensity"] == 95.0


class TestMissingSleepHours:
    """Missing sleep_hours must not crash."""

    def test_missing_sleep_hours(self):
        """No sleep_hours in wellness data does not raise."""
        wellness = {"ctl": 65, "atl": 60, "tsb": 5}
        result = check_pre_session_veto(wellness, MASTER_PROFILE)

        assert result["cancel"] is False
        assert "cancel" in result
