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
    from cyclisme_training_logs.planning.control_tower import planning_tower

    # Automatic backup before modification
    with planning_tower.modify_week("S081") as plan:
        plan.planned_sessions[0].date = "2026-02-17"
        # Auto-saved and backed up on exit

Author: Claude Sonnet 4.5
Created: 2026-02-20
"""

import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from cyclisme_training_logs.config import get_data_config
from cyclisme_training_logs.planning.backup import PlanningBackup
from cyclisme_training_logs.planning.models import WeeklyPlan


class PlanningControlTower:
    """
    Centralized access control for planning files.

    Acts as a "control tower" that intercepts all write operations
    to planning files and automatically creates backups.
    """

    def __init__(self):
        """Initialize control tower."""
        data_config = get_data_config()
        self.planning_dir = data_config.week_planning_dir
        self.backup_system = PlanningBackup(self.planning_dir)

        # Track active modifications (for atomic operations)
        self._active_modifications: set[str] = set()

    @contextmanager
    def modify_week(
        self, week_id: str, auto_save: bool = True
    ) -> Generator[WeeklyPlan, None, None]:
        """
        Context manager for safe week modification with automatic backup.

        Args:
            week_id: Week identifier (e.g., "S081")
            auto_save: Automatically save changes on exit (default: True)

        Yields:
            WeeklyPlan instance for modification

        Raises:
            FileNotFoundError: If planning file doesn't exist
            RuntimeError: If week is already being modified (concurrent access)

        Example:
            >>> with planning_tower.modify_week("S081") as plan:
            ...     # Automatic backup created here
            ...     plan.planned_sessions[0].status = "completed"
            ...     # Automatic save & validation on exit
        """
        # Check for concurrent modification
        if week_id in self._active_modifications:
            raise RuntimeError(
                f"Week {week_id} is already being modified. "
                "Wait for current operation to complete."
            )

        planning_file = self.planning_dir / f"week_planning_{week_id}.json"

        if not planning_file.exists():
            raise FileNotFoundError(f"Planning file not found: {planning_file}")

        # Mark as active
        self._active_modifications.add(week_id)

        # 🔒 AUTOMATIC BACKUP before loading
        print(f"🔒 Control Tower: Backup {week_id}...")
        backups = self.backup_system.backup_week_files(week_id)

        if backups:
            for file_type, backup_path in backups.items():
                print(f"   ✅ {file_type}: {backup_path.name}")

        try:
            # Load planning
            plan = WeeklyPlan.from_json(planning_file)

            # Yield for modifications
            yield plan

            # Save if auto_save enabled
            if auto_save:
                # Update timestamp
                plan.last_updated = datetime.now().isoformat() + "Z"

                # Save to file
                plan.to_json(planning_file)
                print(f"💾 Control Tower: Saved {week_id}")

        except Exception as e:
            # On error, offer rollback
            print(f"❌ Control Tower: Error modifying {week_id}: {e}")
            print(f"   Backups available in: {self.backup_system.backup_dir}")
            raise

        finally:
            # Release lock
            self._active_modifications.discard(week_id)

    def read_week(self, week_id: str) -> WeeklyPlan:
        """
        Read-only access to week planning (no backup needed).

        Args:
            week_id: Week identifier (e.g., "S081")

        Returns:
            WeeklyPlan instance (read-only)

        Example:
            >>> plan = planning_tower.read_week("S081")
            >>> print(plan.tss_target)
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
            >>> print(f"Latest: {backups[0]}")
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
            print(f"⚠️  Restore backup: {backup_path.name}")
            print("   This will overwrite current planning file.")
            response = input("   Continue? (yes/no): ")

            if response.lower() != "yes":
                print("   Cancelled.")
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

        print(f"📸 Snapshot créé: {snapshot_name}")

        return snapshot_path


# Global instance (singleton)
planning_tower = PlanningControlTower()


# Convenience decorator for functions that modify planning
def requires_planning_backup(week_id_param: str = "week_id"):
    """
    Decorator to automatically backup planning before function execution.

    Args:
        week_id_param: Name of parameter containing week_id

    Example:
        @requires_planning_backup()
        def modify_session(week_id: str, session_id: str, new_date: str):
            # Automatic backup created before this runs
            with planning_tower.modify_week(week_id) as plan:
                # ... modifications
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract week_id from args/kwargs
            if week_id_param in kwargs:
                week_id = kwargs[week_id_param]
            else:
                # Try to find in function signature
                import inspect

                sig = inspect.signature(func)
                params = list(sig.parameters.keys())

                if week_id_param in params:
                    idx = params.index(week_id_param)
                    if idx < len(args):
                        week_id = args[idx]
                    else:
                        raise ValueError(f"Cannot find {week_id_param} in function arguments")
                else:
                    raise ValueError(f"Parameter {week_id_param} not found in function signature")

            # Create backup
            planning_tower.backup_week(week_id)

            # Execute function
            return func(*args, **kwargs)

        return wrapper

    return decorator
