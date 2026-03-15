"""Tests for LoggingMixin."""

import json
from datetime import date
from pathlib import Path

from magma_cycling.intelligence.training_intelligence import TrainingIntelligence
from magma_cycling.workflows.pid_eval.evaluation_logging import LoggingMixin


class StubLogging(LoggingMixin):
    """Stub class to test LoggingMixin."""

    def __init__(self, evaluation_log, intelligence_file, dry_run=False):
        """Initialize stub with paths."""
        self.evaluation_log = Path(evaluation_log)
        self.intelligence_file = Path(intelligence_file)
        self.intelligence = TrainingIntelligence()
        self.dry_run = dry_run


class TestLogEvaluation:
    """Tests for log_evaluation."""

    def test_writes_jsonl_entry(self, tmp_path):
        """Log entry written as JSONL."""
        log_file = tmp_path / "pid_evaluation.jsonl"
        stub = StubLogging(log_file, tmp_path / "intel.json")
        metrics = {"adherence_rate": 0.9, "tss_completion_rate": 0.85}
        stub.log_evaluation(date(2026, 1, 1), date(2026, 1, 7), metrics)
        assert log_file.exists()
        entry = json.loads(log_file.read_text().strip())
        assert entry["metrics"]["adherence_rate"] == 0.9
        assert entry["pid_correction"] is None

    def test_dry_run_no_write(self, tmp_path):
        """Dry run does not write to file."""
        log_file = tmp_path / "pid_evaluation.jsonl"
        stub = StubLogging(log_file, tmp_path / "intel.json", dry_run=True)
        stub.log_evaluation(date(2026, 1, 1), date(2026, 1, 7), {})
        assert not log_file.exists()

    def test_pid_result_included(self, tmp_path):
        """PID result included when provided."""
        log_file = tmp_path / "pid_evaluation.jsonl"
        stub = StubLogging(log_file, tmp_path / "intel.json")
        pid_result = {"error": -5.0, "tss_per_week_adjusted": 320}
        stub.log_evaluation(date(2026, 1, 1), date(2026, 1, 7), {}, pid_result=pid_result)
        entry = json.loads(log_file.read_text().strip())
        assert entry["pid_correction"]["error"] == -5.0


class TestSaveIntelligence:
    """Tests for save_intelligence."""

    def test_saves_to_file(self, tmp_path):
        """Intelligence saved to file path."""
        intel_file = tmp_path / "intelligence.json"
        stub = StubLogging(tmp_path / "log.jsonl", intel_file)
        stub.save_intelligence()
        assert intel_file.exists()

    def test_dry_run_no_save(self, tmp_path):
        """Dry run does not save intelligence."""
        intel_file = tmp_path / "intelligence.json"
        stub = StubLogging(tmp_path / "log.jsonl", intel_file, dry_run=True)
        stub.save_intelligence()
        assert not intel_file.exists()
