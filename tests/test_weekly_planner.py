"""Tests for WeeklyPlanner.

Covers:
- Initialization with mock API
- Week number calculations
- collect_current_metrics with mock API
- _mock_current_metrics fallback
- run() workflow with all mocks
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.weekly_planner import WeeklyPlanner


@pytest.fixture
def mock_api():
    """Create mock IntervalsClient."""
    api = MagicMock()
    api.athlete_id = "i12345"
    return api


@pytest.fixture
def project_root(tmp_path):
    """Create temporary project root with required structure."""
    refs = tmp_path / "references"
    refs.mkdir()
    return tmp_path


@pytest.fixture
def planner(mock_api, project_root):
    """Create WeeklyPlanner with mocked API and data config."""
    with (
        patch(
            "magma_cycling.weekly_planner.create_intervals_client",
            return_value=mock_api,
        ),
        patch("magma_cycling.config.get_data_config") as mock_config,
    ):
        config = MagicMock()
        config.week_planning_dir = project_root / "planning"
        config.data_repo_path = project_root / "data"
        mock_config.return_value = config
        (project_root / "planning").mkdir(exist_ok=True)

        p = WeeklyPlanner(
            week_number="S090",
            start_date=datetime(2026, 3, 9),
            project_root=project_root,
        )
    return p


@pytest.fixture
def planner_no_api(project_root):
    """Create WeeklyPlanner without API."""
    with (
        patch(
            "magma_cycling.weekly_planner.create_intervals_client",
            side_effect=ValueError("No API"),
        ),
        patch("magma_cycling.config.get_data_config") as mock_config,
    ):
        config = MagicMock()
        config.week_planning_dir = project_root / "planning"
        config.data_repo_path = project_root / "data"
        mock_config.return_value = config
        (project_root / "planning").mkdir(exist_ok=True)

        p = WeeklyPlanner(
            week_number="S090",
            start_date=datetime(2026, 3, 9),
            project_root=project_root,
        )
    return p


class TestInitialization:
    """Test WeeklyPlanner initialization."""

    def test_basic_init(self, planner):
        """Test basic initialization."""
        assert planner.week_number == "S090"
        assert planner.start_date == datetime(2026, 3, 9)
        assert planner.end_date == datetime(2026, 3, 15)
        assert planner.api is not None

    def test_init_without_api(self, planner_no_api):
        """Test initialization when API is unavailable."""
        assert planner_no_api.week_number == "S090"
        assert planner_no_api.api is None


class TestWeekNumberCalculations:
    """Test week number helper methods."""

    def test_previous_week_number(self, planner):
        """Test previous week calculation."""
        assert planner._previous_week_number() == "S089"

    def test_next_week_number(self, planner):
        """Test next week calculation."""
        assert planner._next_week_number() == "S091"

    def test_week_after_next(self, planner):
        """Test week after next calculation."""
        assert planner._week_after_next() == "S092"

    def test_week_number_formatting(self, planner):
        """Test 3-digit zero-padded formatting."""
        planner.week_number = "S005"
        assert planner._previous_week_number() == "S004"
        assert planner._next_week_number() == "S006"


class TestCollectCurrentMetrics:
    """Test collect_current_metrics with mock API."""

    def test_collects_from_api(self, planner, mock_api):
        """Test metrics collection from API."""
        mock_api.get_wellness.return_value = [
            {
                "ctl": 65.0,
                "atl": 58.0,
                "tsb": 7.0,
                "weight": 84.5,
                "restingHR": 52,
                "hrv": 48,
            }
        ]

        metrics = planner.collect_current_metrics()

        assert metrics["ctl"] == 65.0
        assert metrics["atl"] == 58.0
        assert metrics["tsb"] == 7.0
        assert metrics["weight"] == 84.5
        assert metrics["resting_hr"] == 52

    def test_fallback_when_no_wellness(self, planner, mock_api):
        """Test fallback when API returns empty wellness."""
        mock_api.get_wellness.return_value = []

        metrics = planner.collect_current_metrics()

        assert metrics["ctl"] == 0
        assert "note" in metrics

    def test_fallback_on_api_error(self, planner, mock_api):
        """Test fallback when API raises error."""
        mock_api.get_wellness.side_effect = Exception("API down")

        metrics = planner.collect_current_metrics()

        assert metrics["ctl"] == 0
        assert "note" in metrics

    def test_fallback_no_api(self, planner_no_api):
        """Test fallback when no API configured."""
        metrics = planner_no_api.collect_current_metrics()

        assert metrics["ctl"] == 0
        assert "note" in metrics


class TestMockCurrentMetrics:
    """Test _mock_current_metrics."""

    def test_returns_zeroed_metrics(self, planner):
        """Test mock metrics have all required keys."""
        metrics = planner._mock_current_metrics()

        assert metrics["ctl"] == 0
        assert metrics["atl"] == 0
        assert metrics["tsb"] == 0
        assert metrics["weight"] == 0
        assert "date" in metrics
        assert "note" in metrics


class TestRunWorkflow:
    """Test the full run() workflow."""

    def test_run_completes(self, planner, mock_api):
        """Test run() executes all steps without errors."""
        # Mock API for metrics collection
        mock_api.get_wellness.return_value = [
            {"ctl": 60.0, "atl": 55.0, "tsb": 5.0, "weight": 84.0, "restingHR": 55, "hrv": 40}
        ]

        # Mock all mixin methods
        with (
            patch.object(planner, "load_previous_week_bilan", return_value="## Bilan S089"),
            patch.object(planner, "load_context_files", return_value={}),
            patch.object(
                planner,
                "generate_planning_prompt",
                return_value="Planning prompt",
            ),
            patch.object(planner, "save_planning_json"),
            patch.object(planner, "copy_to_clipboard", return_value=True),
        ):
            planner.run()

        assert planner.current_metrics["ctl"] == 60.0
        assert planner.previous_week_bilan == "## Bilan S089"

    def test_run_without_api(self, planner_no_api):
        """Test run() works without API (fallback metrics)."""
        with (
            patch.object(planner_no_api, "load_previous_week_bilan", return_value=""),
            patch.object(planner_no_api, "load_context_files", return_value={}),
            patch.object(
                planner_no_api,
                "generate_planning_prompt",
                return_value="Planning prompt",
            ),
            patch.object(planner_no_api, "save_planning_json"),
            patch.object(planner_no_api, "copy_to_clipboard", return_value=False),
        ):
            planner_no_api.run()

        assert planner_no_api.current_metrics["ctl"] == 0
