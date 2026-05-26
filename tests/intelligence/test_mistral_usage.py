"""Tests for ``magma_cycling.intelligence.mistral_usage`` (PR3 iso-config AC3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from magma_cycling.intelligence import mistral_usage
from magma_cycling.intelligence.mistral_usage import (
    MAX_CALLS_PER_RUN,
    MistralUsageLogger,
    reset_logger,
)


class TestMistralUsageLogger:
    def test_log_call_writes_one_line(self, tmp_path: Path) -> None:
        usage_logger = MistralUsageLogger(workflow_id="eow-test", data_dir=tmp_path)
        usage_logger.log_call(n_tokens=1234, status="ok")

        log_files = list((tmp_path / "intelligence").glob("mistral_usage_*.log"))
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert content.count("\n") == 1
        # Tab-separated columns: ts, workflow_id, n_tokens, status
        ts, wf_id, n_tokens, status = content.strip().split("\t")
        assert wf_id == "eow-test"
        assert n_tokens == "1234"
        assert status == "ok"
        assert ts  # iso timestamp present

    def test_log_call_handles_missing_tokens(self, tmp_path: Path) -> None:
        usage_logger = MistralUsageLogger(workflow_id="eow-test", data_dir=tmp_path)
        usage_logger.log_call(n_tokens=None, status="error")

        log_files = list((tmp_path / "intelligence").glob("mistral_usage_*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        _, _, n_tokens, status = content.strip().split("\t")
        assert n_tokens == "?"
        assert status == "error"

    def test_log_call_increments_counter(self, tmp_path: Path) -> None:
        usage_logger = MistralUsageLogger(workflow_id="eow-test", data_dir=tmp_path)
        for _ in range(3):
            usage_logger.log_call(n_tokens=10)
        assert usage_logger.calls_this_run == 3

    def test_threshold_alert_triggered_once(self, tmp_path: Path) -> None:
        usage_logger = MistralUsageLogger(workflow_id="eow-test", data_dir=tmp_path)
        with patch.object(usage_logger, "_alert_runaway") as mock_alert:
            for _ in range(MAX_CALLS_PER_RUN + 3):
                usage_logger.log_call(n_tokens=10)
            # Threshold = > MAX_CALLS_PER_RUN, so alert fires once at call 51
            assert mock_alert.call_count == 1
            assert usage_logger.alerted is True
            assert usage_logger.calls_this_run == MAX_CALLS_PER_RUN + 3

    def test_threshold_alert_below_limit_no_alert(self, tmp_path: Path) -> None:
        usage_logger = MistralUsageLogger(workflow_id="eow-test", data_dir=tmp_path)
        with patch.object(usage_logger, "_alert_runaway") as mock_alert:
            for _ in range(MAX_CALLS_PER_RUN):
                usage_logger.log_call(n_tokens=10)
            mock_alert.assert_not_called()
            assert usage_logger.alerted is False

    def test_log_dir_created_lazily(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "data"
        # Parent of intelligence/ does not exist yet.
        MistralUsageLogger(data_dir=nested)
        assert (nested / "intelligence").is_dir()


class TestModuleSingleton:
    def test_reset_logger_replaces_instance(self, tmp_path: Path) -> None:
        a = reset_logger(workflow_id="run-a", data_dir=tmp_path)
        b = reset_logger(workflow_id="run-b", data_dir=tmp_path)
        assert a is not b
        assert mistral_usage.get_logger().workflow_id == "run-b"

    @pytest.fixture(autouse=True)
    def _reset_singleton(self) -> None:
        mistral_usage._logger = None
        yield
        mistral_usage._logger = None
