#!/usr/bin/env python3
"""
Automatic backup system for planning files.

Automatically creates timestamped backups before any modification to:
- week_planning_*.json
- *_workouts.txt

Backups stored in: data/week_planning/backups/

Author: Claude Sonnet 4.5
Created: 2026-02-20
"""

import shutil
from datetime import datetime
from pathlib import Path


class PlanningBackup:
    """Automatic backup for planning files."""

    def __init__(self, planning_dir: Path | None = None):
        """Initialize backup system.

        Args:
            planning_dir: Planning directory (default: auto-detected from config)
        """
        if planning_dir is None:
            from magma_cycling.config import get_data_config

            data_config = get_data_config()
            planning_dir = data_config.week_planning_dir

        self.planning_dir = Path(planning_dir)
        self.backup_dir = self.planning_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_file(self, file_path: Path) -> Path | None:
        """Create timestamped backup of a file.

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup file, or None if source doesn't exist

        Example:
            >>> backup = PlanningBackup()
            >>> backup_path = backup.backup_file(Path("week_planning_S081.json"))
            >>> # Creates: backups/week_planning_S081_20260220_234530.json
        """
        if not file_path.exists():
            return None

        # Generate timestamp (format: YYYYMMDD_HHMMSS)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Construct backup filename
        stem = file_path.stem  # e.g., "week_planning_S081"
        suffix = file_path.suffix  # e.g., ".json"
        backup_name = f"{stem}_{timestamp}{suffix}"

        backup_path = self.backup_dir / backup_name

        # Copy file to backup
        shutil.copy2(file_path, backup_path)

        return backup_path

    def backup_week_files(self, week_id: str) -> dict[str, Path]:
        """Backup all files for a given week.

        Args:
            week_id: Week identifier (e.g., "S081")

        Returns:
            Dict mapping file type to backup path
            Example: {"json": Path(...), "workouts": Path(...)}
        """
        backups = {}

        # Backup JSON planning file
        json_file = self.planning_dir / f"week_planning_{week_id}.json"
        if json_file.exists():
            backup_path = self.backup_file(json_file)
            if backup_path:
                backups["json"] = backup_path

        # Backup workouts text file
        workouts_file = self.planning_dir / f"{week_id}_workouts.txt"
        if workouts_file.exists():
            backup_path = self.backup_file(workouts_file)
            if backup_path:
                backups["workouts"] = backup_path

        return backups

    def list_backups(self, week_id: str | None = None) -> list[Path]:
        """List all backups, optionally filtered by week.

        Args:
            week_id: Optional week filter (e.g., "S081")

        Returns:
            List of backup file paths, sorted by timestamp (newest first)
        """
        if week_id:
            pattern = f"*{week_id}*"
        else:
            pattern = "*"

        backups = sorted(self.backup_dir.glob(pattern), reverse=True)
        return backups

    def restore_backup(self, backup_path: Path, dry_run: bool = False) -> Path | None:
        """Restore a backup file to its original location.

        Args:
            backup_path: Path to backup file
            dry_run: If True, only show what would be restored

        Returns:
            Path where file would be/was restored, or None if backup doesn't exist

        Example:
            >>> backup = PlanningBackup()
            >>> backup.restore_backup(
            ...     Path("backups/week_planning_S081_20260220_234530.json")
            ... )
        """
        if not backup_path.exists():
            return None

        # Parse backup filename to get original name
        # Format: week_planning_S081_20260220_234530.json
        # Extract: week_planning_S081.json
        name = backup_path.name
        parts = name.split("_")

        # Find timestamp part (YYYYMMDD_HHMMSS) and remove it
        timestamp_idx = None
        for i, part in enumerate(parts):
            if len(part) == 8 and part.isdigit():  # YYYYMMDD
                timestamp_idx = i
                break

        if timestamp_idx is None:
            raise ValueError(f"Cannot parse backup filename: {name}")

        # Reconstruct original filename
        original_parts = parts[:timestamp_idx]
        suffix = backup_path.suffix
        original_name = "_".join(original_parts) + suffix

        restore_path = self.planning_dir / original_name

        if dry_run:
            print(f"Would restore: {backup_path.name} → {original_name}")
            return restore_path

        # Create backup of current file before restoring (if it exists)
        if restore_path.exists():
            current_backup = self.backup_file(restore_path)
            print(f"Created backup of current file: {current_backup.name}")

        # Restore backup
        shutil.copy2(backup_path, restore_path)

        return restore_path

    def cleanup_old_backups(self, keep_count: int = 10, week_id: str | None = None) -> int:
        """Remove old backups, keeping only the N most recent.

        Args:
            keep_count: Number of backups to keep per file
            week_id: Optional week filter

        Returns:
            Number of backups deleted
        """
        deleted = 0

        # Group backups by base filename (without timestamp)
        from collections import defaultdict

        groups = defaultdict(list)

        for backup in self.list_backups(week_id):
            # Extract base name (without timestamp)
            name = backup.name
            parts = name.split("_")

            # Find timestamp
            timestamp_idx = None
            for i, part in enumerate(parts):
                if len(part) == 8 and part.isdigit():
                    timestamp_idx = i
                    break

            if timestamp_idx is not None:
                base_name = "_".join(parts[:timestamp_idx]) + backup.suffix
                groups[base_name].append(backup)

        # Keep only N most recent for each group
        for base_name, backups in groups.items():
            # Already sorted by timestamp (newest first)
            to_delete = backups[keep_count:]

            for backup in to_delete:
                backup.unlink()
                deleted += 1

        return deleted


def safe_write(file_path: Path, content: str, backup_dir: Path | None = None) -> Path | None:
    """Backup-then-write: create a backup before overwriting a file.

    Args:
        file_path: Path to write to
        content: Content to write
        backup_dir: Directory for backups (default: file's parent / "backups")

    Returns:
        Path to backup file, or None if file didn't exist before write
    """
    file_path = Path(file_path)
    backup = PlanningBackup(backup_dir or file_path.parent)
    backup_path = backup.backup_file(file_path)
    file_path.write_text(content, encoding="utf-8")
    return backup_path


def auto_backup(week_id: str) -> dict[str, Path]:
    """Convenience function for automatic backup before modifications.

    Args:
        week_id: Week identifier (e.g., "S081")

    Returns:
        Dict of created backups

    Example:
        >>> from magma_cycling.planning.backup import auto_backup
        >>> backups = auto_backup("S081")
        >>> # Proceed with modifications...
    """
    backup = PlanningBackup()
    return backup.backup_week_files(week_id)
