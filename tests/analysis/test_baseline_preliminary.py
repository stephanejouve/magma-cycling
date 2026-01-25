"""Tests for baseline_preliminary module."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cyclisme_training_logs.analysis.baseline_preliminary import BaselineAnalyzer


@pytest.fixture
def mock_adherence_data():
    """Mock adherence JSONL data."""
    return [
        {
            "date": "2026-01-04",
            "planned_workouts": 1,
            "completed_activities": 0,
            "skipped_workouts": [{"id": 123, "name": "Test"}],
            "adherence_rate": 0.0,
            "status": "MISSED",
        },
        {
            "date": "2026-01-05",
            "planned_workouts": 1,
            "completed_activities": 1,
            "skipped_workouts": [],
            "adherence_rate": 1.0,
            "status": "COMPLETE",
        },
        {
            "date": "2026-01-06",
            "planned_workouts": 1,
            "completed_activities": 1,
            "skipped_workouts": [],
            "adherence_rate": 1.0,
            "status": "COMPLETE",
        },
    ]


@pytest.fixture
def mock_wellness_data():
    """Mock Intervals.icu wellness data."""
    return [
        {"id": "2026-01-04", "tsb": 10.0, "ctl": 45.0, "atl": 35.0},
        {"id": "2026-01-05", "tsb": 8.0, "ctl": 45.5, "atl": 37.5},
        {"id": "2026-01-06", "tsb": 5.0, "ctl": 46.0, "atl": 41.0},
    ]


@pytest.fixture
def mock_activities_data():
    """Mock Intervals.icu activities data."""
    return [
        {
            "id": "i123",
            "start_date_local": "2026-01-05",
            "icu_training_load": 50,
            "icu_intensity": 0.75,
        },
        {
            "id": "i124",
            "start_date_local": "2026-01-06",
            "icu_training_load": 60,
            "icu_intensity": 0.80,
        },
    ]


@pytest.fixture
def mock_events_data():
    """Mock Intervals.icu events data."""
    return [
        {"id": "e123", "start_date_local": "2026-01-04", "icu_training_load": 45},
        {"id": "e124", "start_date_local": "2026-01-05", "icu_training_load": 50},
        {"id": "e125", "start_date_local": "2026-01-06", "icu_training_load": 55},
    ]


@pytest.fixture
def analyzer(tmp_path):
    """Create BaselineAnalyzer with temp paths."""
    return BaselineAnalyzer(
        start_date="2026-01-04",
        end_date="2026-01-06",
        adherence_file=tmp_path / "adherence.jsonl",
        workout_history_dir=tmp_path / "workout_history",
        output_dir=tmp_path / "output",
    )


def test_analyzer_initialization(analyzer):
    """Test BaselineAnalyzer initialization."""
    assert analyzer.start_date == date(2026, 1, 4)
    assert analyzer.end_date == date(2026, 1, 6)
    assert analyzer.duration_days == 3
    assert isinstance(analyzer.adherence_file, Path)
    assert isinstance(analyzer.output_dir, Path)


def test_load_adherence_data(analyzer, mock_adherence_data, tmp_path):
    """Test loading adherence data from JSONL."""
    # Create mock JSONL file
    adherence_file = tmp_path / "adherence.jsonl"
    with open(adherence_file, "w") as f:
        for record in mock_adherence_data:
            f.write(json.dumps(record) + "\n")

    analyzer.adherence_file = adherence_file
    analyzer.load_adherence_data()

    assert len(analyzer.adherence_data) == 3
    assert analyzer.adherence_data[0]["date"] == "2026-01-04"
    assert analyzer.adherence_data[-1]["date"] == "2026-01-06"


def test_load_adherence_data_missing_file(analyzer):
    """Test loading adherence data when file doesn't exist."""
    analyzer.load_adherence_data()
    assert len(analyzer.adherence_data) == 0


def test_load_adherence_data_filters_by_date(analyzer, mock_adherence_data, tmp_path):
    """Test that adherence data is filtered by date range."""
    # Add extra record outside range
    extra_data = mock_adherence_data + [
        {
            "date": "2026-01-10",
            "planned_workouts": 1,
            "completed_activities": 1,
            "skipped_workouts": [],
            "adherence_rate": 1.0,
            "status": "COMPLETE",
        }
    ]

    adherence_file = tmp_path / "adherence.jsonl"
    with open(adherence_file, "w") as f:
        for record in extra_data:
            f.write(json.dumps(record) + "\n")

    analyzer.adherence_file = adherence_file
    analyzer.load_adherence_data()

    # Should only load 3 records within range
    assert len(analyzer.adherence_data) == 3


@patch("cyclisme_training_logs.analysis.baseline_preliminary.create_intervals_client")
def test_load_intervals_data(
    mock_client_factory, analyzer, mock_wellness_data, mock_activities_data, mock_events_data
):
    """Test loading Intervals.icu data."""
    mock_client = MagicMock()
    mock_client.get_wellness.return_value = mock_wellness_data
    mock_client.get_activities.return_value = mock_activities_data
    mock_client.get_events.return_value = mock_events_data
    mock_client_factory.return_value = mock_client

    # Re-init analyzer with mocked client
    analyzer.client = mock_client
    analyzer.load_intervals_data()

    assert len(analyzer.wellness_data) == 3
    assert len(analyzer.activities_data) == 2
    assert len(analyzer.events_data) == 3


@patch("cyclisme_training_logs.analysis.baseline_preliminary.create_intervals_client")
def test_load_intervals_data_handles_errors(mock_client_factory, analyzer):
    """Test that errors in API calls are handled gracefully."""
    mock_client = MagicMock()
    mock_client.get_wellness.side_effect = Exception("API Error")
    mock_client.get_activities.side_effect = Exception("API Error")
    mock_client.get_events.side_effect = Exception("API Error")
    mock_client_factory.return_value = mock_client

    analyzer.client = mock_client
    analyzer.load_intervals_data()

    # Should not raise, just log errors
    assert len(analyzer.wellness_data) == 0
    assert len(analyzer.activities_data) == 0
    assert len(analyzer.events_data) == 0


def test_calculate_adherence_metrics(analyzer):
    """Test adherence metrics calculation from Intervals.icu events."""
    # Mock completed workouts (WORKOUT events with paired_activity_id)
    analyzer.events_data = [
        {
            "category": "WORKOUT",
            "paired_activity_id": "i123",
            "start_date_local": "2026-01-05T10:00:00",
        },
        {
            "category": "WORKOUT",
            "paired_activity_id": "i124",
            "start_date_local": "2026-01-06T10:00:00",
        },
        {
            "category": "NOTE",
            "name": "[SAUTÉE] S076-03",
            "description": "Raison: Fatigue",
            "start_date_local": "2026-01-07T00:00:00",
        },
        {
            "category": "NOTE",
            "name": "[REMPLACÉE] S076-05",
            "description": "Raison: Weather",
            "start_date_local": "2026-01-08T00:00:00",
        },
    ]

    # Mock skipped/replaced sessions
    analyzer.skipped_sessions = [
        {
            "date": "2026-01-07",
            "name": "[SAUTÉE] S076-03",
            "description": "Raison: Fatigue",
            "reason": "Fatigue",
        }
    ]
    analyzer.replaced_sessions = [
        {
            "date": "2026-01-08",
            "name": "[REMPLACÉE] S076-05",
            "description": "Raison: Weather",
            "reason": "Weather",
        }
    ]
    analyzer.cancelled_sessions = []

    metrics = analyzer.calculate_adherence_metrics()

    assert (
        metrics["rate"] == 2 / 4
    )  # 2 completed out of 4 total planned (2 completed + 1 skipped + 1 replaced)
    assert metrics["completed"] == 2
    assert metrics["planned"] == 4
    assert metrics["skipped"] == 1
    assert metrics["replaced"] == 1
    assert metrics["cancelled"] == 0
    assert len(metrics["skipped_details"]) == 1
    assert len(metrics["replaced_details"]) == 1
    assert metrics["skipped_details"][0]["date"] == "2026-01-07"
    assert metrics["replaced_details"][0]["date"] == "2026-01-08"


def test_calculate_adherence_metrics_empty_data(analyzer):
    """Test adherence metrics with no data."""
    analyzer.events_data = []
    analyzer.skipped_sessions = []
    analyzer.replaced_sessions = []
    analyzer.cancelled_sessions = []
    metrics = analyzer.calculate_adherence_metrics()

    assert metrics == {}


def test_parse_skipped_replaced_sessions(analyzer):
    """Test parsing of NOTE events with status tags."""
    analyzer.events_data = [
        {
            "category": "NOTE",
            "name": "[SAUTÉE] S076-03-CAD-TechniqueCadence-V001",
            "description": "⏭️ SÉANCE SAUTÉE\nRaison: Too late\n\n--- Description originale ---\nCadence work",
            "start_date_local": "2026-01-14T00:00:00",
        },
        {
            "category": "NOTE",
            "name": "[REMPLACÉE] S077-06-END-EnduranceVolume-V001",
            "description": "🔄 SÉANCE REMPLACÉE\nRaison: Mechanics issues\n\n--- Description originale ---\nEndurance",
            "start_date_local": "2026-01-24T00:00:00",
        },
        {
            "category": "NOTE",
            "name": "[ANNULÉE] S076-01-Test",
            "description": "❌ SÉANCE ANNULÉE\nRaison: Illness\n\n--- Description originale ---\nTest",
            "start_date_local": "2026-01-10T00:00:00",
        },
        {"category": "WORKOUT", "name": "Regular workout", "paired_activity_id": "i123"},
    ]

    analyzer.parse_skipped_replaced_sessions()

    assert len(analyzer.skipped_sessions) == 1
    assert len(analyzer.replaced_sessions) == 1
    assert len(analyzer.cancelled_sessions) == 1

    # Check skipped session details
    assert analyzer.skipped_sessions[0]["date"] == "2026-01-14"
    assert "S076-03" in analyzer.skipped_sessions[0]["name"]
    assert analyzer.skipped_sessions[0]["reason"] == "Too late"

    # Check replaced session details
    assert analyzer.replaced_sessions[0]["date"] == "2026-01-24"
    assert "S077-06" in analyzer.replaced_sessions[0]["name"]
    assert analyzer.replaced_sessions[0]["reason"] == "Mechanics issues"

    # Check cancelled session details
    assert analyzer.cancelled_sessions[0]["date"] == "2026-01-10"
    assert "S076-01" in analyzer.cancelled_sessions[0]["name"]
    assert analyzer.cancelled_sessions[0]["reason"] == "Illness"


def test_extract_reason(analyzer):
    """Test reason extraction from NOTE description."""
    # With reason
    desc1 = "⏭️ SÉANCE SAUTÉE\nRaison: Too late\n\n--- Description ---"
    assert analyzer._extract_reason(desc1) == "Too late"

    # Without reason
    desc2 = "Some description without reason"
    assert analyzer._extract_reason(desc2) == "Non spécifiée"

    # Empty description
    assert analyzer._extract_reason("") == "Non spécifiée"
    assert analyzer._extract_reason(None) == "Non spécifiée"


def test_calculate_tss_metrics(analyzer, mock_events_data, mock_activities_data):
    """Test TSS metrics calculation."""
    analyzer.events_data = mock_events_data
    analyzer.activities_data = mock_activities_data

    metrics = analyzer.calculate_tss_metrics()

    assert metrics["planned_total"] == 150  # 45+50+55
    assert metrics["actual_total"] == 110  # 50+60
    assert metrics["completion_rate"] == pytest.approx(110 / 150)
    assert metrics["avg_daily_planned"] == pytest.approx(150 / 3)
    assert metrics["avg_daily_actual"] == pytest.approx(110 / 3)


def test_calculate_tss_metrics_handles_none_values(analyzer):
    """Test TSS metrics handles None values in TSS."""
    analyzer.events_data = [
        {"id": "e1", "icu_training_load": None},
        {"id": "e2", "icu_training_load": 50},
    ]
    analyzer.activities_data = [
        {"id": "a1", "icu_training_load": None},
        {"id": "a2", "icu_training_load": 60},
    ]

    metrics = analyzer.calculate_tss_metrics()

    assert metrics["planned_total"] == 50
    assert metrics["actual_total"] == 60


def test_analyze_tsb_trajectory(analyzer, mock_wellness_data):
    """Test TSB trajectory analysis."""
    analyzer.wellness_data = mock_wellness_data

    metrics = analyzer.analyze_tsb_trajectory()

    assert metrics["start_tsb"] == 10.0
    assert metrics["end_tsb"] == 5.0
    assert metrics["avg_tsb"] == pytest.approx((10.0 + 8.0 + 5.0) / 3)
    assert metrics["start_ctl"] == 45.0
    assert metrics["end_ctl"] == 46.0
    assert len(metrics["trajectory"]) == 3


def test_analyze_tsb_trajectory_empty_data(analyzer):
    """Test TSB trajectory with no wellness data."""
    analyzer.wellness_data = []

    metrics = analyzer.analyze_tsb_trajectory()

    assert metrics == {}


def test_calculate_cv_coupling_metrics(analyzer):
    """Test cardiovascular coupling metrics."""
    analyzer.cv_coupling_values = [0.02, 0.025, 0.03]  # 2%, 2.5%, 3%

    metrics = analyzer.calculate_cv_coupling_metrics()

    assert metrics["avg"] == pytest.approx(0.025)
    assert metrics["count"] == 3
    assert metrics["quality"] == "EXCELLENT"


def test_calculate_cv_coupling_metrics_quality_grades(analyzer):
    """Test CV coupling quality grading."""
    # Excellent: < 2.5%
    analyzer.cv_coupling_values = [0.02]
    assert analyzer.calculate_cv_coupling_metrics()["quality"] == "EXCELLENT"

    # Good: 2.5-5%
    analyzer.cv_coupling_values = [0.03, 0.04]
    assert analyzer.calculate_cv_coupling_metrics()["quality"] == "GOOD"

    # Acceptable: 5-7.5%
    analyzer.cv_coupling_values = [0.06, 0.07]
    assert analyzer.calculate_cv_coupling_metrics()["quality"] == "ACCEPTABLE"

    # Poor: > 7.5%
    analyzer.cv_coupling_values = [0.08, 0.09]
    assert analyzer.calculate_cv_coupling_metrics()["quality"] == "POOR"


def test_calculate_cv_coupling_metrics_no_data(analyzer):
    """Test CV coupling with no data."""
    analyzer.cv_coupling_values = []

    metrics = analyzer.calculate_cv_coupling_metrics()

    assert metrics["avg"] == 0
    assert metrics["count"] == 0
    assert metrics["quality"] == "NO_DATA"


def test_validate_data_quality(analyzer, mock_adherence_data):
    """Test data quality validation."""
    analyzer.adherence_data = mock_adherence_data
    analyzer.wellness_data = []  # Incomplete
    analyzer.cv_coupling_values = []

    quality = analyzer.validate_data_quality()

    assert "score" in quality
    assert "grade" in quality
    assert "completeness" in quality
    assert "gaps" in quality
    assert "anomalies" in quality
    assert 0 <= quality["score"] <= 100


def test_validate_data_quality_detects_gaps(analyzer, mock_adherence_data):
    """Test that data quality detects missing dates."""
    # Remove middle date
    analyzer.adherence_data = [mock_adherence_data[0], mock_adherence_data[2]]

    quality = analyzer.validate_data_quality()

    assert len(quality["gaps"]) == 1
    assert quality["gaps"][0]["date"] == "2026-01-05"


def test_validate_data_quality_detects_anomalies(analyzer):
    """Test that anomalies are detected."""
    analyzer.adherence_data = [
        {
            "date": "2026-01-04",
            "planned_workouts": 1,
            "completed_activities": 1,
            "adherence_rate": -0.5,  # Anomaly: negative
            "status": "COMPLETE",
        }
    ]

    quality = analyzer.validate_data_quality()

    assert len(quality["anomalies"]) == 1
    assert quality["anomalies"][0]["type"] == "negative_adherence"


def test_validate_data_quality_scoring(analyzer, mock_adherence_data, mock_wellness_data):
    """Test data quality scoring algorithm."""
    # Perfect data
    analyzer.adherence_data = mock_adherence_data
    analyzer.wellness_data = mock_wellness_data
    analyzer.cv_coupling_values = [0.02, 0.03]

    quality = analyzer.validate_data_quality()

    assert quality["score"] >= 90
    assert quality["grade"] == "A"


def test_generate_json_output(analyzer, tmp_path):
    """Test JSON output generation."""
    results = {
        "metadata": {"analysis_date": "2026-01-25", "version": "1.0.0"},
        "adherence": {"rate": 0.85},
    }

    output_file = analyzer.generate_json_output(results)

    assert output_file.exists()
    with open(output_file) as f:
        data = json.load(f)
    assert data["metadata"]["version"] == "1.0.0"
    assert data["adherence"]["rate"] == 0.85


def test_generate_markdown_report(analyzer, tmp_path):
    """Test Markdown report generation."""
    results = {
        "metadata": {
            "analysis_date": "2026-01-25",
            "period_start": "2026-01-04",
            "period_end": "2026-01-06",
            "duration_days": 3,
            "version": "1.0.0",
        },
        "quality": {
            "score": 95,
            "grade": "A",
            "completeness": {"adherence": 1.0, "wellness": 1.0, "activities": 10},
            "gaps": [],
            "anomalies": [],
        },
        "adherence": {
            "rate": 0.85,
            "completed": 17,
            "planned": 20,
            "skipped": 3,
            "skipped_dates": ["2026-01-04", "2026-01-05"],
            "day_patterns": {
                "Monday": {"planned": 3, "completed": 3},
                "Tuesday": {"planned": 3, "completed": 2},
            },
        },
        "tss": {
            "planned_total": 500,
            "actual_total": 450,
            "completion_rate": 0.9,
            "avg_daily_planned": 166.7,
            "avg_daily_actual": 150.0,
        },
        "tsb": {
            "start_tsb": 10.0,
            "end_tsb": 5.0,
            "avg_tsb": 7.5,
            "trajectory": [],
            "start_ctl": 45.0,
            "end_ctl": 46.0,
            "start_atl": 35.0,
            "end_atl": 41.0,
        },
        "cardiovascular_coupling": {"avg": 0.03, "count": 15, "quality": "GOOD"},
    }

    output_file = analyzer.generate_markdown_report(results)

    assert output_file.exists()
    content = output_file.read_text()
    assert "# Rapport Baseline" in content
    assert "85.0%" in content  # Adherence rate
    assert "GOOD" in content  # CV quality
    assert "Séances complétées**: 17/20" in content  # New format with completed/planned


def test_run_analysis_integration(analyzer, mock_adherence_data, tmp_path):
    """Test complete run_analysis integration."""
    # Setup mock data
    adherence_file = tmp_path / "adherence.jsonl"
    with open(adherence_file, "w") as f:
        for record in mock_adherence_data:
            f.write(json.dumps(record) + "\n")

    analyzer.adherence_file = adherence_file

    # Mock Intervals client
    with patch("cyclisme_training_logs.analysis.baseline_preliminary.create_intervals_client"):
        analyzer.client = MagicMock()
        analyzer.client.get_wellness.return_value = []
        analyzer.client.get_activities.return_value = []
        analyzer.client.get_events.return_value = []

        results = analyzer.run_analysis()

    assert "metadata" in results
    assert "quality" in results
    assert "adherence" in results
    assert results["metadata"]["duration_days"] == 3
