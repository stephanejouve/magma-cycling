"""Tests for workflow_state module.

Tests WorkflowState avec tmp_path : persistence, analyse tracking, sessions spéciales, feedback.
"""

import json

from magma_cycling.workflow_state import WorkflowState


class TestWorkflowStateInit:
    """Tests for WorkflowState initialization."""

    def test_init_with_project_root(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        assert state.state_file == tmp_path / ".workflow_state.json"

    def test_init_creates_default_state(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        assert state.state["last_analyzed_activity_id"] is None
        assert state.state["total_analyses"] == 0
        assert state.state["history"] == []

    def test_init_loads_existing_state(self, tmp_path):
        state_data = {
            "last_analyzed_activity_id": "i999",
            "last_analyzed_date": "2026-01-01T00:00:00",
            "total_analyses": 5,
            "history": [{"activity_id": "i999", "activity_date": None, "analyzed_at": "2026-01-01"}],
        }
        (tmp_path / ".workflow_state.json").write_text(json.dumps(state_data))
        state = WorkflowState(project_root=tmp_path)
        assert state.state["total_analyses"] == 5
        assert state.state["last_analyzed_activity_id"] == "i999"

    def test_init_handles_corrupt_json(self, tmp_path):
        (tmp_path / ".workflow_state.json").write_text("not valid json {{{")
        state = WorkflowState(project_root=tmp_path)
        assert state.state["total_analyses"] == 0


class TestMarkAnalyzed:
    """Tests for mark_analyzed()."""

    def test_mark_analyzed_updates_state(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_analyzed("i123456", "2026-03-01")
        assert state.state["last_analyzed_activity_id"] == "i123456"
        assert state.state["total_analyses"] == 1

    def test_mark_analyzed_adds_to_history(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_analyzed("i111", "2026-03-01")
        state.mark_analyzed("i222", "2026-03-02")
        assert len(state.state["history"]) == 2
        assert state.state["history"][0]["activity_id"] == "i111"
        assert state.state["history"][1]["activity_id"] == "i222"

    def test_mark_analyzed_persists_to_file(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_analyzed("i123456", "2026-03-01")

        # Reload from file
        state2 = WorkflowState(project_root=tmp_path)
        assert state2.state["last_analyzed_activity_id"] == "i123456"

    def test_history_limited_to_50(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        for i in range(60):
            state.mark_analyzed(f"i{i:03d}")
        assert len(state.state["history"]) == 50
        assert state.state["history"][0]["activity_id"] == "i010"


class TestIsActivityAnalyzed:
    """Tests for is_activity_analyzed()."""

    def test_analyzed_activity(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_analyzed("i123456")
        assert state.is_activity_analyzed("i123456") is True

    def test_not_analyzed_activity(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        assert state.is_activity_analyzed("i999999") is False


class TestIsValidActivity:
    """Tests for is_valid_activity() static method."""

    def test_valid_activity(self):
        activity = {"moving_time": 3600, "icu_training_load": 50, "icu_average_watts": 200}
        assert WorkflowState.is_valid_activity(activity) is True

    def test_too_short(self):
        activity = {"moving_time": 60, "icu_training_load": 10, "icu_average_watts": 200}
        assert WorkflowState.is_valid_activity(activity) is False

    def test_zero_tss(self):
        activity = {"moving_time": 3600, "icu_training_load": 0, "icu_average_watts": 200}
        assert WorkflowState.is_valid_activity(activity) is False

    def test_no_power_data(self):
        activity = {"moving_time": 3600, "icu_training_load": 50}
        assert WorkflowState.is_valid_activity(activity) is False

    def test_zero_watts(self):
        activity = {"moving_time": 3600, "icu_training_load": 50, "icu_average_watts": 0}
        assert WorkflowState.is_valid_activity(activity) is False

    def test_legacy_average_watts(self):
        activity = {"moving_time": 3600, "icu_training_load": 50, "average_watts": 180}
        assert WorkflowState.is_valid_activity(activity) is True

    def test_missing_moving_time(self):
        activity = {"icu_training_load": 50, "icu_average_watts": 200}
        assert WorkflowState.is_valid_activity(activity) is False


class TestGetUnanalyzedActivities:
    """Tests for get_unanalyzed_activities()."""

    def test_returns_unanalyzed(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_analyzed("i001")
        activities = [
            {"id": "i001", "moving_time": 3600, "icu_training_load": 50, "icu_average_watts": 200},
            {"id": "i002", "moving_time": 3600, "icu_training_load": 60, "icu_average_watts": 210},
        ]
        result = state.get_unanalyzed_activities(activities)
        assert len(result) == 1
        assert result[0]["id"] == "i002"

    def test_filters_invalid_activities(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        activities = [
            {"id": "i001", "moving_time": 30, "icu_training_load": 0, "icu_average_watts": 0},
            {"id": "i002", "moving_time": 3600, "icu_training_load": 60, "icu_average_watts": 210},
        ]
        result = state.get_unanalyzed_activities(activities)
        assert len(result) == 1
        assert result[0]["id"] == "i002"

    def test_skips_none_activity_id(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        activities = [
            {"id": None, "moving_time": 3600, "icu_training_load": 50, "icu_average_watts": 200},
        ]
        result = state.get_unanalyzed_activities(activities)
        assert len(result) == 0


class TestGetStats:
    """Tests for get_stats()."""

    def test_empty_stats(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        stats = state.get_stats()
        assert stats["total_analyses"] == 0
        assert stats["last_analyzed_id"] is None
        assert stats["history_count"] == 0

    def test_stats_after_analysis(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_analyzed("i001", "2026-03-01")
        state.mark_analyzed("i002", "2026-03-02")
        stats = state.get_stats()
        assert stats["total_analyses"] == 2
        assert stats["last_analyzed_id"] == "i002"
        assert stats["history_count"] == 2


class TestSpecialSessions:
    """Tests for special session tracking."""

    def test_mark_and_check_documented(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_special_session_documented("S072-07", "rest", "2026-03-01")
        assert state.is_special_session_documented("S072-07", "2026-03-01") is True

    def test_not_documented(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        assert state.is_special_session_documented("S072-07", "2026-03-01") is False

    def test_empty_session_id(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        assert state.is_special_session_documented("", "2026-03-01") is False

    def test_get_documented_specials(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_special_session_documented("S072-07", "rest", "2026-03-01")
        state.mark_special_session_documented("S073-02", "cancelled", "2026-03-05")
        specials = state.get_documented_specials()
        assert len(specials) == 2


class TestSessionFeedback:
    """Tests for session feedback persistence."""

    def test_save_and_get_feedback(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        feedback = {"rpe": 7, "comments": "Hard session", "sleep_quality": 3}
        state.save_session_feedback("i123", feedback)
        result = state.get_session_feedback("i123")
        assert result is not None
        assert result["feedback"]["rpe"] == 7

    def test_has_session_feedback(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.save_session_feedback("i123", {"rpe": 5})
        assert state.has_session_feedback("i123") is True
        assert state.has_session_feedback("i999") is False

    def test_no_feedback_returns_none(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        assert state.get_session_feedback("i999") is None


class TestReset:
    """Tests for reset()."""

    def test_reset_clears_state(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_analyzed("i001")
        state.reset()
        assert state.state["total_analyses"] == 0
        assert state.state["history"] == []
        assert state.state["last_analyzed_activity_id"] is None

    def test_reset_persists(self, tmp_path):
        state = WorkflowState(project_root=tmp_path)
        state.mark_analyzed("i001")
        state.reset()
        state2 = WorkflowState(project_root=tmp_path)
        assert state2.state["total_analyses"] == 0
