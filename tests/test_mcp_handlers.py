"""
Tests for MCP tool handlers.

Tests the critical MCP handlers to prevent regressions like:
- daily-sync returning None instead of {}
- analyze-session-adherence using wrong attribute names
- update-athlete-profile schema issues
"""

import json
from datetime import date
from unittest.mock import Mock, patch

import pytest

from cyclisme_training_logs.planning.models import Session, WeeklyPlan

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


# Fixtures


@pytest.fixture
def mock_intervals_client():
    """Mock Intervals.icu API client."""
    client = Mock()
    client.get_activities = Mock(return_value=[])
    client.get_activity = Mock(
        return_value={
            "id": "i126850020",
            "name": "Test Activity",
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
    client.get_events = Mock(return_value=[])
    client.update_athlete = Mock(return_value={"ftp": 223, "weight": 75})
    return client


@pytest.fixture
def mock_session():
    """Mock Session model."""
    return Session(
        session_id="S081-06",
        session_date=date(2026, 2, 21),
        name="EnduranceLongue",
        session_type="END",
        tss_planned=70,
        duration_min=90,
        description="Endurance de base",
        status="pending",
    )


@pytest.fixture
def mock_weekly_plan(mock_session):
    """Mock WeeklyPlan model."""
    plan = Mock(spec=WeeklyPlan)
    plan.week_id = "S081"
    plan.start_date = date(2026, 2, 17)
    plan.end_date = date(2026, 2, 23)
    plan.planned_sessions = [mock_session]
    return plan


# Test: daily-sync bug fix (activity_to_session_map returning None)


@pytest.mark.asyncio
async def test_daily_sync_empty_activities_returns_dict(mock_intervals_client, tmp_path):
    """
    Test that daily-sync returns empty dict {} instead of None
    when there are no activities.

    Bug: update_completed_sessions() was returning None instead of {},
    causing 'NoneType' object has no attribute 'get' error.
    """
    from cyclisme_training_logs.daily_sync import DailySync

    tracking_file = tmp_path / "tracking.json"
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    with patch(
        "cyclisme_training_logs.config.config_base.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        sync = DailySync(tracking_file=tracking_file, reports_dir=reports_dir, verbose=False)

        # Mock _check_activities_internal to return empty lists
        sync._check_activities_internal = Mock(return_value=([], []))

        # Call update_completed_sessions with empty activities
        result = sync.update_completed_sessions([])

        # Should return empty dict, not None
        assert result is not None, "update_completed_sessions returned None instead of {}"
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result == {}, f"Expected empty dict, got {result}"


@pytest.mark.asyncio
async def test_daily_sync_api_error_returns_dict(tmp_path):
    """
    Test that daily-sync returns empty dict {} when API call fails.

    Bug: update_completed_sessions() was returning None on exception,
    causing downstream crashes.
    """
    from cyclisme_training_logs.daily_sync import DailySync

    tracking_file = tmp_path / "tracking.json"
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    mock_client = Mock()
    mock_client.get_events.side_effect = Exception("API error")

    with patch(
        "cyclisme_training_logs.config.config_base.create_intervals_client",
        return_value=mock_client,
    ):
        sync = DailySync(tracking_file=tracking_file, reports_dir=reports_dir, verbose=False)

        # Should return empty dict on error, not None
        result = sync.update_completed_sessions([{"id": "i123"}])

        assert result is not None, "update_completed_sessions returned None on error"
        assert isinstance(result, dict), f"Expected dict on error, got {type(result)}"
        assert result == {}, f"Expected empty dict on error, got {result}"


# Test: analyze-session-adherence attribute name bug


@pytest.mark.asyncio
async def test_analyze_session_adherence_attribute_names(
    mock_intervals_client, mock_session, mock_weekly_plan
):
    """
    Test that analyze-session-adherence uses correct attribute names.

    Bug: Code was using planned_session.planned_tss instead of .tss_planned
    and planned_session.planned_duration instead of .duration_min.
    """
    from cyclisme_training_logs.mcp_server import handle_analyze_session_adherence

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        with patch("cyclisme_training_logs.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.return_value = mock_weekly_plan

            args = {"session_id": "S081-06", "activity_id": "i126850020"}

            result = await handle_analyze_session_adherence(args)

            # Should not raise AttributeError
            assert result is not None
            assert len(result) > 0

            # Parse result JSON
            result_json = json.loads(result[0].text)

            # Should have adherence data
            assert "planned" in result_json
            assert "actual" in result_json
            assert "adherence" in result_json

            # Verify it used correct attributes
            assert result_json["planned"]["tss"] == 70  # From mock_session.tss_planned
            assert (
                result_json["planned"]["duration_minutes"] == 90
            )  # From mock_session.duration_min


@pytest.mark.asyncio
async def test_analyze_session_adherence_session_not_found():
    """Test analyze-session-adherence handles session not found correctly."""
    from cyclisme_training_logs.mcp_server import handle_analyze_session_adherence

    mock_plan = Mock(spec=WeeklyPlan)
    mock_plan.planned_sessions = []  # Empty sessions

    with patch("cyclisme_training_logs.planning.control_tower.planning_tower") as mock_tower:
        mock_tower.read_week.return_value = mock_plan

        args = {"session_id": "S081-99", "activity_id": "i123"}
        result = await handle_analyze_session_adherence(args)

        result_json = json.loads(result[0].text)
        assert "error" in result_json
        assert "not found" in result_json["error"].lower()


# Test: update-athlete-profile schema validation


@pytest.mark.asyncio
async def test_update_athlete_profile_schema_allows_dynamic_fields():
    """
    Test that update-athlete-profile schema accepts dynamic fields.

    Bug: Schema was missing "additionalProperties": true, causing
    validation errors when passing fields like {"ftp": 223}.
    """
    from cyclisme_training_logs.mcp_server import list_tools

    tools = await list_tools()

    # Find update-athlete-profile tool
    update_tool = None
    for tool in tools:
        if tool.name == "update-athlete-profile":
            update_tool = tool
            break

    assert update_tool is not None, "update-athlete-profile tool not found"

    # Check schema
    schema = update_tool.inputSchema
    assert "properties" in schema
    assert "updates" in schema["properties"]

    updates_schema = schema["properties"]["updates"]
    assert updates_schema["type"] == "object"

    # Should have additionalProperties: true to allow dynamic fields
    assert (
        "additionalProperties" in updates_schema
    ), "Missing additionalProperties in updates schema"
    assert updates_schema["additionalProperties"] is True, "additionalProperties should be True"


@pytest.mark.asyncio
async def test_update_athlete_profile_accepts_ftp(mock_intervals_client):
    """Test that update-athlete-profile accepts FTP update."""
    from cyclisme_training_logs.mcp_server import handle_update_athlete_profile

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        args = {"updates": {"ftp": 223}}

        result = await handle_update_athlete_profile(args)

        result_json = json.loads(result[0].text)
        assert result_json["success"] is True
        assert "ftp" in result_json["updated_fields"]

        # Verify client was called with correct data
        mock_intervals_client.update_athlete.assert_called_once_with({"ftp": 223})


@pytest.mark.asyncio
async def test_update_athlete_profile_accepts_multiple_fields(mock_intervals_client):
    """Test that update-athlete-profile accepts multiple fields."""
    from cyclisme_training_logs.mcp_server import handle_update_athlete_profile

    mock_intervals_client.update_athlete.return_value = {"ftp": 223, "weight": 75, "max_hr": 185}

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        args = {"updates": {"ftp": 223, "weight": 75, "max_hr": 185}}

        result = await handle_update_athlete_profile(args)

        result_json = json.loads(result[0].text)
        assert result_json["success"] is True
        assert len(result_json["updated_fields"]) == 3


# Test: Session model attribute names


def test_session_model_has_correct_attributes():
    """
    Test that Session model has correct attribute names.

    Ensures tss_planned and duration_min exist (not planned_tss/planned_duration).
    """
    session = Session(
        session_id="S081-01",
        session_date=date(2026, 2, 17),
        name="Test",
        session_type="END",
        tss_planned=50,
        duration_min=60,
        description="Test",
        status="pending",
    )

    # These should exist
    assert hasattr(session, "tss_planned")
    assert hasattr(session, "duration_min")
    assert session.tss_planned == 50
    assert session.duration_min == 60

    # These should NOT exist
    assert not hasattr(session, "planned_tss")
    assert not hasattr(session, "planned_duration")


# Integration test: full daily-sync flow


@pytest.mark.asyncio
async def test_daily_sync_handler_full_flow(mock_intervals_client, mock_weekly_plan):
    """
    Integration test for daily-sync MCP handler.

    Tests the full flow from handler call to response.
    """
    from cyclisme_training_logs.mcp_server import handle_daily_sync

    # Mock activities list
    mock_intervals_client.get_activities.return_value = [
        {
            "id": "i126850020",
            "name": "S081-06-END-EnduranceLongue-V001",
            "type": "VirtualRide",
            "start_date_local": "2026-02-21T16:38:00",
            "icu_training_load": 69,
            "icu_intensity": 69.50673,
            "moving_time": 5139,
            "distance": 38346.29,
            "average_watts": None,
            "icu_ignore_time": False,
        }
    ]

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        with patch("cyclisme_training_logs.planning.control_tower.planning_tower") as mock_tower:
            mock_tower.read_week.return_value = mock_weekly_plan

            args = {"date": "2026-02-21", "week_id": "S081"}

            result = await handle_daily_sync(args)

            # Should return valid result
            assert result is not None
            assert len(result) > 0

            # Parse result
            result_json = json.loads(result[0].text)

            # Should have expected structure
            assert "date" in result_json
            assert "completed_activities" in result_json
            assert "new_activities" in result_json
            assert "activities" in result_json
            assert "status" in result_json

            # Should not have error
            assert "error" not in result_json

            # Verify activities list
            assert isinstance(result_json["activities"], list)
            if len(result_json["activities"]) > 0:
                activity = result_json["activities"][0]
                assert "activity_id" in activity
                assert "session_id" in activity  # Can be None, but key should exist


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
