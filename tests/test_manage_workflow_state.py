"""Tests for manage_workflow_state.py — CLI workflow state management.

Covers:
- show_state() output formatting
- list_activities() with empty/populated history
- remove_activity() with confirm/cancel/not found
- reset_state() with confirm/cancel
- main() argparse and action routing
"""

from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.manage_workflow_state import (
    list_activities,
    main,
    remove_activity,
    reset_state,
    show_state,
)


@pytest.fixture
def mock_state():
    """Create a mock WorkflowState with typical data."""
    state = MagicMock()
    state.get_stats.return_value = {
        "total_analyses": 42,
        "last_analyzed_id": "i129000001",
        "last_analyzed_date": "2026-03-15T14:30:00",
        "history_count": 42,
    }
    state.get_documented_specials.return_value = {}
    state.state = {
        "history": [
            {
                "activity_id": "i129000001",
                "activity_date": "2026-03-15",
                "analyzed_at": "2026-03-15T14:30:00",
            },
            {
                "activity_id": "i129000002",
                "activity_date": "2026-03-14",
                "analyzed_at": "2026-03-14T10:00:00",
            },
            {
                "activity_id": "i129000003",
                "activity_date": "2026-03-13",
                "analyzed_at": "2026-03-13T09:00:00",
            },
        ],
        "last_analyzed_activity_id": "i129000001",
        "last_analyzed_date": "2026-03-15T14:30:00",
    }
    return state


class TestShowState:
    """Test show_state() output formatting."""

    def test_show_state_prints_stats(self, mock_state, capsys):
        """Test show_state displays stats from WorkflowState."""
        show_state(mock_state)

        output = capsys.readouterr().out
        assert "42" in output
        assert "i129000001" in output
        assert "ÉTAT DU WORKFLOW" in output

    def test_show_state_with_specials(self, mock_state, capsys):
        """Test show_state displays documented special sessions."""
        mock_state.get_documented_specials.return_value = {
            "S081-REST_2026-03-10": {
                "session_id": "S081-REST",
                "date": "2026-03-10",
                "type": "rest",
            }
        }

        show_state(mock_state)

        output = capsys.readouterr().out
        assert "S081-REST" in output
        assert "2026-03-10" in output
        assert "rest" in output

    def test_show_state_no_specials(self, mock_state, capsys):
        """Test show_state without special sessions omits section."""
        show_state(mock_state)

        output = capsys.readouterr().out
        assert "Sessions spéciales" not in output


class TestListActivities:
    """Test list_activities() with various history states."""

    def test_list_empty_history(self, mock_state, capsys):
        """Test list_activities with empty history."""
        mock_state.state = {"history": []}

        list_activities(mock_state, count=10)

        output = capsys.readouterr().out
        assert "Aucune activité" in output

    def test_list_activities_default_count(self, mock_state, capsys):
        """Test list_activities shows entries in reverse order."""
        list_activities(mock_state, count=10)

        output = capsys.readouterr().out
        assert "i129000001" in output
        assert "i129000002" in output
        assert "i129000003" in output

    def test_list_activities_limited_count(self, mock_state, capsys):
        """Test list_activities respects count parameter."""
        list_activities(mock_state, count=2)

        output = capsys.readouterr().out
        # Only last 2 entries (i129000002 and i129000003 are positions 2-3)
        assert "i129000002" in output
        assert "i129000003" in output

    def test_list_activities_formats_datetime(self, mock_state, capsys):
        """Test list_activities formats analyzed_at datetime."""
        list_activities(mock_state, count=10)

        output = capsys.readouterr().out
        assert "2026-03-15 14:30:00" in output

    def test_list_activities_handles_invalid_datetime(self, mock_state, capsys):
        """Test list_activities handles invalid analyzed_at gracefully."""
        mock_state.state["history"] = [
            {
                "activity_id": "i999999999",
                "activity_date": "2026-01-01",
                "analyzed_at": "not-a-date",
            }
        ]

        list_activities(mock_state, count=10)

        output = capsys.readouterr().out
        assert "i999999999" in output
        assert "not-a-date" in output  # Passed through as-is

    def test_list_activities_handles_missing_fields(self, mock_state, capsys):
        """Test list_activities handles entries with missing fields."""
        mock_state.state["history"] = [
            {"activity_id": "i111111111"}  # No activity_date, no analyzed_at
        ]

        list_activities(mock_state, count=10)

        output = capsys.readouterr().out
        assert "i111111111" in output
        assert "N/A" in output


class TestRemoveActivity:
    """Test remove_activity() with confirm/cancel/not found."""

    def test_remove_not_found(self, mock_state, capsys):
        """Test remove_activity returns False when activity not found."""
        result = remove_activity(mock_state, "i999999999")

        assert result is False
        output = capsys.readouterr().out
        assert "non trouvée" in output

    def test_remove_confirmed(self, mock_state, capsys):
        """Test remove_activity deletes entry when confirmed."""
        with patch("builtins.input", return_value="o"):
            result = remove_activity(mock_state, "i129000002")

        assert result is True
        # Verify entry was removed from history
        remaining_ids = [h["activity_id"] for h in mock_state.state["history"]]
        assert "i129000002" not in remaining_ids
        mock_state._save_state.assert_called_once()

    def test_remove_cancelled(self, mock_state, capsys):
        """Test remove_activity aborts when user declines."""
        with patch("builtins.input", return_value="n"):
            result = remove_activity(mock_state, "i129000002")

        assert result is False
        output = capsys.readouterr().out
        assert "annulée" in output
        mock_state._save_state.assert_not_called()

    def test_remove_last_analyzed_updates_pointer(self, mock_state, capsys):
        """Test removing last_analyzed activity updates the pointer."""
        with patch("builtins.input", return_value="o"):
            result = remove_activity(mock_state, "i129000001")

        assert result is True
        # last_analyzed should be updated to next-to-last
        assert mock_state.state["last_analyzed_activity_id"] != "i129000001"

    def test_remove_last_entry_clears_pointer(self, mock_state, capsys):
        """Test removing the only entry clears last_analyzed."""
        mock_state.state = {
            "history": [
                {
                    "activity_id": "i129000001",
                    "activity_date": "2026-03-15",
                    "analyzed_at": "2026-03-15T14:30:00",
                }
            ],
            "last_analyzed_activity_id": "i129000001",
            "last_analyzed_date": "2026-03-15T14:30:00",
        }

        with patch("builtins.input", return_value="o"):
            result = remove_activity(mock_state, "i129000001")

        assert result is True
        assert mock_state.state["last_analyzed_activity_id"] is None
        assert mock_state.state["last_analyzed_date"] is None

    def test_remove_shows_occurrence_count(self, mock_state, capsys):
        """Test remove_activity shows how many occurrences found."""
        # Add duplicate
        mock_state.state["history"].append(
            {
                "activity_id": "i129000002",
                "activity_date": "2026-03-14",
                "analyzed_at": "2026-03-14T12:00:00",
            }
        )

        with patch("builtins.input", return_value="o"):
            remove_activity(mock_state, "i129000002")

        output = capsys.readouterr().out
        assert "2 occurrence(s)" in output


class TestResetState:
    """Test reset_state() with confirm/cancel."""

    def test_reset_confirmed(self, mock_state, capsys):
        """Test reset_state calls state.reset() when confirmed."""
        with patch("builtins.input", return_value="o"):
            result = reset_state(mock_state)

        assert result is True
        mock_state.reset.assert_called_once()
        output = capsys.readouterr().out
        assert "réinitialisé" in output

    def test_reset_cancelled(self, mock_state, capsys):
        """Test reset_state aborts when user declines."""
        with patch("builtins.input", return_value="n"):
            result = reset_state(mock_state)

        assert result is False
        mock_state.reset.assert_not_called()
        output = capsys.readouterr().out
        assert "annulé" in output


class TestMain:
    """Test main() CLI entry point."""

    def test_no_action_exits_with_error(self):
        """Test main exits with code 1 when no action specified."""
        with (
            patch("sys.argv", ["manage-state"]),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_show_action(self, mock_state):
        """Test --show action calls show_state."""
        with (
            patch("sys.argv", ["manage-state", "--show"]),
            patch(
                "magma_cycling.manage_workflow_state.WorkflowState",
                return_value=mock_state,
            ),
            pytest.raises(SystemExit, match="0"),
        ):
            main()

        mock_state.get_stats.assert_called_once()

    def test_list_action_default(self, mock_state):
        """Test --list action with default count."""
        with (
            patch("sys.argv", ["manage-state", "--list"]),
            patch(
                "magma_cycling.manage_workflow_state.WorkflowState",
                return_value=mock_state,
            ),
            pytest.raises(SystemExit, match="0"),
        ):
            main()

    def test_list_action_custom_count(self, mock_state):
        """Test --list N action with custom count."""
        with (
            patch("sys.argv", ["manage-state", "--list", "25"]),
            patch(
                "magma_cycling.manage_workflow_state.WorkflowState",
                return_value=mock_state,
            ),
            pytest.raises(SystemExit, match="0"),
        ):
            main()

    def test_remove_action(self, mock_state):
        """Test --remove action calls remove_activity."""
        with (
            patch("sys.argv", ["manage-state", "--remove", "i129000001"]),
            patch(
                "magma_cycling.manage_workflow_state.WorkflowState",
                return_value=mock_state,
            ),
            patch("builtins.input", return_value="o"),
            pytest.raises(SystemExit, match="0"),
        ):
            main()

        mock_state._save_state.assert_called_once()

    def test_reset_action(self, mock_state):
        """Test --reset action calls reset_state."""
        with (
            patch("sys.argv", ["manage-state", "--reset"]),
            patch(
                "magma_cycling.manage_workflow_state.WorkflowState",
                return_value=mock_state,
            ),
            patch("builtins.input", return_value="o"),
            pytest.raises(SystemExit, match="0"),
        ):
            main()

        mock_state.reset.assert_called_once()

    def test_workflow_state_load_error(self):
        """Test main exits with 1 when WorkflowState fails to load."""
        with (
            patch("sys.argv", ["manage-state", "--show"]),
            patch(
                "magma_cycling.manage_workflow_state.WorkflowState",
                side_effect=Exception("State file corrupt"),
            ),
            pytest.raises(SystemExit, match="1"),
        ):
            main()

    def test_combined_actions(self, mock_state):
        """Test --reset --show runs both actions in order."""
        with (
            patch("sys.argv", ["manage-state", "--reset", "--show"]),
            patch(
                "magma_cycling.manage_workflow_state.WorkflowState",
                return_value=mock_state,
            ),
            patch("builtins.input", return_value="o"),
            pytest.raises(SystemExit, match="0"),
        ):
            main()

        mock_state.reset.assert_called_once()
        mock_state.get_stats.assert_called_once()
