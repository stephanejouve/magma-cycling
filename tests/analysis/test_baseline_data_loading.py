"""Tests for analysis.baseline.data_loading module.

Tests DataLoadingMixin : load_adherence_data, parse_skipped_replaced_sessions,
_extract_reason, load_cardiovascular_coupling.
"""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from magma_cycling.analysis.baseline.data_loading import DataLoadingMixin


class StubAnalyzer(DataLoadingMixin):
    """Stub providing required attributes for DataLoadingMixin."""

    def __init__(
        self,
        *,
        start_date=date(2026, 1, 27),
        end_date=date(2026, 2, 9),
        adherence_file=None,
        workout_history_dir=None,
        client=None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.adherence_file = adherence_file or Path("/nonexistent")
        self.workout_history_dir = workout_history_dir or Path("/nonexistent")
        self.client = client
        self.adherence_data = []
        self.wellness_data = []
        self.activities_data = []
        self.events_data = []
        self.cv_coupling_values = []
        self.skipped_sessions = []
        self.replaced_sessions = []
        self.cancelled_sessions = []


class TestExtractReason:
    """Tests for _extract_reason()."""

    def test_reason_found(self):
        analyzer = StubAnalyzer()
        result = analyzer._extract_reason("SÉANCE ANNULÉE\nRaison: Fatigue accumulée\n---")
        assert result == "Fatigue accumulée"

    def test_no_reason_pattern(self):
        analyzer = StubAnalyzer()
        result = analyzer._extract_reason("Some description without reason")
        assert result == "Non spécifiée"

    def test_empty_description(self):
        analyzer = StubAnalyzer()
        result = analyzer._extract_reason("")
        assert result == "Non spécifiée"

    def test_reason_with_colon_spacing(self):
        analyzer = StubAnalyzer()
        result = analyzer._extract_reason("Raison: Too late from work")
        assert result == "Too late from work"


class TestLoadAdherenceData:
    """Tests for load_adherence_data()."""

    def test_file_not_found(self):
        analyzer = StubAnalyzer(adherence_file=Path("/nonexistent/file.jsonl"))
        analyzer.load_adherence_data()
        assert analyzer.adherence_data == []

    def test_loads_records_in_date_range(self, tmp_path):
        jsonl = tmp_path / "adherence.jsonl"
        records = [
            {"date": "2026-01-27", "adherence_rate": 0.9, "timestamp": "2026-01-27T10:00:00"},
            {"date": "2026-02-01", "adherence_rate": 0.85, "timestamp": "2026-02-01T10:00:00"},
            {"date": "2026-02-15", "adherence_rate": 0.7, "timestamp": "2026-02-15T10:00:00"},
        ]
        jsonl.write_text("\n".join(json.dumps(r) for r in records))

        analyzer = StubAnalyzer(adherence_file=jsonl)
        analyzer.load_adherence_data()
        # Only first two are in range (Jan 27 - Feb 9)
        assert len(analyzer.adherence_data) == 2

    def test_deduplicates_by_date(self, tmp_path):
        jsonl = tmp_path / "adherence.jsonl"
        records = [
            {"date": "2026-01-27", "adherence_rate": 0.8, "timestamp": "2026-01-27T08:00:00"},
            {"date": "2026-01-27", "adherence_rate": 0.9, "timestamp": "2026-01-27T18:00:00"},
        ]
        jsonl.write_text("\n".join(json.dumps(r) for r in records))

        analyzer = StubAnalyzer(adherence_file=jsonl)
        analyzer.load_adherence_data()
        assert len(analyzer.adherence_data) == 1
        # Should keep the most recent timestamp
        assert analyzer.adherence_data[0]["adherence_rate"] == 0.9

    def test_sorted_by_date(self, tmp_path):
        jsonl = tmp_path / "adherence.jsonl"
        records = [
            {"date": "2026-02-01", "adherence_rate": 0.85, "timestamp": "T1"},
            {"date": "2026-01-27", "adherence_rate": 0.9, "timestamp": "T2"},
        ]
        jsonl.write_text("\n".join(json.dumps(r) for r in records))

        analyzer = StubAnalyzer(adherence_file=jsonl)
        analyzer.load_adherence_data()
        assert analyzer.adherence_data[0]["date"] == "2026-01-27"
        assert analyzer.adherence_data[1]["date"] == "2026-02-01"


class TestParseSkippedReplacedSessions:
    """Tests for parse_skipped_replaced_sessions()."""

    def test_empty_events(self):
        analyzer = StubAnalyzer()
        analyzer.events_data = []
        analyzer.parse_skipped_replaced_sessions()
        assert analyzer.skipped_sessions == []
        assert analyzer.replaced_sessions == []
        assert analyzer.cancelled_sessions == []

    def test_skipped_session_parsed(self):
        analyzer = StubAnalyzer()
        analyzer.events_data = [
            {
                "category": "NOTE",
                "name": "[SAUTÉE] S077-03-INT-Intervals-V001",
                "description": "Raison: Fatigue",
                "start_date_local": "2026-02-05T00:00:00",
            }
        ]
        analyzer.parse_skipped_replaced_sessions()
        assert len(analyzer.skipped_sessions) == 1
        assert analyzer.skipped_sessions[0]["reason"] == "Fatigue"

    def test_replaced_session_parsed(self):
        analyzer = StubAnalyzer()
        analyzer.events_data = [
            {
                "category": "NOTE",
                "name": "[REMPLACÉE] S077-05-END-Endurance-V001",
                "description": "Raison: Changed to recovery",
                "start_date_local": "2026-02-07T00:00:00",
            }
        ]
        analyzer.parse_skipped_replaced_sessions()
        assert len(analyzer.replaced_sessions) == 1

    def test_cancelled_session_parsed(self):
        analyzer = StubAnalyzer()
        analyzer.events_data = [
            {
                "category": "NOTE",
                "name": "[ANNULÉE] S077-06-INT-Sprint-V001",
                "description": "Raison: Illness",
                "start_date_local": "2026-02-08T00:00:00",
            }
        ]
        analyzer.parse_skipped_replaced_sessions()
        assert len(analyzer.cancelled_sessions) == 1

    def test_workout_events_ignored(self):
        analyzer = StubAnalyzer()
        analyzer.events_data = [
            {
                "category": "WORKOUT",
                "name": "S077-01-END-Endurance-V001",
                "description": "Normal workout",
                "start_date_local": "2026-02-03T00:00:00",
            }
        ]
        analyzer.parse_skipped_replaced_sessions()
        assert len(analyzer.skipped_sessions) == 0
        assert len(analyzer.replaced_sessions) == 0
        assert len(analyzer.cancelled_sessions) == 0

    def test_note_without_tag_ignored(self):
        analyzer = StubAnalyzer()
        analyzer.events_data = [
            {
                "category": "NOTE",
                "name": "Regular note",
                "description": "Just a note",
                "start_date_local": "2026-02-04T00:00:00",
            }
        ]
        analyzer.parse_skipped_replaced_sessions()
        assert len(analyzer.skipped_sessions) == 0

    def test_mixed_events(self):
        analyzer = StubAnalyzer()
        analyzer.events_data = [
            {
                "category": "NOTE",
                "name": "[SAUTÉE] S077-01",
                "description": "Raison: Weather",
                "start_date_local": "2026-02-03T00:00:00",
            },
            {
                "category": "NOTE",
                "name": "[ANNULÉE] S077-02",
                "description": "Raison: Sick",
                "start_date_local": "2026-02-04T00:00:00",
            },
            {
                "category": "WORKOUT",
                "name": "S077-03-END",
                "description": "Done",
                "start_date_local": "2026-02-05T00:00:00",
            },
        ]
        analyzer.parse_skipped_replaced_sessions()
        assert len(analyzer.skipped_sessions) == 1
        assert len(analyzer.cancelled_sessions) == 1
        assert len(analyzer.replaced_sessions) == 0


class TestLoadCardiovascularCoupling:
    """Tests for load_cardiovascular_coupling()."""

    def test_dir_not_found(self):
        analyzer = StubAnalyzer(workout_history_dir=Path("/nonexistent"))
        analyzer.load_cardiovascular_coupling()
        assert analyzer.cv_coupling_values == []

    def test_extracts_coupling_values(self, tmp_path):
        week_dir = tmp_path / "S077"
        week_dir.mkdir()
        history_file = week_dir / "workout_history_S077.md"
        history_file.write_text(
            "## Session 1\n"
            "découplage cardiovasculaire faible (3.2 %)\n"
            "## Session 2\n"
            "découplage cardiovasculaire modéré (5.8 %)\n"
        )

        analyzer = StubAnalyzer(workout_history_dir=tmp_path)
        analyzer.load_cardiovascular_coupling()
        assert len(analyzer.cv_coupling_values) == 2
        # Values converted to decimal (3.2% → 0.032)
        assert 0.03 < analyzer.cv_coupling_values[0] < 0.04
        assert 0.05 < analyzer.cv_coupling_values[1] < 0.06

    def test_empty_directory(self, tmp_path):
        analyzer = StubAnalyzer(workout_history_dir=tmp_path)
        analyzer.load_cardiovascular_coupling()
        assert analyzer.cv_coupling_values == []

    def test_no_coupling_in_file(self, tmp_path):
        week_dir = tmp_path / "S077"
        week_dir.mkdir()
        history_file = week_dir / "workout_history_S077.md"
        history_file.write_text("## Session\nJust a normal ride, nothing special\n")

        analyzer = StubAnalyzer(workout_history_dir=tmp_path)
        analyzer.load_cardiovascular_coupling()
        assert analyzer.cv_coupling_values == []


class TestLoadIntervalsData:
    """Tests for load_intervals_data()."""

    def test_loads_all_data(self):
        mock_client = MagicMock()
        mock_client.get_wellness.return_value = [{"id": "2026-01-27", "tsb": 5}]
        mock_client.get_activities.return_value = [{"id": "a1"}]
        mock_client.get_events.return_value = [{"id": "e1"}]

        analyzer = StubAnalyzer(client=mock_client)
        analyzer.load_intervals_data()

        assert len(analyzer.wellness_data) == 1
        assert len(analyzer.activities_data) == 1
        assert len(analyzer.events_data) == 1

    def test_handles_api_errors(self):
        mock_client = MagicMock()
        mock_client.get_wellness.side_effect = Exception("API Error")
        mock_client.get_activities.side_effect = Exception("API Error")
        mock_client.get_events.side_effect = Exception("API Error")

        analyzer = StubAnalyzer(client=mock_client)
        # Should not raise
        analyzer.load_intervals_data()
        assert analyzer.wellness_data == []
