"""Tests for workflows/rest/markdown_entries.py."""

from unittest.mock import patch

from magma_cycling.workflows.rest.markdown_entries import (
    generate_cancelled_session_entry,
    generate_rest_day_entry,
    generate_skipped_session_entry,
)

# Patch at source module (lazy import inside function bodies)
_PATCH_TARGET = "magma_cycling.utils.metrics.extract_wellness_metrics"


def _mock_extract(data):
    """Mock extract_wellness_metrics to return predictable values."""
    if data is None:
        data = {}
    return {"ctl": data.get("ctl", 50), "atl": data.get("atl", 45), "tsb": data.get("tsb", 5)}


class TestGenerateRestDayEntry:
    """Tests for generate_rest_day_entry."""

    @patch(_PATCH_TARGET, _mock_extract)
    def test_rest_day_contains_session_id(self):
        """Rest day entry contains session ID."""
        session = {
            "session_id": "S090-07",
            "type": "REC",
            "name": "ReposComplet",
            "date": "2026-03-15",
        }
        result = generate_rest_day_entry(session, {"ctl": 50}, {"ctl": 50})
        assert "S090-07" in result

    @patch(_PATCH_TARGET, _mock_extract)
    def test_rest_day_contains_zero_tss(self):
        """Rest day entry shows TSS 0."""
        session = {
            "session_id": "S090-07",
            "type": "REC",
            "name": "Repos",
            "date": "2026-03-15",
        }
        result = generate_rest_day_entry(session, {"ctl": 50}, {"ctl": 50})
        assert "TSS : 0" in result

    @patch(_PATCH_TARGET, _mock_extract)
    def test_rest_day_with_feedback(self):
        """Rest day entry includes athlete feedback."""
        session = {
            "session_id": "S090-07",
            "type": "REC",
            "name": "Repos",
            "date": "2026-03-15",
        }
        feedback = {"sleep_duration": "8h", "sleep_score": 85, "hrv": 55, "resting_hr": 52}
        result = generate_rest_day_entry(session, {"ctl": 50}, {"ctl": 50}, feedback)
        assert "8h" in result
        assert "55" in result


class TestGenerateSkippedSessionEntry:
    """Tests for generate_skipped_session_entry."""

    @patch(_PATCH_TARGET, _mock_extract)
    def test_skipped_entry_contains_reason(self):
        """Skipped entry includes skip reason."""
        session = {"session_id": "S090-03", "name": "SweetSpot", "date": "2026-03-11"}
        result = generate_skipped_session_entry(session, {"ctl": 50}, reason="Fatigue")
        assert "Fatigue" in result
        assert "SAUTÉE" in result


class TestGenerateCancelledSessionEntry:
    """Tests for generate_cancelled_session_entry."""

    @patch(_PATCH_TARGET, _mock_extract)
    def test_cancelled_entry_contains_reason(self):
        """Cancelled entry includes cancellation reason."""
        session = {
            "session_id": "S090-02",
            "type": "INT",
            "name": "VO2Max",
            "date": "2026-03-10",
        }
        result = generate_cancelled_session_entry(session, {"ctl": 50}, "Maladie")
        assert "Maladie" in result
        assert "séance non réalisée" in result
