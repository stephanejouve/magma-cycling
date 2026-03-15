"""Tests for planning.audit_log module.

Tests PlanningAuditLog : log operations, query, statistics avec mock config.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.planning.audit_log import (
    AuditEntry,
    OperationStatus,
    OperationType,
    PlanningAuditLog,
)


@pytest.fixture
def audit_log(tmp_path):
    """Create PlanningAuditLog with mocked config pointing to tmp_path."""
    mock_config = MagicMock()
    mock_config.week_planning_dir = tmp_path
    with patch("magma_cycling.planning.audit_log.get_data_config", return_value=mock_config):
        log = PlanningAuditLog()
    return log


class TestAuditEntry:
    """Tests for AuditEntry model."""

    def test_create_entry(self):
        entry = AuditEntry(
            timestamp="2026-03-01T10:00:00",
            operation=OperationType.MODIFY,
            week_id="S081",
            status=OperationStatus.SUCCESS,
            requested_by="athlete",
            tool="shift-sessions",
            reason="Test",
            description="Test operation",
        )
        assert entry.week_id == "S081"
        assert entry.operation == OperationType.MODIFY

    def test_entry_defaults(self):
        entry = AuditEntry(
            timestamp="2026-03-01T10:00:00",
            operation=OperationType.READ,
            week_id="S082",
            status=OperationStatus.SUCCESS,
            requested_by="test",
            tool="test-tool",
            reason="Test",
            description="Test",
        )
        assert entry.files_modified == []
        assert entry.backup_created is False
        assert entry.error_message is None
        assert entry.metadata == {}


class TestLogOperation:
    """Tests for log_operation()."""

    def test_log_success(self, audit_log, tmp_path):
        entry = audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S081",
            status=OperationStatus.SUCCESS,
            tool="shift-sessions",
            description="Shifted sessions",
            reason="User skipped Thursday",
            requested_by="athlete",
        )
        assert entry.status == OperationStatus.SUCCESS
        assert entry.week_id == "S081"

        # Verify written to file
        log_content = (tmp_path / ".planning_audit.jsonl").read_text()
        assert "S081" in log_content

    def test_log_with_backup_path(self, audit_log):
        entry = audit_log.log_operation(
            operation=OperationType.BACKUP,
            week_id="S081",
            status=OperationStatus.SUCCESS,
            tool="backup-system",
            description="Auto backup",
            backup_path=Path("/backups/test.json"),
        )
        assert entry.backup_created is True
        assert entry.backup_path == "/backups/test.json"

    def test_log_with_error(self, audit_log):
        entry = audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S081",
            status=OperationStatus.FAILED,
            tool="test-tool",
            description="Failed operation",
            error=ValueError("Something went wrong"),
        )
        assert entry.error_message == "Something went wrong"
        assert entry.status == OperationStatus.FAILED

    def test_log_auto_detects_user(self, audit_log):
        entry = audit_log.log_operation(
            operation=OperationType.READ,
            week_id="S081",
            status=OperationStatus.SUCCESS,
            tool="test-tool",
            description="Read operation",
        )
        # requested_by should be auto-detected from USER env var
        assert entry.requested_by is not None

    def test_log_with_files_modified(self, audit_log):
        entry = audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S081",
            status=OperationStatus.SUCCESS,
            tool="test-tool",
            description="Multi-file modification",
            files_modified=["file1.json", "file2.txt"],
        )
        assert entry.files_modified == ["file1.json", "file2.txt"]

    def test_log_with_metadata(self, audit_log):
        entry = audit_log.log_operation(
            operation=OperationType.CREATE,
            week_id="S082",
            status=OperationStatus.SUCCESS,
            tool="planner",
            description="Created week plan",
            metadata={"sessions_count": 7},
        )
        assert entry.metadata == {"sessions_count": 7}


class TestGetRecentOperations:
    """Tests for get_recent_operations()."""

    def test_get_recent_empty_log(self, audit_log):
        result = audit_log.get_recent_operations()
        assert result == []

    def test_get_recent_with_entries(self, audit_log):
        for i in range(5):
            audit_log.log_operation(
                operation=OperationType.MODIFY,
                week_id=f"S08{i}",
                status=OperationStatus.SUCCESS,
                tool="test",
                description=f"Op {i}",
            )
        result = audit_log.get_recent_operations(count=3)
        assert len(result) == 3
        # Newest first
        assert result[0].week_id == "S084"

    def test_filter_by_week_id(self, audit_log):
        audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S081",
            status=OperationStatus.SUCCESS,
            tool="test",
            description="Op 1",
        )
        audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S082",
            status=OperationStatus.SUCCESS,
            tool="test",
            description="Op 2",
        )

        result = audit_log.get_recent_operations(week_id="S081")
        assert len(result) == 1
        assert result[0].week_id == "S081"

    def test_handles_malformed_lines(self, audit_log, tmp_path):
        log_file = tmp_path / ".planning_audit.jsonl"
        log_file.write_text("not json\n{invalid}\n")

        result = audit_log.get_recent_operations()
        assert result == []


class TestGetOperationsForWeek:
    """Tests for get_operations_for_week()."""

    def test_returns_all_for_week(self, audit_log):
        for _ in range(3):
            audit_log.log_operation(
                operation=OperationType.MODIFY,
                week_id="S081",
                status=OperationStatus.SUCCESS,
                tool="test",
                description="Op",
            )
        audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S082",
            status=OperationStatus.SUCCESS,
            tool="test",
            description="Other",
        )

        result = audit_log.get_operations_for_week("S081")
        assert len(result) == 3


class TestGetStatistics:
    """Tests for get_statistics()."""

    def test_empty_statistics(self, audit_log):
        stats = audit_log.get_statistics()
        assert stats["total_operations"] == 0
        assert stats["success_count"] == 0

    def test_statistics_with_entries(self, audit_log):
        audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S081",
            status=OperationStatus.SUCCESS,
            tool="tool-a",
            description="Op 1",
        )
        audit_log.log_operation(
            operation=OperationType.READ,
            week_id="S081",
            status=OperationStatus.SUCCESS,
            tool="tool-b",
            description="Op 2",
        )
        audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S081",
            status=OperationStatus.FAILED,
            tool="tool-a",
            description="Op 3",
            error=ValueError("Failed"),
        )

        stats = audit_log.get_statistics()
        assert stats["total_operations"] == 3
        assert stats["success_count"] == 2
        assert stats["failed_count"] == 1
        assert stats["by_operation"]["modify"] == 2
        assert stats["by_operation"]["read"] == 1
        assert stats["by_tool"]["tool-a"] == 2

    def test_statistics_filtered_by_week(self, audit_log):
        audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S081",
            status=OperationStatus.SUCCESS,
            tool="test",
            description="Op",
        )
        audit_log.log_operation(
            operation=OperationType.MODIFY,
            week_id="S082",
            status=OperationStatus.SUCCESS,
            tool="test",
            description="Op",
        )

        stats = audit_log.get_statistics(week_id="S081")
        assert stats["total_operations"] == 1
