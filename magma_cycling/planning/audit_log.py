#!/usr/bin/env python3
"""
Planning Audit Log - Complete operation tracking for planning files.

Journal d'audit complet pour toutes les opérations sur les fichiers de planification.
Enregistre:
- Qui a fait quoi
- Quand
- Backup associé
- Résultat (succès/échec)

Author: Claude Sonnet 4.5
Created: 2026-02-20
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from magma_cycling.config import get_data_config


class OperationType(str, Enum):
    """Types of operations on planning files."""

    READ = "read"
    MODIFY = "modify"
    CREATE = "create"
    DELETE = "delete"
    BACKUP = "backup"
    RESTORE = "restore"
    SNAPSHOT = "snapshot"


class OperationStatus(str, Enum):
    """Status of an operation."""

    SUCCESS = "success"
    FAILED = "failed"
    ABORTED = "aborted"


class AuditEntry(BaseModel):
    """Single entry in the audit log."""

    timestamp: str = Field(description="ISO timestamp of operation")
    operation: OperationType = Field(description="Type of operation")
    week_id: str = Field(description="Week identifier (e.g., S081)")
    status: OperationStatus = Field(description="Operation result")

    # WHO requested this?
    requested_by: str = Field(description="User/script that initiated operation")
    tool: str = Field(description="Tool/script that performed operation")

    # WHY?
    reason: str = Field(description="Reason for modification")
    description: str = Field(description="Human-readable description of change")

    # WHAT files?
    files_modified: list[str] = Field(default_factory=list, description="List of files modified")

    # WHEN was file timestamp set?
    file_timestamp: str | None = Field(
        default=None, description="Timestamp set in modified planning file"
    )

    # Backup tracking
    backup_created: bool = Field(default=False, description="Was backup created?")
    backup_path: str | None = Field(default=None, description="Path to backup file")

    # Error tracking
    error_message: str | None = Field(default=None, description="Error if failed")

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class PlanningAuditLog:
    """
    Centralized audit log for all planning operations.

    Maintains a JSON-lines log file with all operations.
    """

    def __init__(self):
        """Initialize audit log."""
        data_config = get_data_config()
        planning_dir = data_config.week_planning_dir

        self.log_file = planning_dir / ".planning_audit.jsonl"

        # Ensure log file exists
        if not self.log_file.exists():
            self.log_file.touch()

    def log_operation(
        self,
        operation: OperationType,
        week_id: str,
        status: OperationStatus,
        tool: str,
        description: str,
        reason: str = "User requested",
        requested_by: str | None = None,
        files_modified: list[str] | None = None,
        file_timestamp: str | None = None,
        backup_path: Path | None = None,
        error: Exception | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """
        Log an operation to the audit file.

        Args:
            operation: Type of operation
            week_id: Week identifier
            status: Success/failed/aborted
            tool: Name of tool performing operation
            description: Human-readable description of change
            reason: Why this modification was made
            requested_by: Who initiated this operation (user/script)
            files_modified: List of files that were modified
            file_timestamp: Timestamp set in modified planning file
            backup_path: Path to backup if created
            error: Exception if operation failed
            metadata: Additional context

        Returns:
            Created audit entry

        Example:
            >>> log = PlanningAuditLog()
            >>> log.log_operation(
            ...     OperationType.MODIFY,
            ...     "S081",
            ...     OperationStatus.SUCCESS,
            ...     "shift-sessions",
            ...     "Shifted Thu→Fri sessions",
            ...     reason="User skipped Thursday training",
            ...     requested_by="athlete",
            ...     files_modified=["week_planning_S081.json"],
            ...     file_timestamp="2026-02-20T23:30:00Z",
            ...     backup_path=Path("backups/week_planning_S081_20260220_233000.json")
            ... )
        """
        import os

        # Auto-detect requested_by if not provided
        if requested_by is None:
            requested_by = os.getenv("USER", "unknown")

        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            week_id=week_id,
            status=status,
            tool=tool,
            requested_by=requested_by,
            reason=reason,
            description=description,
            files_modified=files_modified or [],
            file_timestamp=file_timestamp,
            backup_created=backup_path is not None,
            backup_path=str(backup_path) if backup_path else None,
            error_message=str(error) if error else None,
            metadata=metadata or {},
        )

        # Append to log file (JSON Lines format)
        with self.log_file.open("a") as f:
            f.write(entry.model_dump_json() + "\n")

        return entry

    def get_recent_operations(
        self, count: int = 20, week_id: str | None = None
    ) -> list[AuditEntry]:
        """
        Get recent operations from audit log.

        Args:
            count: Number of entries to return
            week_id: Optional filter by week

        Returns:
            List of audit entries (newest first)

        Example:
            >>> log = PlanningAuditLog()
            >>> recent = log.get_recent_operations(10, week_id="S081")
        """
        entries = []

        if not self.log_file.exists():
            return []

        # Read log file in reverse (newest first)
        with self.log_file.open("r") as f:
            lines = f.readlines()

        for line in reversed(lines):
            if not line.strip():
                continue

            try:
                data = json.loads(line)
                entry = AuditEntry(**data)

                # Filter by week_id if specified
                if week_id and entry.week_id != week_id:
                    continue

                entries.append(entry)

                if len(entries) >= count:
                    break

            except (json.JSONDecodeError, ValueError):
                # Skip malformed lines
                continue

        return entries

    def get_operations_for_week(self, week_id: str) -> list[AuditEntry]:
        """
        Get all operations for a specific week.

        Args:
            week_id: Week identifier

        Returns:
            List of audit entries for this week

        Example:
            >>> log = PlanningAuditLog()
            >>> ops = log.get_operations_for_week("S081")
            >>> print(f"Total operations: {len(ops)}")
        """
        return self.get_recent_operations(count=1000, week_id=week_id)

    def print_recent_log(self, count: int = 10, week_id: str | None = None):
        """
        Print recent operations in human-readable format.

        Args:
            count: Number of entries to show
            week_id: Optional filter by week

        Example:
            >>> log = PlanningAuditLog()
            >>> log.print_recent_log(5, week_id="S081")
        """
        entries = self.get_recent_operations(count, week_id)

        if not entries:
            print("📋 Aucune opération dans le journal")
            return

        title = f"📋 Journal d'Audit - {count} dernières opérations"
        if week_id:
            title += f" ({week_id})"

        print("=" * 70)
        print(title)
        print("=" * 70)

        for entry in entries:
            # Format timestamp
            ts = datetime.fromisoformat(entry.timestamp)
            time_str = ts.strftime("%Y-%m-%d %H:%M:%S")

            # Status emoji
            status_emoji = "✅" if entry.status == OperationStatus.SUCCESS else "❌"

            # Backup indicator
            backup_indicator = "🔒" if entry.backup_created else "  "

            print(f"\n{status_emoji} {backup_indicator} {time_str}")
            print(f"   {entry.operation.value.upper()}: {entry.description}")
            print(f"   Tool: {entry.tool} | Week: {entry.week_id}")

            if entry.backup_path:
                backup_name = Path(entry.backup_path).name
                print(f"   Backup: {backup_name}")

            if entry.error_message:
                print(f"   Error: {entry.error_message}")

        print("=" * 70)

    def get_statistics(self, week_id: str | None = None) -> dict[str, Any]:
        """
        Get statistics about operations.

        Args:
            week_id: Optional filter by week

        Returns:
            Dict with operation statistics

        Example:
            >>> log = PlanningAuditLog()
            >>> stats = log.get_statistics("S081")
            >>> print(f"Total: {stats['total_operations']}")
        """
        entries = self.get_recent_operations(count=1000, week_id=week_id)

        if not entries:
            return {
                "total_operations": 0,
                "success_count": 0,
                "failed_count": 0,
                "backup_count": 0,
            }

        success_count = sum(1 for e in entries if e.status == OperationStatus.SUCCESS)
        failed_count = sum(1 for e in entries if e.status == OperationStatus.FAILED)
        backup_count = sum(1 for e in entries if e.backup_created)

        # Count by operation type
        by_operation = {}
        for entry in entries:
            op = entry.operation.value
            by_operation[op] = by_operation.get(op, 0) + 1

        # Count by tool
        by_tool = {}
        for entry in entries:
            tool = entry.tool
            by_tool[tool] = by_tool.get(tool, 0) + 1

        return {
            "total_operations": len(entries),
            "success_count": success_count,
            "failed_count": failed_count,
            "backup_count": backup_count,
            "by_operation": by_operation,
            "by_tool": by_tool,
            "first_operation": entries[-1].timestamp if entries else None,
            "last_operation": entries[0].timestamp if entries else None,
        }


# Global instance (singleton)
audit_log = PlanningAuditLog()
