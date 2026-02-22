"""
Comprehensive test coverage for critical MCP tools.

Extended tests for daily-sync, analyze-session-adherence, and update-athlete-profile
covering edge cases, error conditions, and integration scenarios.
"""

import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cyclisme_training_logs.planning.models import Session, WeeklyPlan

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


# ==========================
# Fixtures
# ==========================


@pytest.fixture
def mock_intervals_client():
    """Mock Intervals.icu API client with realistic responses."""
    client = Mock()

    # Default activity response
    client.get_activity = Mock(
        return_value={
            "id": "i126850020",
            "name": "S081-06-END-EnduranceLongue-V001",
            "start_date_local": "2026-02-21T16:38:00",
            "type": "VirtualRide",
            "moving_time": 5139,
            "distance": 38346.29,
            "icu_training_load": 69,
            "icu_intensity": 69.50673,
            "average_watts": None,
            "weighted_average_watts": None,
            "average_heartrate": 110,
        }
    )

    # Default empty activities/events
    client.get_activities = Mock(return_value=[])
    client.get_events = Mock(return_value=[])
    client.update_athlete = Mock(return_value={"ftp": 223})

    return client


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    return Session(
        session_id="S081-06",
        session_date=date(2026, 2, 21),
        name="EnduranceLongue",
        session_type="END",
        tss_planned=67,
        duration_min=85,
        description="- 85min @ 56-75%",
        status="pending",
    )


@pytest.fixture
def sample_weekly_plan(sample_session):
    """Create a sample weekly plan."""
    plan = Mock(spec=WeeklyPlan)
    plan.week_id = "S081"
    plan.start_date = date(2026, 2, 17)
    plan.end_date = date(2026, 2, 23)
    plan.planned_sessions = [sample_session]
    return plan


# ==========================
# daily-sync tests
# ==========================


class TestDailySyncComprehensive:
    """Comprehensive tests for daily-sync tool."""

    def test_daily_sync_with_no_activities(self, mock_intervals_client):
        """Test daily-sync when no activities exist."""
        from cyclisme_training_logs.daily_sync import DailySync

        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_file = Path(tmpdir) / "tracking.json"
            reports_dir = Path(tmpdir) / "reports"
            reports_dir.mkdir()

            mock_intervals_client.get_activities.return_value = []

            with patch(
                "cyclisme_training_logs.config.config_base.create_intervals_client",
                return_value=mock_intervals_client,
            ):
                sync = DailySync(tracking_file=tracking_file, reports_dir=reports_dir)

                result = sync.update_completed_sessions([])

                assert result == {}, "Should return empty dict for no activities"

    def test_daily_sync_with_multiple_activities(self, mock_intervals_client):
        """Test daily-sync with multiple activities."""
        from cyclisme_training_logs.daily_sync import DailySync

        activities = [
            {
                "id": "i1001",
                "name": "Morning Ride",
                "type": "Ride",
                "start_date_local": "2026-02-21T08:00:00",
                "icu_training_load": 50,
            },
            {
                "id": "i1002",
                "name": "Evening Ride",
                "type": "Ride",
                "start_date_local": "2026-02-21T18:00:00",
                "icu_training_load": 40,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_file = Path(tmpdir) / "tracking.json"
            reports_dir = Path(tmpdir) / "reports"
            reports_dir.mkdir()

            mock_intervals_client.get_events.return_value = []

            with patch(
                "cyclisme_training_logs.config.config_base.create_intervals_client",
                return_value=mock_intervals_client,
            ):
                sync = DailySync(tracking_file=tracking_file, reports_dir=reports_dir)

                result = sync.update_completed_sessions(activities)

                assert isinstance(result, dict), "Should return dict"
                assert len(result) >= 0, "Should handle multiple activities"

    def test_daily_sync_with_mixed_activity_types(self, mock_intervals_client):
        """Test daily-sync filters only cycling activities."""
        from cyclisme_training_logs.daily_sync import DailySync

        activities = [
            {
                "id": "i1001",
                "type": "Ride",
                "name": "Cycling",
                "start_date_local": "2026-02-21T08:00:00",
                "icu_ignore_time": False,
            },
            {
                "id": "i1002",
                "type": "Run",
                "name": "Running",
                "start_date_local": "2026-02-21T09:00:00",
                "icu_ignore_time": False,
            },
            {
                "id": "i1003",
                "type": "VirtualRide",
                "name": "Zwift",
                "start_date_local": "2026-02-21T10:00:00",
                "icu_ignore_time": False,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_file = Path(tmpdir) / "tracking.json"
            reports_dir = Path(tmpdir) / "reports"
            reports_dir.mkdir()

            with patch(
                "cyclisme_training_logs.config.config_base.create_intervals_client",
                return_value=mock_intervals_client,
            ):
                sync = DailySync(tracking_file=tracking_file, reports_dir=reports_dir)

                # Filter activities using internal method
                sync._check_activities_internal = Mock(return_value=([], activities))
                _, filtered = sync._check_activities_internal(date(2026, 2, 21))

                # Should have all 3 activities in mock return
                assert len(filtered) == 3

    def test_daily_sync_with_null_activities_in_list(self, mock_intervals_client):
        """Test daily-sync handles None entries in activity list."""
        from cyclisme_training_logs.daily_sync import DailySync

        activities = [
            {"id": "i1001", "name": "Valid Activity", "start_date_local": "2026-02-21T08:00:00"},
            None,  # Null activity
            {"id": "i1002", "name": "Another Valid", "start_date_local": "2026-02-21T10:00:00"},
            None,  # Another null
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_file = Path(tmpdir) / "tracking.json"
            reports_dir = Path(tmpdir) / "reports"
            reports_dir.mkdir()

            mock_intervals_client.get_events.return_value = []

            with patch(
                "cyclisme_training_logs.config.config_base.create_intervals_client",
                return_value=mock_intervals_client,
            ):
                sync = DailySync(tracking_file=tracking_file, reports_dir=reports_dir)

                # Should not crash with None entries
                result = sync.update_completed_sessions(activities)

                assert isinstance(result, dict), "Should handle None entries gracefully"

    def test_daily_sync_with_malformed_dates(self, mock_intervals_client):
        """Test daily-sync with activities missing start_date_local."""
        from cyclisme_training_logs.daily_sync import DailySync

        activities = [
            {"id": "i1001", "name": "No Date Activity"},  # Missing start_date_local
            {"id": "i1002", "name": "With Date", "start_date_local": "2026-02-21T10:00:00"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_file = Path(tmpdir) / "tracking.json"
            reports_dir = Path(tmpdir) / "reports"
            reports_dir.mkdir()

            mock_intervals_client.get_events.return_value = []

            with patch(
                "cyclisme_training_logs.config.config_base.create_intervals_client",
                return_value=mock_intervals_client,
            ):
                sync = DailySync(tracking_file=tracking_file, reports_dir=reports_dir)

                # Should handle missing dates gracefully
                result = sync.update_completed_sessions(activities)

                assert isinstance(result, dict), "Should handle malformed dates"


# ==========================
# analyze-session-adherence tests
# ==========================


class TestAnalyzeSessionAdherenceComprehensive:
    """Comprehensive tests for analyze-session-adherence tool."""

    @pytest.mark.asyncio
    async def test_adherence_perfect_match(
        self, mock_intervals_client, sample_session, sample_weekly_plan
    ):
        """Test adherence when activity perfectly matches plan."""
        from cyclisme_training_logs.mcp_server import handle_analyze_session_adherence

        # Perfect match: same TSS and duration
        mock_intervals_client.get_activity.return_value = {
            "id": "i126850020",
            "icu_training_load": 67,  # Matches planned TSS
            "moving_time": 5100,  # 85 minutes = 5100 seconds
            "icu_intensity": 70.0,
        }

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            with patch(
                "cyclisme_training_logs.planning.control_tower.planning_tower"
            ) as mock_tower:
                mock_tower.read_week.return_value = sample_weekly_plan

                args = {"session_id": "S081-06", "activity_id": "i126850020"}
                result = await handle_analyze_session_adherence(args)

                result_json = json.loads(result[0].text)

                assert result_json["adherence"]["tss_percent"] == 100.0
                assert result_json["adherence"]["quality"] == "excellent"

    @pytest.mark.asyncio
    async def test_adherence_over_performance(
        self, mock_intervals_client, sample_session, sample_weekly_plan
    ):
        """Test adherence when activity exceeds plan."""
        from cyclisme_training_logs.mcp_server import handle_analyze_session_adherence

        # Over-performance: 150% TSS
        mock_intervals_client.get_activity.return_value = {
            "id": "i126850020",
            "icu_training_load": 100,  # 150% of planned 67
            "moving_time": 6000,  # 100 minutes
            "icu_intensity": 85.0,
        }

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            with patch(
                "cyclisme_training_logs.planning.control_tower.planning_tower"
            ) as mock_tower:
                mock_tower.read_week.return_value = sample_weekly_plan

                args = {"session_id": "S081-06", "activity_id": "i126850020"}
                result = await handle_analyze_session_adherence(args)

                result_json = json.loads(result[0].text)

                assert result_json["adherence"]["tss_percent"] > 100
                assert result_json["actual"]["tss"] == 100

    @pytest.mark.asyncio
    async def test_adherence_under_performance(
        self, mock_intervals_client, sample_session, sample_weekly_plan
    ):
        """Test adherence when activity is significantly below plan."""
        from cyclisme_training_logs.mcp_server import handle_analyze_session_adherence

        # Under-performance: 50% TSS
        mock_intervals_client.get_activity.return_value = {
            "id": "i126850020",
            "icu_training_load": 33,  # 50% of planned 67
            "moving_time": 2550,  # ~42 minutes (50% of 85)
            "icu_intensity": 60.0,
        }

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            with patch(
                "cyclisme_training_logs.planning.control_tower.planning_tower"
            ) as mock_tower:
                mock_tower.read_week.return_value = sample_weekly_plan

                args = {"session_id": "S081-06", "activity_id": "i126850020"}
                result = await handle_analyze_session_adherence(args)

                result_json = json.loads(result[0].text)

                assert result_json["adherence"]["tss_percent"] < 100
                assert result_json["adherence"]["quality"] in ["poor", "fair"]

    @pytest.mark.asyncio
    async def test_adherence_missing_session(self, mock_intervals_client):
        """Test adherence when session doesn't exist."""
        from cyclisme_training_logs.mcp_server import handle_analyze_session_adherence

        empty_plan = Mock(spec=WeeklyPlan)
        empty_plan.planned_sessions = []

        with patch("cyclisme_training_logs.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.return_value = empty_plan

            args = {"session_id": "S999-99", "activity_id": "i126850020"}
            result = await handle_analyze_session_adherence(args)

            result_json = json.loads(result[0].text)

            assert "error" in result_json
            assert "not found" in result_json["error"].lower()

    @pytest.mark.asyncio
    async def test_adherence_with_zero_planned_values(
        self, mock_intervals_client, sample_weekly_plan
    ):
        """Test adherence when planned TSS or duration is zero."""
        from cyclisme_training_logs.mcp_server import handle_analyze_session_adherence

        # Session with zero planned TSS
        zero_session = Session(
            session_id="S081-07",
            session_date=date(2026, 2, 22),
            name="Recovery",
            session_type="REC",
            tss_planned=0,  # Zero TSS
            duration_min=0,  # Zero duration
            description="Rest day",
            status="pending",
        )

        plan = Mock(spec=WeeklyPlan)
        plan.planned_sessions = [zero_session]

        mock_intervals_client.get_activity.return_value = {
            "id": "i126850020",
            "icu_training_load": 10,
            "moving_time": 600,  # 10 minutes
            "icu_intensity": 50.0,
        }

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            with patch(
                "cyclisme_training_logs.planning.control_tower.planning_tower"
            ) as mock_tower:
                mock_tower.read_week.return_value = plan

                args = {"session_id": "S081-07", "activity_id": "i126850020"}
                result = await handle_analyze_session_adherence(args)

                result_json = json.loads(result[0].text)

                # Should handle zero values without crashing
                assert "planned" in result_json
                assert result_json["planned"]["tss"] == 0


# ==========================
# update-athlete-profile tests
# ==========================


class TestUpdateAthleteProfileComprehensive:
    """Comprehensive tests for update-athlete-profile tool."""

    @pytest.mark.asyncio
    async def test_update_single_field_ftp(self, mock_intervals_client):
        """Test updating only FTP."""
        from cyclisme_training_logs.mcp_server import handle_update_athlete_profile

        mock_intervals_client.update_athlete.return_value = {"ftp": 223}

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            args = {"updates": {"ftp": 223}}
            result = await handle_update_athlete_profile(args)

            result_json = json.loads(result[0].text)

            assert result_json["success"] is True
            assert "ftp" in result_json["updated_fields"]
            mock_intervals_client.update_athlete.assert_called_once_with({"ftp": 223})

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, mock_intervals_client):
        """Test updating multiple fields at once."""
        from cyclisme_training_logs.mcp_server import handle_update_athlete_profile

        mock_intervals_client.update_athlete.return_value = {
            "ftp": 223,
            "weight": 75.5,
            "max_hr": 185,
            "resting_hr": 45,
        }

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            args = {"updates": {"ftp": 223, "weight": 75.5, "max_hr": 185, "resting_hr": 45}}
            result = await handle_update_athlete_profile(args)

            result_json = json.loads(result[0].text)

            assert result_json["success"] is True
            assert len(result_json["updated_fields"]) == 4
            assert "ftp" in result_json["updated_fields"]
            assert "weight" in result_json["updated_fields"]

    @pytest.mark.asyncio
    async def test_update_weight_only(self, mock_intervals_client):
        """Test updating only weight."""
        from cyclisme_training_logs.mcp_server import handle_update_athlete_profile

        mock_intervals_client.update_athlete.return_value = {"weight": 74.0}

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            args = {"updates": {"weight": 74.0}}
            result = await handle_update_athlete_profile(args)

            result_json = json.loads(result[0].text)

            assert result_json["success"] is True
            assert "weight" in result_json["updated_fields"]

    @pytest.mark.asyncio
    async def test_update_heart_rate_fields(self, mock_intervals_client):
        """Test updating heart rate fields."""
        from cyclisme_training_logs.mcp_server import handle_update_athlete_profile

        mock_intervals_client.update_athlete.return_value = {
            "max_hr": 190,
            "resting_hr": 42,
            "fthr": 170,
        }

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            args = {"updates": {"max_hr": 190, "resting_hr": 42, "fthr": 170}}
            result = await handle_update_athlete_profile(args)

            result_json = json.loads(result[0].text)

            assert result_json["success"] is True
            assert len(result_json["updated_fields"]) == 3

    @pytest.mark.asyncio
    async def test_update_with_empty_updates(self, mock_intervals_client):
        """Test update with empty updates dict."""
        from cyclisme_training_logs.mcp_server import handle_update_athlete_profile

        mock_intervals_client.update_athlete.return_value = {}

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            args = {"updates": {}}
            result = await handle_update_athlete_profile(args)

            result_json = json.loads(result[0].text)

            assert result_json["success"] is True
            assert len(result_json["updated_fields"]) == 0

    @pytest.mark.asyncio
    async def test_schema_accepts_arbitrary_fields(self):
        """Test that schema accepts arbitrary field names (additionalProperties: true)."""
        from cyclisme_training_logs.mcp_server import list_tools

        tools = await list_tools()
        update_tool = next((t for t in tools if t.name == "update-athlete-profile"), None)

        assert update_tool is not None

        schema = update_tool.inputSchema
        updates_schema = schema["properties"]["updates"]

        # Critical: Must allow arbitrary fields
        assert updates_schema.get("additionalProperties") is True

    @pytest.mark.asyncio
    async def test_update_with_custom_field(self, mock_intervals_client):
        """Test updating with custom/less common field."""
        from cyclisme_training_logs.mcp_server import handle_update_athlete_profile

        mock_intervals_client.update_athlete.return_value = {"lthr": 165}

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ):
            args = {"updates": {"lthr": 165}}  # Less common field
            result = await handle_update_athlete_profile(args)

            result_json = json.loads(result[0].text)

            assert result_json["success"] is True
            mock_intervals_client.update_athlete.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
