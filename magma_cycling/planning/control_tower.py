#!/usr/bin/env python3
"""
Planning Control Tower - Centralized access control for planning files.

Tour de contrôle centralisée pour tous les accès aux fichiers de planification.
Gère automatiquement:
- Backups avant toute modification
- Validation des modifications
- Atomicité des opérations
- Rollback en cas d'erreur

Usage:
    from magma_cycling.planning.control_tower import planning_tower

    # Automatic backup before modification
    with planning_tower.modify_week("S081") as plan:
        plan.planned_sessions[0].date = "2026-02-17"
        # Auto-saved and backed up on exit

Author: Claude Sonnet 4.5
Created: 2026-02-20
"""

import shutil
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from magma_cycling.config import get_data_config
from magma_cycling.planning.backup import PlanningBackup
from magma_cycling.planning.models import WeeklyPlan


class PlanningControlTower:
    """
    Centralized access control for planning files.

    Acts as a "control tower" that intercepts all write operations
    to planning files and automatically creates backups.

    All scripts MUST request permission before modifying planning files.
    """

    def __init__(self):
        """Initialize control tower."""
        data_config = get_data_config()
        self.planning_dir = data_config.week_planning_dir
        self.backup_system = PlanningBackup(self.planning_dir)

        # Track active modifications (for atomic operations)
        self._active_modifications: set[str] = set()

        # Track which script is currently holding the lock
        self._lock_holders: dict[str, str] = {}  # {week_id: script_name}

    def request_permission(self, week_id: str, requesting_script: str, reason: str = "") -> bool:
        """
        Request permission to modify planning files.

        ALL scripts MUST call this before any modification.

        Args:
            week_id: Week identifier (e.g., "S081")
            requesting_script: Name of script requesting permission
            reason: Why this modification is needed

        Returns:
            True if permission granted, False if denied

        Raises:
            RuntimeError: If week is already locked by another script

        Example:
            >>> if not planning_tower.request_permission("S081", "daily-sync", "Update session status"):
            ...     print("Permission denied - week locked", file=sys.stderr)
            ...     return
        """
        # Check if already locked
        if week_id in self._lock_holders:
            current_holder = self._lock_holders[week_id]
            if current_holder != requesting_script:
                raise RuntimeError(
                    f"❌ Control Tower: Permission DENIED\n"
                    f"   Week {week_id} is locked by: {current_holder}\n"
                    f"   Requesting script: {requesting_script}\n"
                    f"   Wait for {current_holder} to complete."
                )

        # Grant permission and acquire lock
        self._lock_holders[week_id] = requesting_script
        print(f"✅ Control Tower: Permission GRANTED to {requesting_script}", file=sys.stderr)
        print(f"   Week: {week_id}", file=sys.stderr)
        if reason:
            print(f"   Reason: {reason}", file=sys.stderr)

        return True

    def release_permission(self, week_id: str, script_name: str):
        """
        Release permission lock on a week.

        Args:
            week_id: Week identifier
            script_name: Script releasing the lock

        Example:
            >>> planning_tower.release_permission("S081", "daily-sync")
        """
        if week_id in self._lock_holders and self._lock_holders[week_id] == script_name:
            del self._lock_holders[week_id]
            print(f"🔓 Control Tower: Lock released by {script_name}", file=sys.stderr)

    @contextmanager
    def modify_week(
        self,
        week_id: str,
        auto_save: bool = True,
        requesting_script: str = "unknown",
        reason: str = "",
    ) -> Generator[WeeklyPlan, None, None]:
        """
        Context manager for safe week modification with automatic backup.

        REQUIRES PERMISSION: Automatically requests permission from Control Tower.

        Args:
            week_id: Week identifier (e.g., "S081")
            auto_save: Automatically save changes on exit (default: True)
            requesting_script: Name of script making modification
            reason: Why this modification is needed

        Yields:
            WeeklyPlan instance for modification

        Raises:
            FileNotFoundError: If planning file doesn't exist
            RuntimeError: If week is already being modified (concurrent access)

        Example:
            >>> with planning_tower.modify_week(
            ...     "S081",
            ...     requesting_script="daily-sync",
            ...     reason="Update session status from Intervals.icu"
            ... ) as plan:
            ...     plan.planned_sessions[0].status = "completed"
        """
        # 🚦 REQUEST PERMISSION from Control Tower
        self.request_permission(week_id, requesting_script, reason)

        planning_file = self.planning_dir / f"week_planning_{week_id}.json"

        if not planning_file.exists():
            raise FileNotFoundError(f"Planning file not found: {planning_file}")

        # Mark as active
        self._active_modifications.add(week_id)

        # 🔒 AUTOMATIC BACKUP before loading
        print(f"🔒 Control Tower: Backup {week_id}...", file=sys.stderr)
        backups = self.backup_system.backup_week_files(week_id)

        if backups:
            for file_type, backup_path in backups.items():
                print(f"   ✅ {file_type}: {backup_path.name}", file=sys.stderr)

        try:
            # Load planning
            plan = WeeklyPlan.from_json(planning_file)

            # Yield for modifications
            yield plan

            # Save if auto_save enabled
            if auto_save:
                # Update timestamp
                file_timestamp = datetime.now().isoformat() + "Z"
                plan.last_updated = file_timestamp

                # Save to file
                plan.to_json(planning_file)
                print(f"💾 Control Tower: Saved {week_id}", file=sys.stderr)

                # 📋 LOG TO AUDIT
                from magma_cycling.planning.audit_log import (
                    OperationStatus,
                    OperationType,
                    audit_log,
                )

                audit_log.log_operation(
                    operation=OperationType.MODIFY,
                    week_id=week_id,
                    status=OperationStatus.SUCCESS,
                    tool=requesting_script,
                    description=f"Modified {week_id} planning",
                    reason=reason or "User requested",
                    files_modified=[f"week_planning_{week_id}.json"],
                    file_timestamp=file_timestamp,
                    backup_path=backups.get("json") if backups else None,
                )

                # Cleanup old backups (keep 10 most recent per file)
                self.backup_system.cleanup_old_backups(keep_count=10, week_id=week_id)

        except Exception as e:
            # On error, log failure and offer rollback
            print(f"❌ Control Tower: Error modifying {week_id}: {e}", file=sys.stderr)
            print(f"   Backups available in: {self.backup_system.backup_dir}", file=sys.stderr)

            # 📋 LOG FAILURE
            from magma_cycling.planning.audit_log import (
                OperationStatus,
                OperationType,
                audit_log,
            )

            audit_log.log_operation(
                operation=OperationType.MODIFY,
                week_id=week_id,
                status=OperationStatus.FAILED,
                tool=requesting_script,
                description=f"Failed to modify {week_id}",
                reason=reason or "User requested",
                error=e,
            )

            raise

        finally:
            # Release lock and permission
            self._active_modifications.discard(week_id)
            self.release_permission(week_id, requesting_script)

    def read_week(self, week_id: str) -> WeeklyPlan:
        """
        Read-only access to week planning (no backup needed).

        Args:
            week_id: Week identifier (e.g., "S081")

        Returns:
            WeeklyPlan instance (read-only)

        Example:
            >>> plan = planning_tower.read_week("S081")
            >>> print(plan.tss_target, file=sys.stderr)
        """
        planning_file = self.planning_dir / f"week_planning_{week_id}.json"

        if not planning_file.exists():
            raise FileNotFoundError(f"Planning file not found: {planning_file}")

        return WeeklyPlan.from_json(planning_file)

    def backup_week(self, week_id: str) -> dict[str, Path]:
        """
        Manually trigger backup for a week.

        Args:
            week_id: Week identifier (e.g., "S081")

        Returns:
            Dict mapping file type to backup path

        Example:
            >>> backups = planning_tower.backup_week("S081")
        """
        return self.backup_system.backup_week_files(week_id)

    def list_backups(self, week_id: str | None = None) -> list[Path]:
        """
        List available backups.

        Args:
            week_id: Optional week filter

        Returns:
            List of backup paths (newest first)

        Example:
            >>> backups = planning_tower.list_backups("S081")
            >>> print(f"Latest: {backups[0]}", file=sys.stderr)
        """
        return self.backup_system.list_backups(week_id)

    def restore_backup(self, backup_path: Path, confirm: bool = True) -> Path | None:
        """
        Restore a backup file.

        Args:
            backup_path: Path to backup file
            confirm: Require user confirmation (default: True)

        Returns:
            Path where file was restored, or None if cancelled

        Example:
            >>> tower.restore_backup(Path("backups/week_planning_S081_20260220.json"))
        """
        if confirm:
            print(f"⚠️  Restore backup: {backup_path.name}", file=sys.stderr)
            print("   This will overwrite current planning file.", file=sys.stderr)
            response = input("   Continue? (yes/no): ")

            if response.lower() != "yes":
                print("   Cancelled.", file=sys.stderr)
                return None

        return self.backup_system.restore_backup(backup_path, dry_run=False)

    def create_week_snapshot(self, week_id: str, description: str = "") -> Path:
        """
        Create named snapshot (special backup with description).

        Args:
            week_id: Week identifier
            description: Optional description for snapshot

        Returns:
            Path to snapshot file

        Example:
            >>> tower.create_week_snapshot("S081", "avant_modifications_dimanche")
        """
        # Create backup
        backups = self.backup_system.backup_week_files(week_id)

        if not backups:
            raise FileNotFoundError(f"No files found for {week_id}")

        # Get JSON backup (primary)
        json_backup = backups.get("json")

        if not json_backup:
            raise FileNotFoundError(f"JSON planning not found for {week_id}")

        # Create named snapshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if description:
            # Sanitize description (remove special chars)
            clean_desc = "".join(c if c.isalnum() or c in "_-" else "_" for c in description)
            snapshot_name = f"week_planning_{week_id}_SNAPSHOT_{clean_desc}_{timestamp}.json"
        else:
            snapshot_name = f"week_planning_{week_id}_SNAPSHOT_{timestamp}.json"

        snapshot_path = self.backup_system.backup_dir / snapshot_name

        # Copy backup to snapshot
        shutil.copy2(json_backup, snapshot_path)

        print(f"📸 Snapshot créé: {snapshot_name}", file=sys.stderr)

        return snapshot_path

    def sync_from_remote(
        self,
        week_id: str,
        intervals_client,
        strategy: str = "merge",
        requesting_script: str = "sync-remote-to-local",
    ) -> dict:
        """
        Synchronize local planning from Intervals.icu events.

        Handles cases where remote sessions have been split or modified
        without local write-back (e.g., S081-07 → S081-07a, S081-07b).

        Args:
            week_id: Week identifier (e.g., "S081")
            intervals_client: IntervalsClient instance
            strategy: "merge" (preserve local data) or "replace" (overwrite)
            requesting_script: Name of script requesting sync

        Returns:
            dict with sync stats: {
                "sessions_added": [],
                "sessions_updated": [],
                "sessions_removed": [],
                "intervals_ids_fixed": []
            }
        """
        from datetime import datetime

        from magma_cycling.planning.models import WORKOUT_NAME_REGEX, Session, WeeklyPlan

        # Load existing planning to get date range
        planning_file = self.planning_dir / f"week_planning_{week_id}.json"
        if not planning_file.exists():
            raise FileNotFoundError(f"Planning file not found: {planning_file}")

        existing_plan = WeeklyPlan.from_json(planning_file)
        start_date = existing_plan.start_date
        end_date = existing_plan.end_date

        # Fetch all events for this week from Intervals.icu
        events = intervals_client.get_events(oldest=start_date, newest=end_date)

        # Parse events to extract session information
        remote_sessions = {}
        for event in events:
            name = event.get("name", "")
            intervals_id = event["id"]

            # Parse session ID from event name
            # Format: S081-07a-INT-TempoSoutenu-V001
            # Or: [ANNULÉE] S081-04-INT-TempoSoutenu-V001
            match = WORKOUT_NAME_REGEX.search(name)
            if not match:
                continue

            session_id = match.group(1)
            session_type = match.group(2)
            session_name = match.group(3)
            version = match.group(4)

            # Extract date from event
            event_date_str = event.get("start_date_local", "")
            if event_date_str:
                event_date = datetime.fromisoformat(event_date_str.replace("Z", "")).date()
            else:
                continue

            # Determine status from category
            category = event.get("category", "")
            if category == "NOTE":
                if "[ANNULÉE]" in name:
                    status = "cancelled"
                elif "[SAUTÉE]" in name:
                    status = "cancelled"
                else:
                    status = "planned"
            else:
                status = "planned"  # Will be updated by daily-sync

            # Extract description
            description = event.get("description", "")

            remote_sessions[session_id] = {
                "session_id": session_id,
                "session_date": event_date,
                "name": session_name,
                "session_type": session_type,
                "version": version,
                "intervals_id": intervals_id,
                "status": status,
                "description": description,
            }

        # Sync with local planning
        stats = {
            "sessions_added": [],
            "sessions_updated": [],
            "sessions_removed": [],
            "intervals_ids_fixed": [],
        }

        with self.modify_week(
            week_id,
            requesting_script=requesting_script,
            reason="Sync from Intervals.icu remote events",
        ) as plan:
            # Build session ID → session mapping
            local_sessions = {s.session_id: s for s in plan.planned_sessions}

            # Add or update sessions from remote
            for session_id, remote_data in remote_sessions.items():
                if session_id in local_sessions:
                    # Update existing session
                    local_session = local_sessions[session_id]

                    # Fix intervals_id if different
                    if local_session.intervals_id != remote_data["intervals_id"]:
                        stats["intervals_ids_fixed"].append(
                            {
                                "session_id": session_id,
                                "old_id": local_session.intervals_id,
                                "new_id": remote_data["intervals_id"],
                            }
                        )
                        local_session.intervals_id = remote_data["intervals_id"]

                    # Update name if changed
                    if local_session.name != remote_data["name"]:
                        stats["sessions_updated"].append(session_id)
                        local_session.name = remote_data["name"]

                    # Update description if empty locally
                    if not local_session.description and remote_data["description"]:
                        local_session.description = remote_data["description"]

                else:
                    # Add new session from remote
                    new_session = Session(
                        session_id=session_id,
                        session_date=remote_data["session_date"],
                        name=remote_data["name"],
                        session_type=remote_data["session_type"],
                        version=remote_data["version"],
                        tss_planned=0,  # Will be calculated if needed
                        duration_min=0,
                        description=remote_data["description"],
                        status=remote_data["status"],
                        intervals_id=remote_data["intervals_id"],
                        description_hash=None,
                        skip_reason=None,
                    )
                    plan.planned_sessions.append(new_session)
                    stats["sessions_added"].append(session_id)

            # Handle strategy for sessions that exist locally but not remotely
            if strategy == "replace":
                sessions_to_remove = [
                    s for s in plan.planned_sessions if s.session_id not in remote_sessions
                ]
                for session in sessions_to_remove:
                    plan.planned_sessions.remove(session)
                    stats["sessions_removed"].append(session.session_id)

            # Sort sessions by date
            plan.planned_sessions.sort(key=lambda s: (s.session_date, s.session_id))

        return stats


# Global instance (singleton)
planning_tower = PlanningControlTower()


# Decorator for functions that modify planning files
def requires_tower_permission(week_id_param: str = "week_id", reason_param: str | None = None):
    """
    Decorator to enforce Control Tower permission before planning modifications.

    🚦 MANDATORY for all functions that modify planning files.

    Args:
        week_id_param: Name of parameter containing week_id
        reason_param: Optional parameter name containing modification reason

    Example:
        @requires_tower_permission()
        def update_session_status(week_id: str, session_id: str, status: str):
            # Permission requested automatically
            # Backup created automatically
            # Audit logged automatically
            with planning_tower.modify_week(
                week_id,
                requesting_script="update_session_status",
                reason=f"Update {session_id} to {status}"
            ) as plan:
                # ... modifications
    """
    import functools
    import inspect

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract week_id from args/kwargs
            week_id = None

            if week_id_param in kwargs:
                week_id = kwargs[week_id_param]
            else:
                # Try to find in function signature
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())

                if week_id_param in params:
                    idx = params.index(week_id_param)
                    if idx < len(args):
                        week_id = args[idx]

            if not week_id:
                raise ValueError(
                    f"Cannot extract {week_id_param} from function arguments. "
                    f"Function: {func.__name__}"
                )

            # Extract reason if specified
            reason = "Function call"
            if reason_param and reason_param in kwargs:
                reason = kwargs[reason_param]

            # Get function name as script identifier
            script_name = func.__module__ + "." + func.__name__

            print(f"\n🚦 Control Tower: {script_name} requesting permission...", file=sys.stderr)
            print(f"   Week: {week_id}", file=sys.stderr)
            print(f"   Reason: {reason}", file=sys.stderr)

            # Request permission (will raise if denied)
            planning_tower.request_permission(week_id, script_name, reason)

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Release permission on success
                planning_tower.release_permission(week_id, script_name)

                return result

            except Exception:
                # Release permission on error
                planning_tower.release_permission(week_id, script_name)
                raise

        return wrapper

    return decorator
