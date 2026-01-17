#!/usr/bin/env python3
"""Cleanup old archives from iCloud to save space.

Keeps only the N most recent archives in iCloud (default: 3).
Local archives in releases/ are preserved.

Usage:
    poetry run cleanup-archives              # Keep 3 most recent
    poetry run cleanup-archives --keep 5     # Keep 5 most recent
    poetry run cleanup-archives --dry-run    # Preview what would be deleted
    poetry run cleanup-archives --keep-days 30  # Keep archives from last 30 days
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
RED = "\033[0;31m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(text: str) -> None:
    """Print formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{text:^70}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{GREEN}✅ {text}{RESET}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}⚠️  {text}{RESET}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{BLUE}ℹ️  {text}{RESET}")


def get_archives(archive_dir: Path) -> list[tuple[Path, datetime]]:
    """Get all archives sorted by modification time (newest first).

    Args:
        archive_dir: Directory containing archives.

    Returns:
        List of (archive_path, modification_time) tuples, sorted newest first.
    """
    if not archive_dir.exists():
        return []

    archives = []
    for archive in archive_dir.glob("sprint-*.tar.gz"):
        # Get modification time
        mtime = datetime.fromtimestamp(archive.stat().st_mtime)
        archives.append((archive, mtime))

    # Sort by modification time, newest first
    archives.sort(key=lambda x: x[1], reverse=True)

    return archives


def cleanup_archives_by_count(
    archive_dir: Path, keep_count: int, dry_run: bool = False
) -> tuple[int, list[Path]]:
    """Remove old archives, keeping only the N most recent.

    Args:
        archive_dir: Directory containing archives.
        keep_count: Number of recent archives to keep.
        dry_run: If True, only show what would be deleted.

    Returns:
        Tuple of (number of files deleted, list of deleted paths).
    """
    archives = get_archives(archive_dir)

    if not archives:
        print_info("No archives found")
        return 0, []

    # Archives to keep (most recent N)
    keep_archives = archives[:keep_count]
    # Archives to delete (everything else)
    delete_archives = archives[keep_count:]

    if keep_archives:
        print(f"\n{BOLD}Archives to keep (most recent {keep_count}):{RESET}")
        for archive, mtime in keep_archives:
            size_mb = archive.stat().st_size / (1024 * 1024)
            print(f"  ✅ {archive.name} ({size_mb:.1f} MB, {mtime:%Y-%m-%d %H:%M})")

    if not delete_archives:
        print_success(f"All archives are recent (≤{keep_count}), nothing to delete")
        return 0, []

    print(f"\n{BOLD}Archives to delete:{RESET}")
    deleted = []

    for archive, mtime in delete_archives:
        size_mb = archive.stat().st_size / (1024 * 1024)
        checksum_file = archive.parent / f"{archive.name}.sha256"

        print(f"  {YELLOW}❌{RESET} {archive.name} ({size_mb:.1f} MB, {mtime:%Y-%m-%d %H:%M})")

        if not dry_run:
            # Delete archive
            archive.unlink()
            deleted.append(archive)

            # Delete checksum if exists
            if checksum_file.exists():
                checksum_file.unlink()
                deleted.append(checksum_file)

    return len(deleted), deleted


def cleanup_archives_by_age(
    archive_dir: Path, keep_days: int, dry_run: bool = False
) -> tuple[int, list[Path]]:
    """Remove archives older than specified days.

    Args:
        archive_dir: Directory containing archives.
        keep_days: Keep archives from last N days.
        dry_run: If True, only show what would be deleted.

    Returns:
        Tuple of (number of files deleted, list of deleted paths).
    """
    archives = get_archives(archive_dir)

    if not archives:
        print_info("No archives found")
        return 0, []

    cutoff_date = datetime.now() - timedelta(days=keep_days)

    # Archives to keep (newer than cutoff)
    keep_archives = [(a, m) for a, m in archives if m >= cutoff_date]
    # Archives to delete (older than cutoff)
    delete_archives = [(a, m) for a, m in archives if m < cutoff_date]

    if keep_archives:
        print(f"\n{BOLD}Archives to keep (< {keep_days} days old):{RESET}")
        for archive, mtime in keep_archives:
            size_mb = archive.stat().st_size / (1024 * 1024)
            age_days = (datetime.now() - mtime).days
            print(f"  ✅ {archive.name} ({size_mb:.1f} MB, {age_days} days old)")

    if not delete_archives:
        print_success(f"All archives are recent (≤{keep_days} days), nothing to delete")
        return 0, []

    print(f"\n{BOLD}Archives to delete (>{keep_days} days old):{RESET}")
    deleted = []

    for archive, mtime in delete_archives:
        size_mb = archive.stat().st_size / (1024 * 1024)
        age_days = (datetime.now() - mtime).days
        checksum_file = archive.parent / f"{archive.name}.sha256"

        print(f"  {YELLOW}❌{RESET} {archive.name} ({size_mb:.1f} MB, {age_days} days old)")

        if not dry_run:
            # Delete archive
            archive.unlink()
            deleted.append(archive)

            # Delete checksum if exists
            if checksum_file.exists():
                checksum_file.unlink()
                deleted.append(checksum_file)

    return len(deleted), deleted


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup old archives from iCloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Keep 3 most recent archives (default)
  %(prog)s --keep 5            # Keep 5 most recent archives
  %(prog)s --keep-days 30      # Keep archives from last 30 days
  %(prog)s --dry-run           # Preview what would be deleted
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--keep",
        type=int,
        default=3,
        help="Number of recent archives to keep (default: 3)",
    )
    group.add_argument(
        "--keep-days",
        type=int,
        help="Keep archives from last N days",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes",
    )

    args = parser.parse_args()

    # iCloud archive directory
    archive_dir = Path.home() / "Documents" / "cyclisme-training-logs-archives"

    print_header("🗑️  iCloud Archives Cleanup")

    if args.dry_run:
        print(f"{YELLOW}{BOLD}DRY RUN MODE - No changes will be made{RESET}\n")

    print_info(f"Archive directory: {archive_dir}")

    if not archive_dir.exists():
        print_warning("Archive directory does not exist")
        return 0

    # Count total archives
    total_archives = len(list(archive_dir.glob("sprint-*.tar.gz")))
    print_info(f"Total archives found: {total_archives}")

    # Cleanup based on mode
    if args.keep_days:
        deleted_count, deleted_files = cleanup_archives_by_age(
            archive_dir, args.keep_days, args.dry_run
        )
        mode_desc = f"older than {args.keep_days} days"
    else:
        deleted_count, deleted_files = cleanup_archives_by_count(
            archive_dir, args.keep, args.dry_run
        )
        mode_desc = f"keeping {args.keep} most recent"

    # Summary
    print(f"\n{BOLD}Summary:{RESET}")
    print(f"  Mode: {mode_desc}")
    print(f"  Files deleted: {deleted_count}")

    if deleted_count > 0:
        # Calculate space freed
        space_freed = sum(
            f.stat().st_size if f.suffix != ".sha256" else 0 for f in deleted_files if f.exists()
        )
        space_freed_mb = space_freed / (1024 * 1024)
        print(f"  Space freed: {space_freed_mb:.1f} MB")

        if args.dry_run:
            print(f"\n{YELLOW}Run without --dry-run to actually delete files{RESET}")
        else:
            print(f"\n{GREEN}{BOLD}✅ Cleanup completed successfully!{RESET}")
    else:
        print(f"\n{GREEN}{BOLD}✅ No cleanup needed!{RESET}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
