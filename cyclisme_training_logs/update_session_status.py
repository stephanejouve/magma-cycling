#!/usr/bin/env python3
"""
Update Session Status Tool with Intervals.icu Sync.

Updates training session status in local planning JSON and optionally
synchronizes with Intervals.icu calendar.

Behavior:
    - Local: Always updates planning JSON with status and reason
    - Intervals.icu sync (--sync flag):
      * cancelled/skipped: Converts event to NOTE with [ANNULÉE]/[SAUTÉE] tag
        (or creates NOTE if event doesn't exist)
      * modified: Updates event description with modification note
      * completed: No action (activity should exist)

Usage:
    # Cancel a session (local only)
    poetry run update-session --week S074 --session S074-05 --status cancelled --reason "Fatigue"

    # Cancel and sync with Intervals.icu (converts to NOTE)
    poetry run update-session --week S074 --session S074-05 --status cancelled --reason "Fatigue" --sync

    # Skip session with sync
    poetry run update-session --week S074 --session S074-03 --status skipped --reason "Travel" --sync

    # Mark as completed (local only)
    poetry run update-session --week S074 --session S074-01 --status completed

Metadata:
    Created: 2026-01-02
    Updated: 2026-01-02
    Author: Claude Code
    Category: TOOLS
    Status: Production
    Priority: P1
    Version: 2.1.0
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from api.intervals_client import IntervalsClient  # noqa: E402
from weekly_planner import WeeklyPlanner  # noqa: E402

# Statuses that should remove the event from Intervals.icu
STATUSES_TO_DELETE = ["cancelled", "skipped"]


def load_intervals_credentials() -> tuple[str | None, str | None]:
    """Load Intervals.icu credentials from environment.

    Returns:
        Tuple of (athlete_id, api_key) or (None, None) if not configured.
    """
    athlete_id = os.getenv("INTERVALS_ATHLETE_ID")
    api_key = os.getenv("INTERVALS_API_KEY")

    if not athlete_id or not api_key:
        return None, None

    return athlete_id, api_key


def find_event_by_session(
    client: IntervalsClient, session_id: str, session_date: str
) -> dict | None:
    """Find Intervals.icu event matching a session.

    Args:
        client: IntervalsClient instance
        session_id: Session ID (e.g., "S074-05")
        session_date: Session date (YYYY-MM-DD)

    Returns:
        Event dict if found, None otherwise
    """
    try:
        # Get events for the session date
        events = client.get_events(oldest=session_date, newest=session_date)

        # Find event matching session_id in name
        for event in events:
            event_name = event.get("name", "")
            if session_id in event_name:
                return event

        return None

    except Exception as e:
        print(f"⚠️  Warning: Could not search for event on Intervals.icu: {e}")
        return None


def sync_with_intervals(
    client: IntervalsClient,
    session_id: str,
    session_date: str,
    new_status: str,
    reason: str | None = None,
    session_info: dict | None = None,
) -> bool:
    """Synchronize session status change with Intervals.icu.

    Args:
        client: IntervalsClient instance
        session_id: Session ID (e.g., "S074-05")
        session_date: Session date (YYYY-MM-DD)
        new_status: New session status
        reason: Optional reason for status change
        session_info: Session info from planning JSON (for creating cancelled notes)

    Returns:
        True if sync successful, False otherwise
    """
    print("\n🔄 Synchronizing with Intervals.icu...")

    # Find the event
    event = find_event_by_session(client, session_id, session_date)

    # Decide action based on status
    if new_status in STATUSES_TO_DELETE:
        if event:
            # Event exists - convert to NOTE with [ANNULÉE] tag
            event_id = event.get("id")
            event_name = event.get("name", "Unknown")
            event_category = event.get("category", "WORKOUT")

            print(f"   Found event: {event_name} (ID: {event_id}, Type: {event_category})")

            # Check if already marked as cancelled
            if event_name.startswith("[ANNULÉE]"):
                print("   ℹ️  Event already marked as cancelled")
                return True

            # Prepare cancelled note format
            status_emoji = "❌" if new_status == "cancelled" else "⏭️"
            status_text = "ANNULÉE" if new_status == "cancelled" else "SAUTÉE"

            original_description = event.get("description", "")
            new_description = (
                f"{status_emoji} SÉANCE {status_text}\n"
                f"Raison: {reason or 'Non spécifiée'}\n\n"
                f"--- Description originale ---\n"
                f"{original_description}"
            )

            update_data = {
                "name": f"[{status_text}] {event_name}",
                "category": "NOTE",
                "description": new_description,
            }

            print(f"   Action: Converting to NOTE with [{status_text}] tag...")
            updated = client.update_event(event_id, update_data)

            if updated:
                print("   ✅ Event converted to NOTE on Intervals.icu")
                return True
            else:
                print("   ❌ Failed to update event on Intervals.icu")
                return False
        else:
            # Event doesn't exist - create NOTE with [ANNULÉE] tag
            print(f"   ℹ️  No matching event found on Intervals.icu for {session_id}")

            if not session_info:
                print("   ⚠️  Cannot create cancelled note without session info")
                return True

            status_emoji = "❌" if new_status == "cancelled" else "⏭️"
            status_text = "ANNULÉE" if new_status == "cancelled" else "SAUTÉE"

            session_name = session_info.get("name", "Unknown")
            session_type = session_info.get("type", "")
            session_version = session_info.get("version", "")
            session_desc = session_info.get("description", "")
            session_tss = session_info.get("tss_planned", 0)
            session_duration = session_info.get("duration_min", 0)

            full_name = f"{session_id}-{session_type}-{session_name}-{session_version}"

            event_data = {
                "category": "NOTE",
                "name": f"[{status_text}] {full_name}",
                "description": (
                    f"{status_emoji} SÉANCE {status_text}\n"
                    f"Raison: {reason or 'Non spécifiée'}\n\n"
                    f"--- Description originale ---\n"
                    f"{session_desc} ({session_duration}min, {session_tss} TSS)"
                ),
                "start_date_local": f"{session_date}T00:00:00",
            }

            print(f"   Action: Creating NOTE with [{status_text}] tag...")
            created = client.create_event(event_data)

            if created:
                print(f"   ✅ Cancelled note created on Intervals.icu (ID: {created.get('id')})")
                return True
            else:
                print("   ❌ Failed to create cancelled note on Intervals.icu")
                return False

    elif new_status == "modified":
        if not event:
            print(f"   ℹ️  No matching event found on Intervals.icu for {session_id}")
            return True

        event_id = event.get("id")
        event_name = event.get("name", "Unknown")
        print(f"   Found event: {event_name} (ID: {event_id})")

        # Update event description to indicate modification
        print("   Action: Updating event description...")

        update_data = {
            "description": event.get("description", "")
            + f"\n\n⚠️ MODIFIED: {reason or 'See local planning'}"
        }

        updated = client.update_event(event_id, update_data)

        if updated:
            print("   ✅ Event updated on Intervals.icu")
            return True
        else:
            print("   ❌ Failed to update event on Intervals.icu")
            return False

    elif new_status == "completed":
        # Leave event - actual activity will exist
        print("   Action: No change (activity should exist)")
        return True

    else:
        # Other statuses - no action needed
        print(f"   Action: No sync needed for status '{new_status}'")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update session status in planning JSON and optionally sync with Intervals.icu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Cancel session (local only)
  %(prog)s --week S074 --session S074-05 --status cancelled --reason "Fatigue"

  # Cancel and sync with Intervals.icu
  %(prog)s --week S074 --session S074-05 --status cancelled --reason "Fatigue" --sync

  # Skip session with sync
  %(prog)s --week S074 --session S074-03 --status skipped --reason "Travel" --sync

Valid statuses:
  - planned     : Session is planned (default)
  - completed   : Session was completed
  - cancelled   : Session was cancelled (requires --reason)
  - skipped     : Session was skipped (requires --reason)
  - replaced    : Session was replaced (requires --reason)
  - rest_day    : Converted to rest day
  - modified    : Session was modified
        """,
    )

    parser.add_argument("--week", type=str, required=True, help="Week ID (e.g., S074)")

    parser.add_argument("--session", type=str, required=True, help="Session ID (e.g., S074-05)")

    parser.add_argument(
        "--status",
        type=str,
        required=True,
        choices=[
            "planned",
            "completed",
            "cancelled",
            "skipped",
            "rest_day",
            "replaced",
            "modified",
        ],
        help="New status for the session",
    )

    parser.add_argument(
        "--reason",
        type=str,
        help="Reason for status change (required for cancelled/skipped/replaced)",
    )

    parser.add_argument(
        "--start-date", type=str, help="Week start date (YYYY-MM-DD) - optional if JSON exists"
    )

    parser.add_argument(
        "--sync", action="store_true", help="Synchronize change with Intervals.icu calendar"
    )

    args = parser.parse_args()

    # Validate reason requirement
    if args.status in ["cancelled", "skipped", "replaced"] and not args.reason:
        parser.error(f"Status '{args.status}' requires --reason")

    try:
        # Parse start date if provided
        if args.start_date:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        else:
            start_date = datetime.now()

        # Get data repository configuration
        from cyclisme_training_logs.config import get_data_config

        try:
            data_config = get_data_config()
            planning_dir = data_config.week_planning_dir
        except FileNotFoundError:
            # Fallback to legacy path
            project_root = Path(__file__).parent.parent
            planning_dir = project_root / "data" / "week_planning"

        # Create planner instance
        project_root = Path(__file__).parent.parent
        planner = WeeklyPlanner(args.week, start_date, project_root)

        print(f"\n📝 Updating session {args.session}")
        print(f"   Week: {args.week}")
        print(f"   Status: {args.status}")
        if args.reason:
            print(f"   Reason: {args.reason}")

        # Update local JSON
        success = planner.update_session_status(
            session_id=args.session, status=args.status, reason=args.reason
        )

        if not success:
            print("\n❌ Failed to update local planning JSON")
            sys.exit(1)

        print("\n✅ Local planning JSON updated successfully")

        # Sync with Intervals.icu if requested
        if args.sync:
            athlete_id, api_key = load_intervals_credentials()

            if not athlete_id or not api_key:
                print("\n⚠️  Warning: Intervals.icu credentials not configured")
                print("   Set INTERVALS_ATHLETE_ID and INTERVALS_API_KEY environment variables")
                print("   Skipping sync with Intervals.icu")
                sys.exit(0)

            # Get session date from planning
            planning_file = planning_dir / f"week_planning_{args.week}.json"

            if not planning_file.exists():
                print("\n⚠️  Warning: Could not find planning file to get session date")
                print(f"   Expected: {planning_file}")
                print("   Skipping sync with Intervals.icu")
                sys.exit(0)

            with open(planning_file) as f:
                planning = json.load(f)

            session_date = None
            session_info = None
            for session in planning.get("planned_sessions", []):
                if session.get("session_id") == args.session:
                    session_date = session.get("date")
                    session_info = session
                    break

            if not session_date:
                print("\n⚠️  Warning: Could not find session date in planning")
                print("   Skipping sync with Intervals.icu")
                sys.exit(0)

            # Create Intervals.icu client
            client = IntervalsClient(athlete_id=athlete_id, api_key=api_key)

            # Sync
            sync_success = sync_with_intervals(
                client=client,
                session_id=args.session,
                session_date=session_date,
                new_status=args.status,
                reason=args.reason,
                session_info=session_info,
            )

            if sync_success:
                print("\n✅ Successfully synchronized with Intervals.icu")
            else:
                print("\n⚠️  Warning: Sync with Intervals.icu failed (local changes preserved)")

        print("\n✨ Done!")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
