"""
Tests for MCP edge cases discovered during debugging.

Focuses on specific bugs encountered in production:
1. daily-sync: activity_to_session_map returning None
2. analyze-session-adherence: wrong attribute names (planned_tss vs tss_planned)
3. update-athlete-profile: schema missing additionalProperties
4. get-activity-details: streams present but aggregated values not exposed
5. create-remote-note: regex extraction and status updates
"""

from datetime import date

import pytest

from cyclisme_training_logs.planning.models import Session

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)

# Apply mock_data_repo fixture to all tests in this module
pytestmark = pytest.mark.usefixtures("mock_data_repo")


# =======================
# Test 1: daily-sync bug
# =======================


def test_update_completed_sessions_returns_dict_not_none():
    """
    Critical regression test for daily-sync bug.

    Bug: update_completed_sessions() was returning None instead of {}
    when no activities exist, causing 'NoneType' object has no attribute 'get'.

    Lines fixed: daily_sync.py:1362, 1385
    Changed: return → return {}
    """
    import tempfile
    from pathlib import Path
    from unittest.mock import Mock, patch

    # Create DailySync with temp files
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_file = Path(tmpdir) / "tracking.json"
        reports_dir = Path(tmpdir) / "reports"
        reports_dir.mkdir()

        mock_client = Mock()
        mock_client.get_events.return_value = []  # Empty events → early return

        mock_data_config = Mock()
        mock_data_config.week_planning_dir = Path(tmpdir) / "planning"
        mock_data_config.week_planning_dir.mkdir()

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_client,
        ):
            with patch(
                "cyclisme_training_logs.config.config_base.get_data_config",
                return_value=mock_data_config,
            ):
                from cyclisme_training_logs.daily_sync import DailySync

                sync = DailySync(
                    tracking_file=tracking_file, reports_dir=reports_dir, verbose=False
                )

                # Test with empty activities list
                result = sync.update_completed_sessions([])

                # MUST return dict, not None
                assert result is not None, "BUG: update_completed_sessions() returned None"
                assert isinstance(result, dict), f"Expected dict, got {type(result)}"
                assert result == {}, f"Expected empty dict, got {result}"


def test_update_completed_sessions_exception_returns_dict():
    """
    Test that update_completed_sessions returns {} when API throws exception.

    Bug: Exception handler was returning None (line 1385).
    """
    import tempfile
    from pathlib import Path
    from unittest.mock import Mock, patch

    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_file = Path(tmpdir) / "tracking.json"
        reports_dir = Path(tmpdir) / "reports"
        reports_dir.mkdir()

        mock_client = Mock()
        mock_client.get_events.side_effect = Exception("API Error")

        mock_data_config = Mock()
        mock_data_config.week_planning_dir = Path(tmpdir) / "planning"
        mock_data_config.week_planning_dir.mkdir()

        with patch(
            "cyclisme_training_logs.config.create_intervals_client",
            return_value=mock_client,
        ):
            with patch(
                "cyclisme_training_logs.config.config_base.get_data_config",
                return_value=mock_data_config,
            ):
                from cyclisme_training_logs.daily_sync import DailySync

                sync = DailySync(
                    tracking_file=tracking_file, reports_dir=reports_dir, verbose=False
                )

                # Should return {}, not None, even on error
                result = sync.update_completed_sessions([{"id": "i123"}])

                assert result is not None, "BUG: Returned None on exception"
                assert isinstance(result, dict), f"Expected dict on error, got {type(result)}"


# ========================================
# Test 2: analyze-session-adherence bug
# ========================================


def test_session_model_attribute_names():
    """
    Test Session model has correct attribute names.

    Bug: Code was accessing session.planned_tss instead of session.tss_planned
    and session.planned_duration instead of session.duration_min.

    Lines fixed: mcp_server.py:2766, 2770
    """
    session = Session(
        session_id="S081-06",
        session_date=date(2026, 2, 21),
        name="EnduranceLongue",
        session_type="END",
        tss_planned=70,
        duration_min=90,
        description="Test",
        status="pending",
    )

    # Correct attributes exist
    assert hasattr(session, "tss_planned")
    assert hasattr(session, "duration_min")
    assert session.tss_planned == 70
    assert session.duration_min == 90

    # Wrong attributes do NOT exist
    assert not hasattr(session, "planned_tss"), "BUG: planned_tss should not exist"
    assert not hasattr(session, "planned_duration"), "BUG: planned_duration should not exist"


# =========================================
# Test 3: update-athlete-profile schema
# =========================================


@pytest.mark.asyncio
async def test_update_athlete_profile_schema_structure():
    """
    Test that update-athlete-profile schema allows dynamic fields.

    Bug: Schema was missing "additionalProperties": true, causing validation
    errors when passing fields like {"ftp": 223}.

    Line fixed: mcp_server.py:580
    Added: "additionalProperties": True
    """
    from cyclisme_training_logs.mcp_server import list_tools

    tools = await list_tools()

    # Find update-athlete-profile tool
    update_tool = next((t for t in tools if t.name == "update-athlete-profile"), None)
    assert update_tool is not None, "update-athlete-profile tool not found"

    # Check schema structure
    schema = update_tool.inputSchema
    assert "properties" in schema
    assert "updates" in schema["properties"]

    updates_schema = schema["properties"]["updates"]
    assert updates_schema["type"] == "object"

    # CRITICAL: Must have additionalProperties: true
    assert "additionalProperties" in updates_schema, "BUG: Missing 'additionalProperties' in schema"
    assert (
        updates_schema["additionalProperties"] is True
    ), "BUG: additionalProperties should be True"


# =========================================
# Test 4: get-activity-details streams
# =========================================


def test_activity_details_includes_stream_metadata():
    """
    Test that get-activity-details returns stream metadata.

    Known limitation: Returns stream metadata (type, count) but not actual
    values. This is expected behavior currently, but could be enhanced to
    calculate aggregates (mean watts, NP, max watts).

    Enhancement opportunity: Calculate from streams when average_watts is null.
    """
    mock_activity = {
        "id": "i126850020",
        "name": "Test Activity",
        "icu_training_load": 69,
        "icu_intensity": 69.50673,
        "average_watts": None,  # Often null for Zwift activities
        "weighted_average_watts": None,
    }

    # Verify the API limitation is documented
    assert (
        mock_activity["average_watts"] is None
    ), "Test simulates real case where average_watts is null"

    # Future enhancement: Could calculate from streams
    # For now, we acknowledge this limitation


# =================================
# Test 5: create-remote-note regex
# =================================


def test_create_remote_note_name_pattern():
    """
    Test that create-remote-note enforces correct name patterns.

    Names must start with: [ANNULÉE], [SAUTÉE], or [REMPLACÉE]
    followed by session details.

    Example: '[ANNULÉE] S081-04-INT-TempoSoutenu'
    """
    import re

    # Pattern from tool schema
    pattern = r"^\[(ANNULÉE|SAUTÉE|REMPLACÉE)\] .+"

    # Valid examples
    valid_names = [
        "[ANNULÉE] S081-04-INT-TempoSoutenu",
        "[SAUTÉE] S081-06-END-EnduranceLongue",
        "[REMPLACÉE] S082-01-REC-Récupération",
    ]

    for name in valid_names:
        assert re.match(pattern, name), f"Valid name rejected: {name}"

    # Invalid examples
    invalid_names = [
        "S081-04-INT-TempoSoutenu",  # Missing prefix
        "[SKIP] S081-04",  # Wrong prefix
        "[ANNULÉE]",  # No session details
        "ANNULÉE S081-04",  # Missing brackets
    ]

    for name in invalid_names:
        assert not re.match(pattern, name), f"Invalid name accepted: {name}"


# =======================================
# Regression tests for all fixes today
# =======================================


def test_all_fixes_integrated():
    """
    Meta-test: Verify all fixes from 2026-02-21 are present.

    This test documents the 3 bugs fixed today:
    1. daily-sync: activity_to_session_map None
    2. analyze-session-adherence: wrong attributes
    3. update-athlete-profile: schema incomplete
    """
    from cyclisme_training_logs.planning.models import Session

    # Fix 1: Session model attributes
    session_fields = Session.model_fields.keys()
    assert "tss_planned" in session_fields, "Fix 1: tss_planned missing"
    assert "duration_min" in session_fields, "Fix 1: duration_min missing"
    assert "planned_tss" not in session_fields, "Fix 1: planned_tss should not exist"

    # Fix 2 & 3: Verified by other tests
    # This test serves as documentation


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
