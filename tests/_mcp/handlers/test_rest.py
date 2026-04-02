"""Tests for _mcp/handlers/rest.py and patch-coach-analysis.

Part 1 — extra_sleep_hours override in handle_pre_session_check:
sleep augmentation before veto evaluation, boundary validation,
null-safety, and verdict impact.

Part 2 — patch-coach-analysis (TDD: tests written before handler):
sleep_hours correction in workouts-history.md analyses, [CORRIGÉ] marker,
note de correction, error handling.
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
HEALTH_HANDLER = "magma_cycling._mcp.handlers.health"


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
        patch(f"{HEALTH_HANDLER}.sync_health_to_calendar"),
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


# =====================================================================
# Part 2 — patch-coach-analysis (TDD: handler not yet implemented)
# =====================================================================

PATCH_HANDLER = HANDLER  # patch-coach-analysis lives in rest.py alongside pre-session-check

# --- Sample analysis content for tests ---

_ANALYSIS_SLEEP_IN_ATTENTION = """\
### S084-04-END-RecupActive-V001
ID : i131572602
Date : 15/03/2026

#### Métriques Pré-séance
- CTL : 46
- ATL : 42
- TSB : +5
- Sommeil : 5.5h

#### Exécution
- Durée : 56min
- IF : 0.74
- TSS : 51

#### Exécution Technique
Séance correctement exécutée.

#### Charge d'Entraînement
TSS conforme aux prévisions.

#### Validation Objectifs
- ✅ Zone respectée

#### Points d'Attention
- Sommeil insuffisant (5.5h), risque de récupération altérée
- Cadence légèrement basse (86rpm vs 92rpm)

#### Recommandations Progression
1. Améliorer le sommeil

#### Métriques Post-séance
- CTL : 47
- ATL : 43
- TSB : +4
"""

_ANALYSIS_NO_SLEEP_IN_ATTENTION = """\
### S084-04-END-RecupActive-V001
ID : i131572602
Date : 15/03/2026

#### Métriques Pré-séance
- CTL : 46
- ATL : 42
- TSB : +5
- Sommeil : 5.5h

#### Exécution
- Durée : 56min
- IF : 0.74
- TSS : 51

#### Points d'Attention
- Cadence légèrement basse (86rpm vs 92rpm)

#### Métriques Post-séance
- CTL : 47
- ATL : 43
- TSB : +4
"""

_ANALYSIS_NO_SLEEP_FIELD = """\
### S084-04-END-RecupActive-V001
ID : i131572602
Date : 15/03/2026

#### Métriques Pré-séance
- CTL : 46
- ATL : 42
- TSB : +5

#### Exécution
- Durée : 56min

#### Métriques Post-séance
- CTL : 47
"""


@pytest.fixture
def _patch_history():
    """Mock file I/O for workouts-history.md (no disk files)."""
    mock_path = MagicMock()
    mock_path.exists.return_value = True

    mock_config = MagicMock()
    mock_config.workouts_history_path = mock_path

    written = {}
    mock_path.write_text.side_effect = lambda content, **kw: written.update(text=content)

    def _fake_safe_write(path, content, backup_dir=None):
        path.write_text(content, encoding="utf-8")
        return None

    with (
        patch(f"{PATCH_HANDLER}.suppress_stdout_stderr"),
        patch(f"{CFG}.get_data_config", return_value=mock_config),
        patch("magma_cycling.planning.backup.safe_write", side_effect=_fake_safe_write),
    ):
        yield {
            "path": mock_path,
            "written": written,
        }


class TestPatchSleepHoursValid:
    """1. Patch sleep_hours valide → metrics_pre mis à jour, [CORRIGÉ], patches_applied."""

    @pytest.mark.asyncio
    async def test_patch_sleep_updates_metrics_pre(self, _patch_history):
        from magma_cycling._mcp.handlers.rest import handle_patch_coach_analysis

        _patch_history["path"].read_text.return_value = _ANALYSIS_SLEEP_IN_ATTENTION

        result = await handle_patch_coach_analysis(
            {"activity_id": "i131572602", "sleep_hours": 7.8}
        )
        data = json.loads(result[0].text)

        written = _patch_history["written"]["text"]
        # metrics_pre updated with new value
        assert "- Sommeil : 7.8h" in written
        # [CORRIGÉ marker present (handler appends details after tag)
        assert "[CORRIGÉ" in written
        # patches_applied in response
        assert "patches_applied" in data
        assert len(data["patches_applied"]) >= 1


class TestPatchSleepHoursWithNote:
    """2. Patch sleep_hours + note → Note de correction présent."""

    @pytest.mark.asyncio
    async def test_patch_sleep_with_note(self, _patch_history):
        from magma_cycling._mcp.handlers.rest import handle_patch_coach_analysis

        _patch_history["path"].read_text.return_value = _ANALYSIS_SLEEP_IN_ATTENTION

        result = await handle_patch_coach_analysis(
            {
                "activity_id": "i131572602",
                "sleep_hours": 7.8,
                "note": "Sieste de 2h non comptabilisée par Withings",
            }
        )
        data = json.loads(result[0].text)

        written = _patch_history["written"]["text"]
        # metrics_pre updated
        assert "- Sommeil : 7.8h" in written
        # Note de correction block present
        assert "Note de correction" in written or "note" in data
        assert "Sieste" in written


class TestPatchMissingIdentifier:
    """3. activity_id absent + session_id absent → erreur explicite."""

    @pytest.mark.asyncio
    async def test_no_identifier_returns_error(self, _patch_history):
        from magma_cycling._mcp.handlers.rest import handle_patch_coach_analysis

        with pytest.raises(ValueError, match="activity_id|session_id"):
            await handle_patch_coach_analysis({"sleep_hours": 7.8})


class TestPatchAnalysisNotFound:
    """4. activity_id fourni mais analyse introuvable → erreur explicite."""

    @pytest.mark.asyncio
    async def test_analysis_not_found(self, _patch_history):
        from magma_cycling._mcp.handlers.rest import handle_patch_coach_analysis

        _patch_history["path"].read_text.return_value = _ANALYSIS_SLEEP_IN_ATTENTION

        result = await handle_patch_coach_analysis(
            {"activity_id": "i999999999", "sleep_hours": 7.8}
        )
        data = json.loads(result[0].text)

        assert data.get("status") == "error"


class TestPatchNoSleepField:
    """5. Champ sleep_hours absent dans l'analyse → warning non bloquant, success."""

    @pytest.mark.asyncio
    async def test_no_sleep_field_warning_success(self, _patch_history):
        from magma_cycling._mcp.handlers.rest import handle_patch_coach_analysis

        _patch_history["path"].read_text.return_value = _ANALYSIS_NO_SLEEP_FIELD

        result = await handle_patch_coach_analysis(
            {"activity_id": "i131572602", "sleep_hours": 7.8}
        )
        data = json.loads(result[0].text)

        # Status success despite missing field
        assert data.get("status") == "success"
        # Warning present inside patches_applied
        patches = data.get("patches_applied", [])
        assert any(p.get("warning") for p in patches)


class TestPatchSleepInAttention:
    """6. sleep_hours dans attention section → valeur remplacée."""

    @pytest.mark.asyncio
    async def test_attention_sleep_patched(self, _patch_history):
        from magma_cycling._mcp.handlers.rest import handle_patch_coach_analysis

        _patch_history["path"].read_text.return_value = _ANALYSIS_SLEEP_IN_ATTENTION

        await handle_patch_coach_analysis({"activity_id": "i131572602", "sleep_hours": 7.8})

        written = _patch_history["written"]["text"]
        # Extract attention section
        attention_start = written.find("#### Points d'Attention")
        assert attention_start != -1, "Points d'Attention section missing"
        attention_section = written[attention_start:]
        next_section = attention_section.find("\n####", 4)
        if next_section != -1:
            attention_section = attention_section[:next_section]

        # Old sleep value replaced in attention section
        assert "5.5h" not in attention_section
        assert "7.8h" in attention_section


class TestPatchNoSleepInAttention:
    """7. sleep_hours absent dans attention → pas d'erreur, metrics_pre patché."""

    @pytest.mark.asyncio
    async def test_no_attention_sleep_no_error(self, _patch_history):
        from magma_cycling._mcp.handlers.rest import handle_patch_coach_analysis

        _patch_history["path"].read_text.return_value = _ANALYSIS_NO_SLEEP_IN_ATTENTION

        result = await handle_patch_coach_analysis(
            {"activity_id": "i131572602", "sleep_hours": 7.8}
        )
        data = json.loads(result[0].text)

        written = _patch_history["written"]["text"]
        # metrics_pre patched
        assert "- Sommeil : 7.8h" in written
        # No error
        assert "error" not in data
