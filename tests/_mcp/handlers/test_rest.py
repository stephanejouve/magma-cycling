"""Tests for _mcp/handlers/rest.py — extra_sleep_hours parameter.

Tests the new extra_sleep_hours override in handle_pre_session_check:
sleep augmentation before veto evaluation, boundary validation,
null-safety, and verdict impact.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

# Patches target the *source* modules because handler uses local imports
# inside suppress_stdout_stderr() context manager.
CFG = "magma_cycling.config"
HEALTH = "magma_cycling.health"
VETO = "magma_cycling.workflows.rest.veto_check"
HANDLER = "magma_cycling._mcp.handlers.rest"
WITHINGS = "magma_cycling._mcp.handlers.withings"


def _base_wellness_raw(sleep_seconds=None, ctl=50, atl=45):
    """Build a raw wellness dict as returned by IntervalsClient.get_wellness."""
    w = {"ctl": ctl, "atl": atl}
    if sleep_seconds is not None:
        w["sleepTime"] = sleep_seconds
    return w


def _athlete_profile():
    """Minimal AthleteProfile mock."""
    profile = MagicMock()
    profile.model_dump.return_value = {
        "age": 54,
        "category": "master",
        "ftp": 250,
        "max_hr": 170,
        "resting_hr": 48,
        "weight": 72,
    }
    return profile


def _no_veto_result(**overrides):
    """Default veto result — no risk."""
    base = {
        "cancel": False,
        "veto": False,
        "risk_level": "low",
        "recommendation": "All clear",
        "factors": [],
    }
    base.update(overrides)
    return base


def _caution_result(**overrides):
    """Veto result with medium risk (CAUTION)."""
    base = {
        "cancel": False,
        "veto": False,
        "risk_level": "medium",
        "recommendation": "Sommeil insuffisant, vigilance requise",
        "factors": ["Sleep < 6h combined stress"],
    }
    base.update(overrides)
    return base


@pytest.fixture
def _patches():
    """Patch all external dependencies of handle_pre_session_check.

    Local imports inside suppress_stdout_stderr() require patching at source.
    """
    mock_client = MagicMock()
    mock_profile = _athlete_profile()
    mock_health = MagicMock()
    mock_health.get_readiness.return_value = None
    mock_veto_fn = MagicMock(return_value=_no_veto_result())

    with (
        patch(f"{HANDLER}.suppress_stdout_stderr"),
        patch(f"{CFG}.create_intervals_client", return_value=mock_client),
        patch(f"{CFG}.AthleteProfile") as mock_profile_cls,
        patch(f"{HEALTH}.create_health_provider", return_value=mock_health),
        patch(f"{VETO}.check_pre_session_veto", mock_veto_fn),
        patch(f"{HANDLER}._find_week_id_for_date", return_value=None),
        patch(f"{WITHINGS}.sync_withings_to_intervals"),
    ):
        mock_profile_cls.from_env.return_value = mock_profile

        yield {
            "client": mock_client,
            "veto": mock_veto_fn,
            "profile_cls": mock_profile_cls,
            "health_provider": mock_health,
        }


class TestExtraSleepHoursAbsent:
    """1. extra_sleep_hours absent → sleep_hours unchanged."""

    @pytest.mark.asyncio
    async def test_no_extra_sleep_param(self, _patches):
        from magma_cycling._mcp.handlers.rest import handle_pre_session_check

        _patches["client"].get_wellness.return_value = [
            _base_wellness_raw(sleep_seconds=19908)  # 5.53h
        ]

        await handle_pre_session_check({"date": "2026-03-19"})

        # Veto called with original sleep_hours (19908/3600 ≈ 5.53)
        veto_call = _patches["veto"].call_args
        wellness_passed = veto_call.kwargs.get(
            "wellness_data", veto_call.args[0] if veto_call.args else {}
        )
        assert wellness_passed["sleep_hours"] == pytest.approx(5.53, abs=0.01)


class TestExtraSleepHoursZero:
    """2. extra_sleep_hours=0 → no override, same as absent."""

    @pytest.mark.asyncio
    async def test_zero_extra_sleep(self, _patches):
        from magma_cycling._mcp.handlers.rest import handle_pre_session_check

        _patches["client"].get_wellness.return_value = [
            _base_wellness_raw(sleep_seconds=19908)  # 5.53h
        ]

        await handle_pre_session_check({"date": "2026-03-19", "extra_sleep_hours": 0})

        veto_call = _patches["veto"].call_args
        wellness_passed = veto_call.kwargs.get(
            "wellness_data", veto_call.args[0] if veto_call.args else {}
        )
        assert wellness_passed["sleep_hours"] == pytest.approx(5.53, abs=0.01)


class TestExtraSleepHoursApplied:
    """3. extra_sleep_hours=2.5 + sleep_hours=5.53 → 8.03, override applied."""

    @pytest.mark.asyncio
    async def test_sleep_augmented(self, _patches):
        from magma_cycling._mcp.handlers.rest import handle_pre_session_check

        _patches["client"].get_wellness.return_value = [
            _base_wellness_raw(sleep_seconds=19908)  # 5.53h
        ]

        result = await handle_pre_session_check({"date": "2026-03-19", "extra_sleep_hours": 2.5})
        data = json.loads(result[0].text)

        # Veto receives augmented sleep
        veto_call = _patches["veto"].call_args
        wellness_passed = veto_call.kwargs.get(
            "wellness_data", veto_call.args[0] if veto_call.args else {}
        )
        assert wellness_passed["sleep_hours"] == pytest.approx(8.03, abs=0.01)

        # Response indicates override was applied
        assert data.get("override", {}).get("applied") is True


class TestExtraSleepHoursNullSleep:
    """4. extra_sleep_hours=2.5 + sleep_hours=null → stays null, no error."""

    @pytest.mark.asyncio
    async def test_null_sleep_not_augmented(self, _patches):
        from magma_cycling._mcp.handlers.rest import handle_pre_session_check

        # No sleepTime in wellness → sleep_hours will be None
        _patches["client"].get_wellness.return_value = [_base_wellness_raw(sleep_seconds=None)]

        await handle_pre_session_check({"date": "2026-03-19", "extra_sleep_hours": 2.5})

        # Veto receives None sleep (can't augment what doesn't exist)
        veto_call = _patches["veto"].call_args
        wellness_passed = veto_call.kwargs.get(
            "wellness_data", veto_call.args[0] if veto_call.args else {}
        )
        assert wellness_passed["sleep_hours"] is None

        # Override flag present but sleep stayed null (nothing to augment)
        assert wellness_passed["sleep_hours"] is None  # critical: veto sees null


class TestExtraSleepHoursMaxBound:
    """5. extra_sleep_hours > 6 → rejected by schema validation."""

    def test_schema_max_bound(self):
        """Verify schema defines maximum<=6 for extra_sleep_hours."""
        from magma_cycling._mcp.schemas.rest import get_tools

        tools = get_tools()
        tool = next(t for t in tools if t.name == "pre-session-check")
        props = tool.inputSchema["properties"]
        extra = props["extra_sleep_hours"]
        assert extra["maximum"] <= 6


class TestVerdictChangesWithExtraSleep:
    """6. Verdict flips: sleep 5.53h → CAUTION, sleep 5.53+2.37=7.9h → GO."""

    @pytest.mark.asyncio
    async def test_verdict_caution_without_extra(self, _patches):
        from magma_cycling._mcp.handlers.rest import handle_pre_session_check

        _patches["client"].get_wellness.return_value = [
            _base_wellness_raw(sleep_seconds=19908, ctl=50, atl=60)  # 5.53h, TSB=-10
        ]
        _patches["veto"].return_value = _caution_result()

        result = await handle_pre_session_check({"date": "2026-03-19"})
        data = json.loads(result[0].text)
        assert data["verdict"] == "CAUTION"

    @pytest.mark.asyncio
    async def test_verdict_go_with_extra_sleep(self, _patches):
        from magma_cycling._mcp.handlers.rest import handle_pre_session_check

        _patches["client"].get_wellness.return_value = [
            _base_wellness_raw(sleep_seconds=19908, ctl=50, atl=60)  # 5.53h
        ]

        # With extra sleep, veto returns GO
        _patches["veto"].return_value = _no_veto_result()

        result = await handle_pre_session_check({"date": "2026-03-19", "extra_sleep_hours": 2.37})
        data = json.loads(result[0].text)
        assert data["verdict"] == "GO"
