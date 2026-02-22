"""
Tests for MCP tool handlers.

Tests the critical MCP handlers to prevent regressions like:
- daily-sync returning None instead of {}
- analyze-session-adherence using wrong attribute names
- update-athlete-profile schema issues
"""

import json
from datetime import date, datetime
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
    tracking_file = tmp_path / "tracking.json"
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.daily_sync import DailySync

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
    tracking_file = tmp_path / "tracking.json"
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    mock_client = Mock()
    mock_client.get_events.side_effect = Exception("API error")

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_client,
    ):
        from cyclisme_training_logs.daily_sync import DailySync

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
        "cyclisme_training_logs.daily_sync.create_intervals_client",
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


# Test: sync-remote-to-local MCP tool


@pytest.mark.asyncio
async def test_sync_remote_to_local_handler_returns_json(mock_intervals_client, tmp_path):
    """
    Test that sync-remote-to-local handler returns valid JSON response.

    Tests the MCP interface (black-box) - verifies JSON structure, not implementation.
    """
    # Create test planning file
    from cyclisme_training_logs.planning.models import Session, WeeklyPlan

    planning_dir = tmp_path / "data" / "week_planning"
    planning_dir.mkdir(parents=True)

    test_session = Session(
        session_id="S081-06",
        session_date=date(2026, 2, 21),
        name="EnduranceLongue",
        session_type="END",
        tss_planned=70,
        duration_min=90,
        description="Endurance de base",
        status="pending",
    )

    test_plan = WeeklyPlan(
        week_id="S081",
        start_date=date(2026, 2, 16),
        end_date=date(2026, 2, 22),
        created_at=datetime.now(),
        last_updated=datetime.now(),
        version=1,
        athlete_id="test_athlete",
        tss_target=0,
        planned_sessions=[test_session],
    )

    planning_file = planning_dir / "week_planning_S081.json"
    test_plan.to_json(planning_file)

    # Mock remote events
    mock_intervals_client.get_events = Mock(
        return_value=[
            {
                "id": 93703927,
                "name": "S081-06-END-EnduranceLongue-V001",
                "category": "WORKOUT",
                "start_date_local": "2026-02-21T16:30:00",
                "description": "Endurance longue",
            }
        ]
    )

    # Patch dependencies
    with (
        patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ),
        patch("cyclisme_training_logs.config.get_data_config") as mock_get_config,
        patch(
            "cyclisme_training_logs.planning.control_tower.planning_tower.planning_dir",
            planning_dir,
        ),
    ):
        # Mock data config
        mock_config = Mock()
        mock_config.week_planning_dir = planning_dir
        mock_get_config.return_value = mock_config

        # Import and call handler
        from cyclisme_training_logs.mcp_server import handle_sync_remote_to_local

        args = {"week_id": "S081", "strategy": "merge"}

        result = await handle_sync_remote_to_local(args)

        # Verify JSON response structure
        assert len(result) == 1
        result_text = result[0].text
        result_json = json.loads(result_text)

        # Should not have error
        assert "error" not in result_json

        # Verify response structure (black-box testing)
        assert "week_id" in result_json
        assert result_json["week_id"] == "S081"
        assert "strategy" in result_json
        assert "stats" in result_json
        assert "changes" in result_json

        # Verify stats structure
        stats = result_json["stats"]
        assert "sessions_added" in stats
        assert "sessions_updated" in stats
        assert "intervals_ids_fixed" in stats
        assert "sessions_removed" in stats

        # Verify changes is a list
        assert isinstance(result_json["changes"], list)


@pytest.mark.asyncio
async def test_sync_remote_to_local_planning_not_found():
    """
    Test that sync-remote-to-local returns error for non-existent week.

    Tests error handling in MCP interface.
    """
    with (
        patch("cyclisme_training_logs.config.create_intervals_client"),
        patch("cyclisme_training_logs.config.get_data_config") as mock_get_config,
    ):
        # Mock data config with non-existent directory
        mock_config = Mock()
        mock_config.week_planning_dir = Mock()
        mock_config.week_planning_dir.__truediv__ = Mock(
            return_value=Mock(exists=Mock(return_value=False))
        )
        mock_get_config.return_value = mock_config

        from cyclisme_training_logs.mcp_server import handle_sync_remote_to_local

        args = {"week_id": "S999"}

        result = await handle_sync_remote_to_local(args)

        # Should return error in JSON
        result_text = result[0].text
        result_json = json.loads(result_text)

        # Error should be present
        assert "error" in result_json or "Planning file not found" in str(result_json)


# Test: backfill-activities MCP tool


@pytest.mark.asyncio
async def test_backfill_activities_handler_returns_json(mock_intervals_client, tmp_path):
    """
    Test that backfill-activities handler returns valid JSON response.

    Tests the MCP interface (black-box) - verifies JSON structure, not implementation.
    """
    # Create test planning file
    from cyclisme_training_logs.planning.models import Session, WeeklyPlan

    planning_dir = tmp_path / "data" / "week_planning"
    planning_dir.mkdir(parents=True)

    test_session = Session(
        session_id="S081-01",
        session_date=date(2026, 2, 16),
        name="EnduranceBase",
        session_type="END",
        tss_planned=50,
        duration_min=60,
        description="Test session",
        status="pending",
    )

    test_plan = WeeklyPlan(
        week_id="S081",
        start_date=date(2026, 2, 16),
        end_date=date(2026, 2, 22),
        created_at=datetime.now(),
        last_updated=datetime.now(),
        version=1,
        athlete_id="test_athlete",
        tss_target=0,
        planned_sessions=[test_session],
    )

    planning_file = planning_dir / "week_planning_S081.json"
    test_plan.to_json(planning_file)

    # Mock activities
    mock_intervals_client.get_activities = Mock(
        return_value=[
            {
                "id": "i125641351",
                "name": "S081-01-END-EnduranceBase-V001",
                "start_date_local": "2026-02-16T10:00:00",
                "type": "VirtualRide",
            }
        ]
    )

    # Mock events (for matching)
    mock_intervals_client.get_events = Mock(return_value=[])

    # Patch dependencies
    with (
        patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ),
        patch("cyclisme_training_logs.config.get_data_config") as mock_get_config,
    ):
        # Mock data config
        mock_config = Mock()
        mock_config.week_planning_dir = planning_dir
        mock_config.data_repo_path = tmp_path
        mock_get_config.return_value = mock_config

        # Create reports dir
        (tmp_path / "reports").mkdir()

        # Import and call handler
        from cyclisme_training_logs.mcp_server import handle_backfill_activities

        args = {"week_id": "S081"}

        result = await handle_backfill_activities(args)

        # Verify JSON response structure
        assert len(result) == 1
        result_text = result[0].text
        result_json = json.loads(result_text)

        # Should not have error
        assert "error" not in result_json

        # Verify response structure (black-box testing)
        assert "message" in result_json
        assert "start_date" in result_json
        assert "end_date" in result_json
        assert "total_activities" in result_json
        assert "updated" in result_json
        assert "already_completed" in result_json
        assert "unmatched" in result_json
        assert "details" in result_json

        # Verify data types
        assert isinstance(result_json["total_activities"], int)
        assert isinstance(result_json["updated"], int)
        assert isinstance(result_json["already_completed"], int)
        assert isinstance(result_json["unmatched"], int)
        assert isinstance(result_json["details"], dict)

        # Verify details structure
        assert "updated_sessions" in result_json["details"]
        assert "already_completed_sessions" in result_json["details"]
        assert "unmatched_activities" in result_json["details"]
        assert isinstance(result_json["details"]["updated_sessions"], list)
        assert isinstance(result_json["details"]["already_completed_sessions"], list)
        assert isinstance(result_json["details"]["unmatched_activities"], list)

        # Verify math
        assert (
            result_json["updated"] + result_json["already_completed"] + result_json["unmatched"]
            == result_json["total_activities"]
        )


@pytest.mark.asyncio
async def test_backfill_activities_with_date_range(mock_intervals_client, tmp_path):
    """
    Test backfill-activities with start_date/end_date instead of week_id.

    Tests alternative input format.
    """
    # Mock activities
    mock_intervals_client.get_activities = Mock(return_value=[])
    mock_intervals_client.get_events = Mock(return_value=[])

    with (
        patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_intervals_client,
        ),
        patch("cyclisme_training_logs.config.get_data_config") as mock_get_config,
    ):
        # Mock data config
        mock_config = Mock()
        mock_config.data_repo_path = tmp_path
        mock_get_config.return_value = mock_config

        # Create reports dir
        (tmp_path / "reports").mkdir()

        from cyclisme_training_logs.mcp_server import handle_backfill_activities

        args = {"start_date": "2026-02-16", "end_date": "2026-02-22"}

        result = await handle_backfill_activities(args)

        # Verify JSON response
        result_text = result[0].text
        result_json = json.loads(result_text)

        # Should not have error
        assert "error" not in result_json

        # Verify dates in response
        assert result_json["start_date"] == "2026-02-16"
        assert result_json["end_date"] == "2026-02-22"


@pytest.mark.asyncio
async def test_get_activity_details_calculates_power_from_streams(mock_intervals_client):
    """Test that power metrics are calculated from streams when API returns null."""
    # Mock activity with null power metrics
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Test Activity",
            "start_date_local": "2026-02-22T10:00:00",
            "type": "VirtualRide",
            "moving_time": 3600,
            "distance": 30000,
            "total_elevation_gain": 500,
            "icu_training_load": 100,
            "icu_intensity": 80,
            "average_watts": None,  # API returns null
            "weighted_average_watts": None,  # API returns null
            "average_heartrate": 150,
            "average_cadence": 90,
        }
    )

    # Mock watts stream with realistic data (60 minutes at varying power)
    # Simulate intervals: 30s @ 200W, 30s @ 100W
    watts_data = [200] * 30 + [100] * 30
    watts_data = watts_data * 60  # Repeat for 60 minutes

    mock_intervals_client.get_activity_streams = Mock(
        return_value=[{"type": "watts", "data": watts_data}]
    )

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Verify power metrics were calculated
        assert result_json["average_watts"] is not None
        assert result_json["weighted_average_watts"] is not None

        # Average should be around 150W (200W + 100W) / 2
        assert 145 <= result_json["average_watts"] <= 155

        # NP should be higher due to variability
        assert result_json["weighted_average_watts"] > result_json["average_watts"]


@pytest.mark.asyncio
async def test_get_activity_details_uses_api_values_when_present(mock_intervals_client):
    """Test that API-provided power metrics are used when available."""
    # Mock activity with valid power metrics from API
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Test Activity",
            "start_date_local": "2026-02-22T10:00:00",
            "type": "VirtualRide",
            "moving_time": 3600,
            "distance": 30000,
            "icu_training_load": 100,
            "icu_intensity": 80,
            "average_watts": 180.5,  # API provides value
            "weighted_average_watts": 190.3,  # API provides value
            "average_heartrate": 150,
        }
    )

    # Mock streams for decoupling calculation
    mock_intervals_client.get_activity_streams = Mock(
        return_value=[
            {"type": "watts", "data": [180] * 3600},
            {"type": "heartrate", "data": [150] * 3600},
        ]
    )

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Verify API values are used as-is (not recalculated from streams)
        assert result_json["average_watts"] == 180.5
        assert result_json["weighted_average_watts"] == 190.3

        # Note: get_activity_streams IS called for cardiovascular decoupling calculation
        # even when power metrics are present in API


@pytest.mark.asyncio
async def test_get_activity_details_handles_missing_watts_stream(mock_intervals_client):
    """Test graceful handling when watts stream is not available."""
    # Mock activity with null power metrics
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Test Activity",
            "type": "Run",  # Running activity without power
            "moving_time": 3600,
            "average_watts": None,
            "weighted_average_watts": None,
        }
    )

    # Mock streams without watts (e.g., only HR and cadence)
    mock_intervals_client.get_activity_streams = Mock(
        return_value=[
            {"type": "heartrate", "data": [150] * 3600},
            {"type": "cadence", "data": [85] * 3600},
        ]
    )

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Should not crash, return null for power metrics
        assert result_json["average_watts"] is None
        assert result_json["weighted_average_watts"] is None


@pytest.mark.asyncio
async def test_get_activity_details_calculates_cardiovascular_decoupling(
    mock_intervals_client,
):
    """Test that cardiovascular decoupling is calculated when power and HR streams are available."""
    # Mock activity
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Test Activity",
            "type": "VirtualRide",
            "moving_time": 3600,
            "average_watts": 150,
            "weighted_average_watts": 160,
            "average_heartrate": 140,
        }
    )

    # Create realistic power and HR data showing some decoupling
    # First half: 155W at 135 HR (ratio ~1.15)
    # Second half: 155W at 145 HR (ratio ~1.07) - slight decoupling
    watts_data = [155] * 1800 + [155] * 1800  # 3600 seconds at constant power
    hr_data = [135] * 1800 + [145] * 1800  # HR drifts up in second half

    mock_intervals_client.get_activity_streams = Mock(
        return_value=[
            {"type": "watts", "data": watts_data},
            {"type": "heartrate", "data": hr_data},
        ]
    )

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Should calculate decoupling
        assert result_json["cardiovascular_decoupling"] is not None
        assert isinstance(result_json["cardiovascular_decoupling"], (int, float))
        # Should be negative (HR increased = worse efficiency)
        assert result_json["cardiovascular_decoupling"] < 0


@pytest.mark.asyncio
async def test_get_activity_details_no_decoupling_without_hr_stream(
    mock_intervals_client,
):
    """Test that decoupling is None when HR stream is not available."""
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Test Activity",
            "type": "VirtualRide",
            "moving_time": 3600,
            "average_watts": 150,
            "weighted_average_watts": 160,
        }
    )

    # Only watts stream, no HR
    mock_intervals_client.get_activity_streams = Mock(
        return_value=[
            {"type": "watts", "data": [150] * 3600},
        ]
    )

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Should return None without HR data
        assert result_json["cardiovascular_decoupling"] is None


@pytest.mark.asyncio
async def test_get_activity_details_no_decoupling_for_short_activity(
    mock_intervals_client,
):
    """Test that decoupling is None for activities shorter than 60 seconds."""
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Short Sprint",
            "type": "VirtualRide",
            "moving_time": 30,
            "average_watts": 250,
            "weighted_average_watts": 260,
        }
    )

    # Very short activity (30 seconds)
    mock_intervals_client.get_activity_streams = Mock(
        return_value=[
            {"type": "watts", "data": [250] * 30},
            {"type": "heartrate", "data": [150] * 30},
        ]
    )

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Should return None for very short activities
        assert result_json["cardiovascular_decoupling"] is None


@pytest.mark.asyncio
async def test_get_activity_details_handles_stream_fetch_exception(
    mock_intervals_client,
):
    """Test graceful handling when get_activity_streams raises an exception."""
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Test Activity",
            "type": "VirtualRide",
            "moving_time": 3600,
            "average_watts": None,
            "weighted_average_watts": None,
            "average_heartrate": 150,
        }
    )

    # Mock streams API raising an exception
    mock_intervals_client.get_activity_streams = Mock(side_effect=Exception("API timeout"))

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Should not crash, return None for metrics that need streams
        assert result_json["average_watts"] is None
        assert result_json["weighted_average_watts"] is None
        assert result_json["cardiovascular_decoupling"] is None


@pytest.mark.asyncio
async def test_get_activity_details_handles_malformed_stream_data(
    mock_intervals_client,
):
    """Test graceful handling when stream data is malformed."""
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Test Activity",
            "type": "VirtualRide",
            "moving_time": 3600,
            "average_watts": None,
            "weighted_average_watts": None,
            "average_heartrate": 150,
        }
    )

    # Mock streams with malformed data (missing 'data' key)
    mock_intervals_client.get_activity_streams = Mock(
        return_value=[
            {"type": "watts"},  # Missing 'data' key
            {"type": "heartrate", "data": [150] * 3600},
        ]
    )

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Should gracefully handle malformed data
        assert result_json["average_watts"] is None
        assert result_json["weighted_average_watts"] is None
        assert result_json["cardiovascular_decoupling"] is None


@pytest.mark.asyncio
async def test_get_activity_details_decoupling_with_all_zero_hr(
    mock_intervals_client,
):
    """Test that decoupling is None when all HR values are zero."""
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Test Activity",
            "type": "VirtualRide",
            "moving_time": 3600,
            "average_watts": 150,
            "weighted_average_watts": 160,
            "average_heartrate": 0,  # HR sensor failed
        }
    )

    # Power data exists but HR is all zeros
    mock_intervals_client.get_activity_streams = Mock(
        return_value=[
            {"type": "watts", "data": [150] * 3600},
            {"type": "heartrate", "data": [0] * 3600},  # All zeros
        ]
    )

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Should return None when HR data is unusable
        assert result_json["cardiovascular_decoupling"] is None


@pytest.mark.asyncio
async def test_get_activity_details_decoupling_with_barely_long_enough_activity(
    mock_intervals_client,
):
    """Test decoupling calculation edge case where halves are just barely < 30s each."""
    mock_intervals_client.get_activity = Mock(
        return_value={
            "id": "i123456",
            "name": "Test Activity",
            "type": "VirtualRide",
            "moving_time": 100,  # 100 seconds total, 50 seconds per half
            "average_watts": 150,
            "weighted_average_watts": 160,
            "average_heartrate": 140,
        }
    )

    # 100 seconds activity - each half will be 50 seconds (> 30s, can calculate NP)
    mock_intervals_client.get_activity_streams = Mock(
        return_value=[
            {"type": "watts", "data": [150] * 100},
            {"type": "heartrate", "data": [140] * 100},
        ]
    )

    with patch(
        "cyclisme_training_logs.config.create_intervals_client",
        return_value=mock_intervals_client,
    ):
        from cyclisme_training_logs.mcp_server import handle_get_activity_details

        result = await handle_get_activity_details(
            {"activity_id": "i123456", "include_streams": False}
        )

        result_json = json.loads(result[0].text)

        # Should calculate decoupling for activities where each half >= 30s
        assert result_json["cardiovascular_decoupling"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
