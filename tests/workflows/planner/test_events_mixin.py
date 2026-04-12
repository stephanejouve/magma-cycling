"""Tests for workflows/planner/events.py — EventsMixin."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.weekly_planner import WeeklyPlanner


@pytest.fixture
def project_root(tmp_path):
    """Create temporary project root with required structure."""
    refs = tmp_path / "references"
    refs.mkdir()
    return tmp_path


@pytest.fixture
def kb_dir(tmp_path):
    """Create a circuits.json in a fake data repo."""
    data_dir = tmp_path / "data" / "data" / "race_knowledge"
    data_dir.mkdir(parents=True)
    circuits = {
        "the-classic": {
            "name": "The Classic",
            "aliases": ["the classic"],
            "world": "Watopia",
            "region": "Jarvis Island",
            "distance_km": 4.87,
            "elevation_m": 46,
            "profile": "flat",
            "grade_avg_pct": 0.53,
            "segments": ["Jarvis KOM", "Jarvis Sprint"],
            "tactical_notes": "Drafting crucial.",
        },
    }
    (data_dir / "circuits.json").write_text(json.dumps(circuits), encoding="utf-8")
    return tmp_path / "data"


@pytest.fixture
def planner(project_root, kb_dir):
    """Create WeeklyPlanner with API mock and KB available."""
    with (
        patch(
            "magma_cycling.weekly_planner.create_intervals_client",
            side_effect=ValueError("No API"),
        ),
        patch("magma_cycling.config.get_data_config") as mock_config,
    ):
        config = MagicMock()
        config.week_planning_dir = project_root / "planning"
        config.data_repo_path = kb_dir
        mock_config.return_value = config
        (project_root / "planning").mkdir(exist_ok=True)

        p = WeeklyPlanner(
            week_number="S092",
            start_date=datetime(2026, 4, 13),
            project_root=project_root,
        )

    # Store kb_dir reference for tests that need data config
    p._test_kb_dir = kb_dir
    p.current_metrics = {"ctl": 65.0, "atl": 58.0, "tsb": 7.0, "ftp": 260}
    p.previous_week_bilan = ""
    p.context_files = {}
    return p


def _make_event(name, category="RACE", date="2026-04-14T19:00:00", desc=""):
    """Helper to create a mock event dict."""
    return {
        "name": name,
        "category": category,
        "start_date_local": date,
        "description": desc,
    }


class TestNoEvents:
    """Test when no events are available."""

    def test_no_events_returns_empty(self, planner):
        """get_events returns [] -> empty string."""
        planner.api = MagicMock()
        planner.api.get_events.return_value = []

        with patch("magma_cycling.config.get_data_config") as m:
            m.return_value.data_repo_path = planner._test_kb_dir
            result = planner._load_week_events_section()

        assert result == ""

    def test_api_unavailable_graceful(self, planner):
        """self.api is None -> empty string, no crash."""
        planner.api = None
        result = planner._load_week_events_section()
        assert result == ""

    def test_api_error_graceful(self, planner):
        """get_events raises -> empty string."""
        planner.api = MagicMock()
        planner.api.get_events.side_effect = ConnectionError("timeout")
        result = planner._load_week_events_section()
        assert result == ""


class TestEventFormatting:
    """Test event formatting and enrichment."""

    def test_race_event_formatted(self, planner):
        """A RACE event produces a markdown section."""
        planner.api = MagicMock()
        planner.api.get_events.return_value = [
            _make_event("Course du mardi", "RACE", "2026-04-15T19:00:00"),
        ]

        with patch("magma_cycling.config.get_data_config") as m:
            m.return_value.data_repo_path = planner._test_kb_dir
            result = planner._load_week_events_section()

        assert "Course du mardi" in result
        assert "RACE" in result
        assert "Competitions" in result

    def test_race_enriched_with_kb(self, planner):
        """RACE event + circuit in KB -> distance/D+/profile included."""
        planner.api = MagicMock()
        planner.api.get_events.return_value = [
            _make_event("ZRL - The Classic", "RACE", "2026-04-14T19:00:00"),
        ]

        with patch("magma_cycling.config.get_data_config") as m:
            m.return_value.data_repo_path = planner._test_kb_dir
            result = planner._load_week_events_section()

        assert "Watopia" in result
        assert "4.87" in result
        assert "Jarvis" in result
        assert "Drafting" in result

    def test_workout_events_excluded(self, planner):
        """WORKOUT events are filtered out, RACE kept."""
        planner.api = MagicMock()
        planner.api.get_events.return_value = [
            _make_event("Sweet Spot 90min", "WORKOUT", "2026-04-14T08:00:00"),
            _make_event("ZRL - The Classic", "RACE", "2026-04-14T19:00:00"),
        ]

        with patch("magma_cycling.config.get_data_config") as m:
            m.return_value.data_repo_path = planner._test_kb_dir
            result = planner._load_week_events_section()

        assert "ZRL - The Classic" in result
        assert "Sweet Spot" not in result

    def test_multiple_events_sorted(self, planner):
        """Multiple events are sorted chronologically."""
        planner.api = MagicMock()
        planner.api.get_events.return_value = [
            _make_event("Course B", "RACE", "2026-04-16T19:00:00"),
            _make_event("Course A", "RACE", "2026-04-14T10:00:00"),
        ]

        with patch("magma_cycling.config.get_data_config") as m:
            m.return_value.data_repo_path = planner._test_kb_dir
            result = planner._load_week_events_section()

        # Course A (14th) should appear before Course B (16th)
        pos_a = result.index("Course A")
        pos_b = result.index("Course B")
        assert pos_a < pos_b

    def test_kb_unavailable_graceful(self, planner):
        """No circuits.json -> events still formatted without enrichment."""
        planner.api = MagicMock()
        planner.api.get_events.return_value = [
            _make_event("ZRL - The Classic", "RACE"),
        ]

        with patch("magma_cycling.config.get_data_config") as m:
            # Point to a dir without circuits.json
            m.return_value.data_repo_path = planner._test_kb_dir.parent / "empty"
            result = planner._load_week_events_section()

        assert "ZRL - The Classic" in result
        # No enrichment, but no crash
        assert "Watopia" not in result
