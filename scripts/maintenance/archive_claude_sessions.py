#!/usr/bin/env python3
"""
Archive and summarize Claude Code sessions.

This script:
1. Lists all Claude Code sessions in ~/.claude/projects/
2. Generates markdown summaries using session_summarizer.py
3. Creates compressed archives of old sessions
4. Moves archives to project-docs/sessions/archives/

Usage:
    python archive_claude_sessions.py                    # Interactive mode
    python archive_claude_sessions.py --auto             # Auto-archive sessions older than 30 days
    python archive_claude_sessions.py --session-id <id>  # Archive specific session
    python archive_claude_sessions.py --dry-run          # Preview what would be archived
"""

import argparse
import shutil
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
RED = "\033[0;31m"
BOLD = "\033[1m"
RESET = "\033[0m"


class SessionArchiver:
    """Archive Claude Code sessions with summaries."""

    def __init__(self, project_root: Path, dry_run: bool = False):
        """Initialize archiver.

        Args:
            project_root: Root of cyclisme-training-logs project
            dry_run: If True, only show what would be done
        """
        self.project_root = project_root
        self.dry_run = dry_run

        # Paths
        self.claude_dir = (
            Path.home() / ".claude" / "projects" / "-Users-stephanejouve-cyclisme-training-logs"
        )
        self.archive_dir = project_root / "project-docs" / "sessions" / "archives"
        self.summaries_dir = project_root / "project-docs" / "sessions"

        # Create directories
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

    def list_sessions(self) -> list[tuple[str, Path, datetime]]:
        """List all Claude Code sessions.

        Returns:
            List of (session_id, jsonl_path, last_modified) tuples
        """
        if not self.claude_dir.exists():
            print(f"{RED}❌ Claude sessions directory not found: {self.claude_dir}{RESET}")
            return []

        sessions = []
        for jsonl_file in self.claude_dir.glob("*.jsonl"):
            session_id = jsonl_file.stem
            mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
            sessions.append((session_id, jsonl_file, mtime))

        # Sort by modification time, newest first
        sessions.sort(key=lambda x: x[2], reverse=True)

        return sessions

    def generate_summary(self, session_id: str, jsonl_path: Path) -> Path | None:
        """Generate markdown summary for a session.

        Args:
            session_id: Session ID
            jsonl_path: Path to session JSONL file

        Returns:
            Path to generated summary, or None if failed
        """
        # Import here to avoid E402 (module level import not at top of file)
        sys.path.insert(0, str(Path(__file__).parent))
        from session_summarizer import summarize_session

        try:
            output_path = self.summaries_dir / f"SESSION_{session_id[:8]}_SUMMARY.md"

            if self.dry_run:
                print(f"  {BLUE}Would generate:{RESET} {output_path.name}")
                return output_path

            _, summary_path = summarize_session(jsonl_path, output_path)
            print(f"  {GREEN}✅ Summary:{RESET} {summary_path.name}")
            return summary_path

        except Exception as e:
            print(f"  {YELLOW}⚠️  Failed to generate summary: {e}{RESET}")
            return None

    def archive_session(
        self, session_id: str, jsonl_path: Path, summary_path: Path | None = None
    ) -> Path | None:
        """Create compressed archive of a session.

        Args:
            session_id: Session ID
            jsonl_path: Path to session JSONL file
            summary_path: Optional path to summary file

        Returns:
            Path to created archive, or None if failed
        """
        try:
            # Archive filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d")
            archive_name = f"session_{session_id[:8]}_{timestamp}.tar.gz"
            archive_path = self.archive_dir / archive_name

            if self.dry_run:
                print(f"  {BLUE}Would create:{RESET} {archive_name}")
                return archive_path

            # Create archive
            with tarfile.open(archive_path, "w:gz") as tar:
                # Add JSONL
                tar.add(jsonl_path, arcname=f"{session_id}.jsonl")

                # Add summary if exists
                if summary_path and summary_path.exists():
                    tar.add(summary_path, arcname=f"{session_id}_SUMMARY.md")

            # Archive size
            size_mb = archive_path.stat().st_size / (1024 * 1024)
            print(f"  {GREEN}✅ Archive:{RESET} {archive_name} ({size_mb:.1f} MB)")

            return archive_path

        except Exception as e:
            print(f"  {RED}❌ Failed to create archive: {e}{RESET}")
            return None

    def cleanup_archived_session(
        self, session_id: str, jsonl_path: Path, summary_path: Path | None = None
    ) -> bool:
        """Remove original session files after archiving.

        Args:
            session_id: Session ID
            jsonl_path: Path to session JSONL file
            summary_path: Optional path to summary file

        Returns:
            True if cleaned up successfully
        """
        try:
            if self.dry_run:
                print(f"  {BLUE}Would remove:{RESET} Original session files")
                return True

            # Remove JSONL
            if jsonl_path.exists():
                jsonl_path.unlink()

            # Remove session directory (if exists)
            session_dir = self.claude_dir / session_id
            if session_dir.exists():
                shutil.rmtree(session_dir)

            print(f"  {GREEN}✅ Cleaned up:{RESET} Original files removed")
            return True

        except Exception as e:
            print(f"  {YELLOW}⚠️  Failed to cleanup: {e}{RESET}")
            return False

    def archive_old_sessions(self, days_old: int = 30) -> tuple[int, int]:
        """Archive sessions older than specified days.

        Args:
            days_old: Archive sessions older than this many days

        Returns:
            Tuple of (archived_count, failed_count)
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        sessions = self.list_sessions()

        print(f"\n{BOLD}Scanning sessions older than {days_old} days...{RESET}\n")

        archived_count = 0
        failed_count = 0

        for session_id, jsonl_path, mtime in sessions:
            age_days = (datetime.now() - mtime).days

            # Skip recent sessions
            if mtime >= cutoff_date:
                continue

            print(f"{BOLD}{session_id[:8]}...{RESET} ({age_days} days old)")

            # Generate summary
            summary_path = self.generate_summary(session_id, jsonl_path)

            # Create archive
            archive_path = self.archive_session(session_id, jsonl_path, summary_path)

            if archive_path:
                # Cleanup originals
                self.cleanup_archived_session(session_id, jsonl_path, summary_path)
                archived_count += 1
            else:
                failed_count += 1

            print()

        return archived_count, failed_count

    def display_sessions(self):
        """Display all sessions with their age."""
        sessions = self.list_sessions()

        if not sessions:
            print(f"{YELLOW}No sessions found{RESET}")
            return

        print(f"\n{BOLD}Claude Code Sessions:{RESET}\n")
        print(f"{'Session ID':<20} {'Age':<12} {'Size':<10} {'Last Modified'}")
        print("-" * 70)

        for session_id, jsonl_path, mtime in sessions:
            age_days = (datetime.now() - mtime).days
            size_mb = jsonl_path.stat().st_size / (1024 * 1024)

            # Color code by age
            if age_days < 7:
                age_color = GREEN
            elif age_days < 30:
                age_color = YELLOW
            else:
                age_color = RED

            print(
                f"{session_id[:20]:<20} "
                f"{age_color}{age_days:>3d} days{RESET:<12} "
                f"{size_mb:>6.1f} MB   "
                f"{mtime:%Y-%m-%d %H:%M}"
            )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Archive and summarize Claude Code sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # List all sessions
  %(prog)s --auto                    # Auto-archive sessions >30 days
  %(prog)s --auto --days 60          # Auto-archive sessions >60 days
  %(prog)s --session-id abc123       # Archive specific session
  %(prog)s --dry-run --auto          # Preview what would be archived
        """,
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically archive old sessions",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Archive sessions older than N days (default: 30)",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        help="Archive specific session by ID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Project root
    project_root = Path(__file__).parent.parent.parent

    # Initialize archiver
    archiver = SessionArchiver(project_root, dry_run=args.dry_run)

    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{'📦 Claude Code Session Archiver':^70}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

    if args.dry_run:
        print(f"{YELLOW}{BOLD}DRY RUN MODE - No changes will be made{RESET}\n")

    # Auto mode
    if args.auto:
        archived, failed = archiver.archive_old_sessions(args.days)

        print(f"\n{BOLD}Summary:{RESET}")
        print(f"  Sessions archived: {archived}")
        print(f"  Failed: {failed}")

        if args.dry_run:
            print(f"\n{YELLOW}Run without --dry-run to actually archive files{RESET}")
        elif archived > 0:
            print(f"\n{GREEN}{BOLD}✅ Archiving completed!{RESET}")
        else:
            print(f"\n{GREEN}{BOLD}✅ No old sessions to archive{RESET}")

    # Single session mode
    elif args.session_id:
        sessions = archiver.list_sessions()
        session = next((s for s in sessions if s[0].startswith(args.session_id)), None)

        if not session:
            print(f"{RED}❌ Session not found: {args.session_id}{RESET}")
            return 1

        session_id, jsonl_path, mtime = session

        print(f"{BOLD}Archiving session: {session_id}{RESET}\n")

        summary_path = archiver.generate_summary(session_id, jsonl_path)
        archive_path = archiver.archive_session(session_id, jsonl_path, summary_path)

        if archive_path:
            archiver.cleanup_archived_session(session_id, jsonl_path, summary_path)
            print(f"\n{GREEN}{BOLD}✅ Session archived successfully!{RESET}")
        else:
            print(f"\n{RED}{BOLD}❌ Failed to archive session{RESET}")
            return 1

    # List mode (default)
    else:
        archiver.display_sessions()
        print(f"\n{BLUE}💡 Tip: Use --auto to archive old sessions automatically{RESET}")


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
