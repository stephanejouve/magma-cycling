"""Tests for stale bilan detection, live bilan enrichment, and workout analyses loading."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.planning.models import Session, WeeklyPlan
from magma_cycling.workflows.planner.context_loading import ContextLoadingMixin

PATCH_TOWER = "magma_cycling.planning.control_tower.planning_tower"
PATCH_CLIENT = "magma_cycling.config.create_intervals_client"


def _make_session(session_id, session_type, name, tss, duration, status, **kwargs):
    """Helper to create a Session with required fields."""
    sess_num = int(session_id.split("-")[1])
    base_date = date(2026, 3, 9)  # Monday of S084
    session_date = base_date + timedelta(days=sess_num - 1)

    params = {
        "session_id": session_id,
        "date": session_date,
        "name": name,
        "type": session_type,
        "tss_planned": tss,
        "duration_min": duration,
        "status": status,
    }
    if status in ("skipped", "cancelled", "replaced"):
        params["reason"] = kwargs.get("reason", "test reason")
    params.update(kwargs)
    return Session(**params)


def _make_plan(week_id, sessions):
    """Helper to create a WeeklyPlan."""
    start = date(2026, 3, 9)
    return WeeklyPlan(
        week_id=week_id,
        start_date=start,
        end_date=date(2026, 3, 15),
        created_at=datetime(2026, 3, 9, tzinfo=UTC),
        last_updated=datetime(2026, 3, 9, tzinfo=UTC),
        version=1,
        athlete_id="i12345",
        tss_target=400,
        planned_sessions=sessions,
    )


class FakePlanner(ContextLoadingMixin):
    """Minimal planner stub for testing ContextLoadingMixin."""

    def __init__(self, week_number, weekly_reports_dir):
        self.week_number = week_number
        self.weekly_reports_dir = Path(weekly_reports_dir)

    def _previous_week_number(self):
        num = int(self.week_number[1:])
        return f"S{num - 1:03d}"


@pytest.fixture
def tmp_planner(tmp_path):
    """Create a FakePlanner with temp directories."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    return FakePlanner("S085", reports_dir)


@pytest.fixture
def s084_dir(tmp_planner):
    """Create the S084 report directory."""
    d = tmp_planner.weekly_reports_dir / "S084"
    d.mkdir()
    return d


def _plan_with_completed_sessions(**overrides):
    """Return a plan with 3 completed + 1 cancelled + 1 rest_day session."""
    return _make_plan(
        "S084",
        [
            _make_session(
                "S084-01",
                "END",
                "EnduranceDouce",
                50,
                60,
                "completed",
                **overrides.get("s01", {}),
            ),
            _make_session(
                "S084-02",
                "INT",
                "SweetSpot",
                90,
                75,
                "completed",
                **overrides.get("s02", {}),
            ),
            _make_session(
                "S084-03",
                "REC",
                "Recuperation",
                30,
                45,
                "completed",
                **overrides.get("s03", {}),
            ),
            _make_session("S084-04", "VO2", "VO2max", 110, 60, "cancelled", reason="fatigue"),
            _make_session("S084-05", "END", "Repos", 0, 0, "rest_day"),
        ],
    )


def _plan_with_intervals_ids():
    """Return a plan where completed sessions have intervals_id set."""
    return _plan_with_completed_sessions(
        s01={"intervals_id": 1001},
        s02={"intervals_id": 1002},
        s03={"intervals_id": 1003},
    )


def _mock_intervals_client(activities, events):
    """Create a mock IntervalsClient returning given activities and events."""
    client = MagicMock()
    client.get_activities.return_value = activities
    client.get_events.return_value = events
    return client


# =============================================================================
# Phase 1 tests: stale detection + live bilan from Control Tower
# =============================================================================


class TestStaleBilanEnriched:
    """Bilan with 0% compliance is replaced by live data."""

    def test_stale_bilan_enriched(self, tmp_planner, s084_dir):
        """Stale bilan (0% compliance) is replaced by live Control Tower data."""
        stale_bilan = (
            "# Bilan Final S084\n"
            "- Compliance : 0.0%\n"
            "- Séances exécutées : 0\n"
            "- TSS total : 0\n"
        )
        (s084_dir / "bilan_final_s084.md").write_text(stale_bilan, encoding="utf-8")

        plan = _plan_with_completed_sessions()

        with patch(PATCH_TOWER) as mock_tower:
            mock_tower.read_week.return_value = plan
            result = tmp_planner.load_previous_week_bilan()

        assert "données planning live" in result
        assert "**Compliance :** 100.0%" in result
        assert "**Séances planifiées :** 3" in result
        assert "**Séances exécutées :** 3" in result
        assert "**TSS total planifié :** 170" in result


class TestNormalBilanKept:
    """Bilan with non-zero compliance is kept as-is."""

    def test_normal_bilan_kept(self, tmp_planner, s084_dir):
        """Non-stale bilan is kept unchanged."""
        good_bilan = (
            "# Bilan Final S084\n"
            "- Compliance : 85.7%\n"
            "- Séances exécutées : 6\n"
            "- TSS total : 420\n"
        )
        (s084_dir / "bilan_final_s084.md").write_text(good_bilan, encoding="utf-8")

        result = tmp_planner.load_previous_week_bilan()

        assert "Compliance : 85.7%" in result
        assert "données planning live" not in result


class TestMissingBilanLiveFallback:
    """Missing bilan file triggers live generation from Control Tower."""

    def test_missing_bilan_live_fallback(self, tmp_planner, s084_dir):
        """Missing bilan file generates live bilan from planning data."""
        plan = _plan_with_completed_sessions()

        with patch(PATCH_TOWER) as mock_tower:
            mock_tower.read_week.return_value = plan
            result = tmp_planner.load_previous_week_bilan()

        assert "données planning live" in result
        assert "**Séances exécutées :** 3" in result


class TestMissingBilanNoPlanning:
    """Missing bilan + no planning data gives fallback message."""

    def test_missing_bilan_no_planning(self, tmp_planner, s084_dir):
        """Missing bilan with no planning data returns non-disponible message."""
        plan = _make_plan(
            "S084",
            [_make_session("S084-01", "END", "Repos", 0, 0, "rest_day")],
        )

        with patch(PATCH_TOWER) as mock_tower:
            mock_tower.read_week.return_value = plan
            result = tmp_planner.load_previous_week_bilan()

        assert "[Bilan S084 non disponible]" in result


class TestLiveBilanListsSessions:
    """Live bilan includes completed session details."""

    def test_live_bilan_lists_sessions(self, tmp_planner, s084_dir):
        """Live bilan lists each completed session with details."""
        plan = _plan_with_completed_sessions()

        with patch(PATCH_TOWER) as mock_tower:
            mock_tower.read_week.return_value = plan
            result = tmp_planner.load_previous_week_bilan()

        assert "S084-01 (END)" in result
        assert "EnduranceDouce" in result
        assert "S084-02 (INT)" in result
        assert "SweetSpot" in result
        assert "S084-03 (REC)" in result
        assert "S084-04" not in result


class TestStaleBilanZeroSessions:
    """Stale bilan with 'Séances exécutées : 0' pattern detected."""

    def test_stale_bilan_zero_sessions_pattern(self, tmp_planner, s084_dir):
        """Detect stale bilan via 'Séances exécutées : 0' pattern."""
        stale_bilan = "# Bilan Final S084\n- Compliance : N/A\n- Séances exécutées : 0\n"
        (s084_dir / "bilan_final_s084.md").write_text(stale_bilan, encoding="utf-8")

        plan = _plan_with_completed_sessions()

        with patch(PATCH_TOWER) as mock_tower:
            mock_tower.read_week.return_value = plan
            result = tmp_planner.load_previous_week_bilan()

        assert "données planning live" in result
        assert "**Séances exécutées :** 3" in result


class TestComputeLiveBilanException:
    """Control Tower exception returns None gracefully."""

    def test_control_tower_exception(self, tmp_planner):
        """_compute_live_bilan returns None if Control Tower fails."""
        with patch(PATCH_TOWER) as mock_tower:
            mock_tower.read_week.side_effect = Exception("boom")
            result = tmp_planner._compute_live_bilan("S084")

        assert result is None


# =============================================================================
# Phase 2 tests: actual TSS enrichment from Intervals.icu
# =============================================================================


class TestActualTssEnrichment:
    """Live bilan uses actual TSS from Intervals.icu when available."""

    def test_actual_tss_replaces_planned(self, tmp_planner, s084_dir):
        """Actual TSS from activities replaces planned TSS in bilan."""
        plan = _plan_with_intervals_ids()

        activities = [
            {"id": "i100", "icu_training_load": 21},
            {"id": "i200", "icu_training_load": 62},
            {"id": "i300", "icu_training_load": 175},
        ]
        events = [
            {"id": 1001, "paired_activity_id": "i100"},
            {"id": 1002, "paired_activity_id": "i200"},
            {"id": 1003, "paired_activity_id": "i300"},
        ]
        mock_client = _mock_intervals_client(activities, events)

        with (
            patch(PATCH_TOWER) as mock_tower,
            patch(PATCH_CLIENT, return_value=mock_client),
        ):
            mock_tower.read_week.return_value = plan
            result = tmp_planner.load_previous_week_bilan()

        # Total actual TSS: 21 + 62 + 175 = 258
        assert "**TSS total réel :** 258" in result
        assert "Intervals.icu" in result
        assert "TSS réel: 21" in result
        assert "TSS réel: 62" in result
        assert "TSS réel: 175" in result

    def test_partial_actual_tss(self, tmp_planner, s084_dir):
        """When only some sessions have paired activities, mix actual and planned."""
        plan = _plan_with_intervals_ids()

        # Only 2 of 3 activities matched
        activities = [
            {"id": "i100", "icu_training_load": 21},
            {"id": "i200", "icu_training_load": 62},
        ]
        events = [
            {"id": 1001, "paired_activity_id": "i100"},
            {"id": 1002, "paired_activity_id": "i200"},
            # event 1003 has no paired activity yet
            {"id": 1003},
        ]
        mock_client = _mock_intervals_client(activities, events)

        with (
            patch(PATCH_TOWER) as mock_tower,
            patch(PATCH_CLIENT, return_value=mock_client),
        ):
            mock_tower.read_week.return_value = plan
            result = tmp_planner.load_previous_week_bilan()

        # Total: 21 + 62 + 30 (planned fallback for S084-03)
        assert "**TSS total réel :** 113" in result
        assert "TSS réel: 21" in result
        assert "TSS réel: 62" in result
        assert "TSS planifié: 30" in result  # S084-03 falls back to planned

    def test_api_failure_falls_back_to_planned(self, tmp_planner, s084_dir):
        """When Intervals.icu API fails, gracefully fall back to planned TSS."""
        plan = _plan_with_intervals_ids()

        with (
            patch(PATCH_TOWER) as mock_tower,
            patch(PATCH_CLIENT, side_effect=Exception("API down")),
        ):
            mock_tower.read_week.return_value = plan
            result = tmp_planner.load_previous_week_bilan()

        assert "**TSS total planifié :** 170" in result
        assert "TSS planifié: 50" in result
        assert "TSS réel" not in result

    def test_no_intervals_id_uses_planned(self, tmp_planner, s084_dir):
        """Sessions without intervals_id always use planned TSS."""
        plan = _plan_with_completed_sessions()  # No intervals_id

        with patch(PATCH_TOWER) as mock_tower:
            mock_tower.read_week.return_value = plan
            result = tmp_planner.load_previous_week_bilan()

        assert "**TSS total planifié :** 170" in result
        assert "TSS planifié: 50" in result


class TestFetchActualTss:
    """Unit tests for _fetch_actual_tss method."""

    def test_returns_tss_map(self, tmp_planner):
        """Returns dict mapping session_id to actual TSS."""
        plan = _plan_with_intervals_ids()

        activities = [{"id": "i100", "icu_training_load": 42.7}]
        events = [{"id": 1001, "paired_activity_id": "i100"}]
        mock_client = _mock_intervals_client(activities, events)

        with patch(PATCH_CLIENT, return_value=mock_client):
            result = tmp_planner._fetch_actual_tss(plan)

        assert result == {"S084-01": 43}  # Rounded

    def test_returns_none_on_empty_match(self, tmp_planner):
        """Returns None when no sessions match activities."""
        plan = _plan_with_intervals_ids()

        mock_client = _mock_intervals_client([], [])

        with patch(PATCH_CLIENT, return_value=mock_client):
            result = tmp_planner._fetch_actual_tss(plan)

        assert result is None

    def test_returns_none_on_exception(self, tmp_planner):
        """Returns None when API call raises an exception."""
        plan = _plan_with_intervals_ids()

        with patch(PATCH_CLIENT, side_effect=Exception("timeout")):
            result = tmp_planner._fetch_actual_tss(plan)

        assert result is None


# =============================================================================
# Bug #3 tests: workout analyses split on #### subsections
# =============================================================================

HISTORY_WITH_SUBSECTIONS = """\
### S084-04-END-EnduranceLongue-V001
ID : i131572602
Date : 12/03/2026

#### Métriques Pré-séance
- CTL : 45
- ATL : 38
- TSB : 7

#### Exécution
- Durée : 174min
- TSS réel : 175
- IF : 0.72

#### Analyse Technique
Bonne tenue de cadence à 85rpm.

### S084-02-END-EnduranceModeree-V001
ID : i131059208
Date : 11/03/2026

#### Métriques Pré-séance
- CTL : 44
- ATL : 35

#### Exécution
- Durée : 65min
- TSS réel : 62

### S083-07-REC-RecupActive-V001
ID : i130000000
Date : 08/03/2026

#### Exécution
- Durée : 40min
"""

PATCH_DATA_CONFIG = "magma_cycling.config.get_data_config"


class TestWorkoutAnalysesSplit:
    """Bug #3: .split('###') truncated analyses at #### subsections."""

    def test_analyses_preserve_subsections(self, tmp_planner, tmp_path):
        """Workout analyses include #### subsection content, not just headers."""
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text(HISTORY_WITH_SUBSECTIONS, encoding="utf-8")

        mock_config = MagicMock()
        mock_config.data_repo_path = tmp_path

        with patch(PATCH_DATA_CONFIG, return_value=mock_config):
            result = tmp_planner.load_previous_week_workouts()

        # Should find 2 S084 workouts
        assert "2 séance(s) analysée(s)" in result

        # Full content preserved (not truncated at ####)
        assert "#### Métriques Pré-séance" in result
        assert "#### Exécution" in result
        assert "#### Analyse Technique" in result
        assert "TSS réel : 175" in result
        assert "Bonne tenue de cadence" in result

        # S083 should NOT be included
        assert "S083" not in result

    def test_analyses_exclude_other_weeks(self, tmp_planner, tmp_path):
        """Only previous week (S084) workouts are included."""
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text(HISTORY_WITH_SUBSECTIONS, encoding="utf-8")

        mock_config = MagicMock()
        mock_config.data_repo_path = tmp_path

        with patch(PATCH_DATA_CONFIG, return_value=mock_config):
            result = tmp_planner.load_previous_week_workouts()

        assert "S084-04" in result
        assert "S084-02" in result
        assert "S083-07" not in result

    def test_no_analyses_returns_empty(self, tmp_planner, tmp_path):
        """No matching analyses returns empty string."""
        history_file = tmp_path / "workouts-history.md"
        history_file.write_text(
            "### S082-01-END-Test-V001\n#### Exécution\n- TSS : 50\n",
            encoding="utf-8",
        )

        mock_config = MagicMock()
        mock_config.data_repo_path = tmp_path

        with patch(PATCH_DATA_CONFIG, return_value=mock_config):
            result = tmp_planner.load_previous_week_workouts()

        assert result == ""
