"""Tests for event_sync utility module."""

from datetime import date

import pytest

from magma_cycling.utils.event_sync import (
    SyncDecision,
    calculate_description_hash,
    compute_start_time,
    evaluate_sync,
)


class TestCalculateDescriptionHash:
    """Tests for calculate_description_hash."""

    def test_returns_16_char_hex(self):
        h = calculate_description_hash("some workout description")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_input_same_hash(self):
        assert calculate_description_hash("abc") == calculate_description_hash("abc")

    def test_different_input_different_hash(self):
        assert calculate_description_hash("abc") != calculate_description_hash("xyz")

    def test_empty_string(self):
        h = calculate_description_hash("")
        assert len(h) == 16


class TestComputeStartTime:
    """Tests for compute_start_time."""

    def test_weekday_single_session(self):
        # Wednesday (weekday=2) → 17:00
        assert compute_start_time(date(2026, 3, 4), "S083-03") == "17:00:00"

    def test_saturday_single_session(self):
        # Saturday (weekday=5) → 09:00
        assert compute_start_time(date(2026, 3, 7), "S083-06") == "09:00:00"

    def test_double_session_morning(self):
        # Suffix "a" → 09:00 regardless of day
        assert compute_start_time(date(2026, 3, 4), "S083-03a") == "09:00:00"

    def test_double_session_afternoon(self):
        # Suffix "b" → 15:00 regardless of day
        assert compute_start_time(date(2026, 3, 4), "S083-03b") == "15:00:00"

    def test_sunday(self):
        # Sunday (weekday=6) → 17:00
        assert compute_start_time(date(2026, 3, 8), "S083-07") == "17:00:00"

    def test_monday(self):
        # Monday (weekday=0) → 17:00
        assert compute_start_time(date(2026, 3, 2), "S083-01") == "17:00:00"


class TestEvaluateSync:
    """Tests for evaluate_sync."""

    def _make_event_data(self, name="S083-03-INT-Test-V001", desc="workout content"):
        return {
            "category": "WORKOUT",
            "type": "VirtualRide",
            "name": name,
            "description": desc,
            "start_date_local": "2026-03-04T17:00:00",
        }

    def test_create_when_no_existing(self):
        decision = evaluate_sync(self._make_event_data(), None)
        assert decision.action == "create"
        assert decision.existing_event_id is None

    def test_skip_when_paired_activity_id(self):
        existing = {
            "id": "evt-123",
            "paired_activity_id": "act-456",
            "name": "S083-03-INT-Test-V001",
            "description": "old content",
            "start_date_local": "2026-03-04T17:00:00",
        }
        decision = evaluate_sync(self._make_event_data(), existing)
        assert decision.action == "skip"
        assert "protected" in decision.reason
        assert "act-456" in decision.reason
        assert decision.existing_event_id == "evt-123"

    def test_skip_when_paired_activity_id_even_with_force(self):
        existing = {
            "id": "evt-123",
            "paired_activity_id": "act-456",
            "name": "old-name",
            "description": "old content",
            "start_date_local": "2026-03-04T17:00:00",
        }
        decision = evaluate_sync(self._make_event_data(), existing, force_update=True)
        assert decision.action == "skip"
        assert "protected" in decision.reason

    def test_skip_when_identical_content(self):
        event_data = self._make_event_data()
        existing = {
            "id": "evt-123",
            "name": event_data["name"],
            "description": event_data["description"],
            "start_date_local": event_data["start_date_local"],
        }
        decision = evaluate_sync(event_data, existing)
        assert decision.action == "skip"
        assert "identical" in decision.reason

    def test_update_when_description_changed(self):
        event_data = self._make_event_data(desc="new workout content")
        existing = {
            "id": "evt-123",
            "name": event_data["name"],
            "description": "old workout content",
            "start_date_local": event_data["start_date_local"],
        }
        decision = evaluate_sync(event_data, existing)
        assert decision.action == "update"
        assert "content changed" in decision.reason
        assert decision.existing_event_id == "evt-123"

    def test_update_when_name_changed(self):
        event_data = self._make_event_data()
        existing = {
            "id": "evt-123",
            "name": "S083-03-INT-OldName-V001",
            "description": event_data["description"],
            "start_date_local": event_data["start_date_local"],
        }
        decision = evaluate_sync(event_data, existing)
        assert decision.action == "update"
        assert "content changed" in decision.reason

    def test_update_when_start_time_changed(self):
        event_data = self._make_event_data()
        existing = {
            "id": "evt-123",
            "name": event_data["name"],
            "description": event_data["description"],
            "start_date_local": "2026-03-04T09:00:00",
        }
        decision = evaluate_sync(event_data, existing)
        assert decision.action == "update"

    def test_force_update_overrides_identical(self):
        event_data = self._make_event_data()
        existing = {
            "id": "evt-123",
            "name": event_data["name"],
            "description": event_data["description"],
            "start_date_local": event_data["start_date_local"],
        }
        decision = evaluate_sync(event_data, existing, force_update=True)
        assert decision.action == "update"
        assert "force_update" in decision.reason

    def test_sync_decision_is_frozen(self):
        decision = SyncDecision(action="create", reason="test")
        with pytest.raises(AttributeError):
            decision.action = "update"
