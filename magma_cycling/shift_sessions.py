#!/usr/bin/env python3
"""
Shift (décaler) des sessions planifiées dans le temps.

Permet de:
- Décaler toutes les sessions restantes d'un certain nombre de jours
- Renumeroter les session_id pour correspondre aux jours de la semaine
- Insérer un jour de repos et décaler le reste
- Gérer les débordements entre semaines

Usage:
    # Décaler toutes les sessions à partir de jeudi d'un jour
    shift-sessions --week-id S081 --from-day 4 --shift-days 1

    # Décaler session S081-04 et suivantes, avec renumérotation
    shift-sessions --week-id S081 --from-session S081-04 --shift-days 1 --renumber

    # Insérer un jour de repos jeudi et décaler tout le reste
    shift-sessions --week-id S081 --insert-rest-day 4

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

import argparse
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from magma_cycling.api.intervals_client import IntervalsClient
from magma_cycling.config import create_intervals_client, get_data_config
from magma_cycling.planning.control_tower import planning_tower
from magma_cycling.planning.models import Session, WeeklyPlan
from magma_cycling.utils.cli import cli_main


class SessionShifter:
    """Shift and reorganize planned sessions.

    Can work with Control Tower (preferred) or standalone (legacy).
    """

    def __init__(
        self, week_id: str, plan: WeeklyPlan | None = None, planning_dir: Path | None = None
    ):
        """Initialize shifter.

        Args:
            week_id: Week identifier (e.g., "S081")
            plan: WeeklyPlan instance (if using Control Tower)
            planning_dir: Planning directory (legacy mode only)

        Note:
            Prefer passing `plan` from Control Tower context.
            Legacy mode (plan=None) is deprecated and will be removed.
        """
        self.week_id = week_id

        if plan is not None:
            # 🚦 CONTROL TOWER MODE (preferred)
            # Plan is managed by Control Tower (backup + audit already done)
            self.plan = plan
            self.planning_file = None  # Not used in Control Tower mode
        else:
            # ⚠️ LEGACY MODE (deprecated)
            # Direct file access - will be removed in future version
            print("⚠️  Warning: Using legacy mode (bypassing Control Tower)")
            print("   This mode is deprecated and will be removed")

            if planning_dir is None:
                data_config = get_data_config()
                planning_dir = data_config.week_planning_dir

            self.planning_file = planning_dir / f"week_planning_{week_id}.json"

            if not self.planning_file.exists():
                raise FileNotFoundError(f"Planning file not found: {self.planning_file}")

            # Load planning (legacy)
            self.plan = WeeklyPlan.from_json(self.planning_file)

        # Track modified sessions for sync
        self.modified_sessions: list[tuple[Session, date]] = []  # (session, old_date)

    def shift_sessions(
        self,
        from_session_id: str | None = None,
        from_day: int | None = None,
        shift_days: int = 1,
        renumber: bool = False,
        stop_at_completed: bool = True,
    ) -> list[Session]:
        """Shift sessions forward or backward in time.

        Args:
            from_session_id: Session ID to start shifting from (e.g., "S081-04")
            from_day: Day of week to start shifting from (1=Monday, 7=Sunday)
            shift_days: Number of days to shift (positive=forward, negative=backward)
            renumber: Renumber session_id to match day of week
            stop_at_completed: Don't shift sessions with status 'completed'

        Returns:
            List of modified sessions

        Raises:
            ValueError: If neither from_session_id nor from_day is specified
        """
        if from_session_id is None and from_day is None:
            raise ValueError("Must specify either from_session_id or from_day")

        # Find starting index
        if from_session_id:
            start_idx = next(
                (
                    i
                    for i, s in enumerate(self.plan.planned_sessions)
                    if s.session_id == from_session_id
                ),
                None,
            )
            if start_idx is None:
                raise ValueError(f"Session {from_session_id} not found")
        else:
            # Find first session on or after from_day
            target_date = self.plan.start_date + timedelta(days=from_day - 1)
            start_idx = next(
                (
                    i
                    for i, s in enumerate(self.plan.planned_sessions)
                    if s.session_date >= target_date
                ),
                None,
            )
            if start_idx is None:
                raise ValueError(f"No sessions found on or after day {from_day}")

        # Shift sessions
        modified_sessions = []
        for i in range(start_idx, len(self.plan.planned_sessions)):
            session = self.plan.planned_sessions[i]

            # Skip completed sessions if requested
            if stop_at_completed and session.status == "completed":
                print(f"⏭️  Skipping {session.session_id} (completed)")
                continue

            # Calculate new date
            new_date = session.session_date + timedelta(days=shift_days)

            # Check if still within week boundaries
            if new_date < self.plan.start_date or new_date > self.plan.end_date:
                print(
                    f"⚠️  {session.session_id} would move outside week boundaries "
                    f"({new_date}), skipping"
                )
                continue

            # Update session date
            old_date = session.session_date
            session.session_date = new_date

            # Track for sync
            self.modified_sessions.append((session, old_date))

            # Renumber if requested
            if renumber:
                # Calculate new session number based on day of week (1=Monday)
                new_day_num = (new_date - self.plan.start_date).days + 1
                old_session_id = session.session_id
                new_session_id = f"{self.week_id}-{new_day_num:02d}"

                # Only renumber if it's actually changing
                if new_session_id != old_session_id:
                    session.session_id = new_session_id
                    print(f"🔄 {old_session_id} → {new_session_id} ({old_date} → {new_date})")
                else:
                    print(f"📅 {session.session_id}: {old_date} → {new_date}")
            else:
                print(f"📅 {session.session_id}: {old_date} → {new_date}")

            modified_sessions.append(session)

        return modified_sessions

    def insert_rest_day(self, day: int, description: str = "Jour de repos") -> Session:
        """Insert a rest day and shift subsequent sessions.

        Args:
            day: Day of week to insert rest (1=Monday, 7=Sunday)
            description: Description for rest day

        Returns:
            Created rest day session
        """
        rest_date = self.plan.start_date + timedelta(days=day - 1)

        # Check if a session already exists on this day
        existing = next(
            (s for s in self.plan.planned_sessions if s.session_date == rest_date),
            None,
        )

        if existing:
            raise ValueError(
                f"Session {existing.session_id} already exists on day {day} ({rest_date})"
            )

        # Create rest day session
        rest_session = Session(
            session_id=f"{self.week_id}-{day:02d}",
            session_date=rest_date,
            name="Repos",
            session_type="REC",
            tss_planned=0,
            duration_min=0,
            description=description,
            status="rest_day",
        )

        # Find insertion index (sorted by date)
        insert_idx = 0
        for i, s in enumerate(self.plan.planned_sessions):
            if s.session_date < rest_date:
                insert_idx = i + 1
            else:
                break

        # Insert rest day
        self.plan.planned_sessions.insert(insert_idx, rest_session)

        print(f"😴 Inserted rest day: {rest_session.session_id} on {rest_date}")

        # Shift subsequent sessions (if any)
        try:
            self.shift_sessions(from_day=day + 1, shift_days=1, renumber=True)
        except ValueError as e:
            # No sessions to shift after rest day - that's OK
            if "No sessions found" in str(e):
                print(f"   ℹ️  No sessions to shift after day {day}")
            else:
                raise

        return rest_session

    def swap_sessions(
        self,
        session1_id: str | None = None,
        session2_id: str | None = None,
        day1: int | None = None,
        day2: int | None = None,
    ) -> tuple[Session, Session] | None:
        """Swap two sessions (exchange their dates).

        Args:
            session1_id: First session ID (e.g., "S081-04")
            session2_id: Second session ID (e.g., "S081-05")
            day1: First day of week (1-7)
            day2: Second day of week (1-7)

        Returns:
            Tuple of (session1, session2) if swapped, None if failed

        Raises:
            ValueError: If neither session IDs nor days are specified, or if
                       attempting to swap a completed session
        """
        # Find sessions
        if session1_id and session2_id:
            session1 = next(
                (s for s in self.plan.planned_sessions if s.session_id == session1_id), None
            )
            session2 = next(
                (s for s in self.plan.planned_sessions if s.session_id == session2_id), None
            )

            if not session1:
                raise ValueError(f"Session {session1_id} not found")
            if not session2:
                raise ValueError(f"Session {session2_id} not found")

        elif day1 is not None and day2 is not None:
            date1 = self.plan.start_date + timedelta(days=day1 - 1)
            date2 = self.plan.start_date + timedelta(days=day2 - 1)

            session1 = next(
                (s for s in self.plan.planned_sessions if s.session_date == date1), None
            )
            session2 = next(
                (s for s in self.plan.planned_sessions if s.session_date == date2), None
            )

            if not session1:
                raise ValueError(f"No session found on day {day1} ({date1})")
            if not session2:
                raise ValueError(f"No session found on day {day2} ({date2})")

        else:
            raise ValueError("Must specify either session IDs or days")

        # ⚠️ CRITICAL: Prevent swapping completed sessions
        if session1.status == "completed":
            raise ValueError(
                f"❌ Cannot swap {session1.session_id}: session already completed!\n"
                f"   Completed sessions must not be modified."
            )
        if session2.status == "completed":
            raise ValueError(
                f"❌ Cannot swap {session2.session_id}: session already completed!\n"
                f"   Completed sessions must not be modified."
            )

        # Swap dates
        old_date1 = session1.session_date
        old_date2 = session2.session_date

        session1.session_date = old_date2
        session2.session_date = old_date1

        # Track for sync
        self.modified_sessions.append((session1, old_date1))
        self.modified_sessions.append((session2, old_date2))

        print("🔄 Swapped sessions:")
        print(f"   {session1.session_id}: {old_date1} ↔ {old_date2}")
        print(f"   {session2.session_id}: {old_date2} ↔ {old_date1}")

        return (session1, session2)

    def remove_session(self, session_id: str) -> bool:
        """Remove a session from the plan.

        Args:
            session_id: Session ID to remove

        Returns:
            True if removed, False if not found
        """
        initial_count = len(self.plan.planned_sessions)
        self.plan.planned_sessions = [
            s for s in self.plan.planned_sessions if s.session_id != session_id
        ]

        removed = len(self.plan.planned_sessions) < initial_count
        if removed:
            print(f"🗑️  Removed session: {session_id}")

        return removed

    def sync_session_changes(self, client: IntervalsClient) -> bool:
        """Synchronize session date changes with Intervals.icu.

        Args:
            client: IntervalsClient instance

        Returns:
            True if all syncs successful, False otherwise
        """
        if not self.modified_sessions:
            print("\n💡 No sessions modified, nothing to sync")
            return True

        print(f"\n🔄 Synchronizing {len(self.modified_sessions)} session(s) with Intervals.icu...")

        success_count = 0
        for session, old_date in self.modified_sessions:
            # Skip if no intervals_id (not yet uploaded)
            if not session.intervals_id:
                print(f"   ⏭️  {session.session_id}: No intervals_id, skipping sync")
                continue

            try:
                # Get the event
                event = client.get_event(session.intervals_id)
                if not event:
                    print(
                        f"   ⚠️  {session.session_id}: Event {session.intervals_id} not found "
                        f"on Intervals.icu"
                    )
                    continue

                # Update the event date
                new_date_str = session.session_date.isoformat()
                update_data = {"start_date_local": new_date_str}

                updated = client.update_event(session.intervals_id, update_data)
                if updated:
                    print(
                        f"   ✅ {session.session_id}: Updated event {session.intervals_id} "
                        f"({old_date} → {session.session_date})"
                    )
                    success_count += 1
                else:
                    print(
                        f"   ❌ {session.session_id}: Failed to update event "
                        f"{session.intervals_id}"
                    )

            except Exception as e:
                print(f"   ❌ {session.session_id}: Error syncing - {e}")

        total = len([s for s, _ in self.modified_sessions if s.intervals_id])
        if total > 0:
            print(f"\n✅ Synced {success_count}/{total} sessions with Intervals.icu")
            return success_count == total
        else:
            print("\n💡 No sessions had intervals_id to sync")
            return True

    def save(self, dry_run: bool = False, sync: bool = False) -> bool:
        """Save modified planning and optionally sync with Intervals.icu.

        Args:
            dry_run: If True, don't actually save
            sync: If True, synchronize with Intervals.icu

        Returns:
            True if saved successfully

        Note:
            In Control Tower mode, plan is auto-saved by context manager.
            This method only handles sync in that case.
        """
        if dry_run:
            print("\n🔍 DRY RUN - Changes not saved")
            return False

        # 🚦 CONTROL TOWER MODE
        if self.planning_file is None:
            print("\n💡 Control Tower mode - plan will be auto-saved by context manager")

            # Only handle sync if requested
            if sync:
                try:
                    client = create_intervals_client()
                    self.sync_session_changes(client)
                except Exception as e:
                    print(f"\n⚠️  Warning: Sync with Intervals.icu failed: {e}")
                    # Don't fail the whole operation if sync fails
                    return True

            return True

        # ⚠️ LEGACY MODE (deprecated)
        try:
            # Update timestamp
            self.plan.last_updated = datetime.now(UTC)

            # Save
            self.plan.to_json(self.planning_file)

            print(f"\n✅ Planning saved: {self.planning_file}")

            # Sync with Intervals.icu if requested
            if sync:
                try:
                    client = create_intervals_client()
                    self.sync_session_changes(client)
                except Exception as e:
                    print(f"\n⚠️  Warning: Sync with Intervals.icu failed: {e}")
                    # Don't fail the whole operation if sync fails
                    return True

            return True

        except Exception as e:
            print(f"\n❌ Error saving planning: {e}")
            return False

    def display_summary(self):
        """Display current planning summary."""
        print(f"\n📅 Planning {self.week_id} ({self.plan.start_date} → {self.plan.end_date})")
        print("=" * 70)

        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        for i, day_name in enumerate(days, 1):
            day_date = self.plan.start_date + timedelta(days=i - 1)
            sessions = [s for s in self.plan.planned_sessions if s.session_date == day_date]

            if sessions:
                s = sessions[0]
                status_emoji = {
                    "planned": "✅",
                    "completed": "✔️",
                    "rest_day": "😴",
                    "cancelled": "❌",
                    "skipped": "⏭️",
                    "replaced": "🔄",
                }.get(s.status, "❓")
                print(
                    f"{status_emoji} {s.session_id}: {day_name:10} "
                    f"({day_date}) - {s.name:15} [{s.status}]"
                )
            else:
                print(f"   S{self.week_id[1:]}-{i:02d}: {day_name:10} ({day_date}) - VIDE")


@cli_main
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Shift planned training sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Shift all sessions from day 4 (Thursday) by +1 day
  %(prog)s --week-id S081 --from-day 4 --shift-days 1

  # Shift session S081-04 and following, with renumbering
  %(prog)s --week-id S081 --from-session S081-04 --shift-days 1 --renumber

  # Insert rest day on Thursday and shift everything after
  %(prog)s --week-id S081 --insert-rest-day 4

  # Swap/rotate two sessions by ID
  %(prog)s --week-id S081 --swap S081-04 S081-05

  # Swap/rotate sessions on two days (Thursday ↔ Friday)
  %(prog)s --week-id S081 --swap-days 4 5

  # Preview changes without saving
  %(prog)s --week-id S081 --from-day 4 --shift-days 1 --dry-run
        """,
    )

    parser.add_argument("--week-id", required=True, help="Week ID (e.g., S081)")

    # Shift mode
    shift_group = parser.add_argument_group("shift options")
    shift_group.add_argument(
        "--from-session", help="Session ID to start shifting from (e.g., S081-04)"
    )
    shift_group.add_argument(
        "--from-day", type=int, help="Day of week to start shifting from (1-7)"
    )
    shift_group.add_argument(
        "--shift-days", type=int, default=1, help="Number of days to shift (default: 1)"
    )
    shift_group.add_argument(
        "--renumber", action="store_true", help="Renumber session_id to match day of week"
    )

    # Insert rest day mode
    parser.add_argument(
        "--insert-rest-day",
        type=int,
        metavar="DAY",
        help="Insert rest day on specified day (1-7) and shift following sessions",
    )

    # Swap/rotate mode
    swap_group = parser.add_argument_group("swap/rotate options")
    swap_group.add_argument(
        "--swap",
        nargs=2,
        metavar=("SESSION1", "SESSION2"),
        help="Swap two sessions by ID (e.g., S081-04 S081-05)",
    )
    swap_group.add_argument(
        "--swap-days",
        nargs=2,
        type=int,
        metavar=("DAY1", "DAY2"),
        help="Swap sessions on two days (e.g., 4 5 to swap Thursday and Friday)",
    )

    # Remove session mode
    parser.add_argument("--remove-session", help="Remove session by ID (e.g., S081-07)")

    # Options
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Synchronize changes with Intervals.icu (update event dates)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")

    args = parser.parse_args()

    # Build operation description for audit log
    operation_parts = []
    if args.insert_rest_day:
        operation_parts.append(f"insert rest day {args.insert_rest_day}")
    elif args.swap:
        operation_parts.append(f"swap {args.swap[0]} ↔ {args.swap[1]}")
    elif args.swap_days:
        operation_parts.append(f"swap days {args.swap_days[0]} ↔ {args.swap_days[1]}")
    elif args.remove_session:
        operation_parts.append(f"remove {args.remove_session}")
    elif args.from_session:
        operation_parts.append(
            f"shift from {args.from_session} by {args.shift_days} days"
            + (" (renumber)" if args.renumber else "")
        )
    elif args.from_day:
        operation_parts.append(
            f"shift from day {args.from_day} by {args.shift_days} days"
            + (" (renumber)" if args.renumber else "")
        )
    else:
        print(
            "\n❌ Must specify --insert-rest-day, --swap, --swap-days, "
            "--remove-session, or shift options"
        )
        return 1

    operation_description = ", ".join(operation_parts)

    print(f"\n{'🔍 DRY RUN MODE' if args.dry_run else '🔧 SHIFT SESSIONS'}")
    print("=" * 70)

    # 🚦 USE CONTROL TOWER for permission + backup + audit
    with planning_tower.modify_week(
        args.week_id,
        requesting_script="shift-sessions",
        reason=operation_description,
        auto_save=not args.dry_run,  # Only save if not dry-run
    ) as plan:
        # Create shifter in Control Tower mode
        shifter = SessionShifter(week_id=args.week_id, plan=plan)

        # Display current state
        shifter.display_summary()

        # Perform operation
        if args.insert_rest_day:
            shifter.insert_rest_day(args.insert_rest_day)

        elif args.swap:
            shifter.swap_sessions(session1_id=args.swap[0], session2_id=args.swap[1])

        elif args.swap_days:
            shifter.swap_sessions(day1=args.swap_days[0], day2=args.swap_days[1])

        elif args.remove_session:
            shifter.remove_session(args.remove_session)

        elif args.from_session or args.from_day:
            shifter.shift_sessions(
                from_session_id=args.from_session,
                from_day=args.from_day,
                shift_days=args.shift_days,
                renumber=args.renumber,
            )

        # Display final state
        shifter.display_summary()

        # Handle sync (save will be automatic via Control Tower)
        if not args.dry_run and args.sync:
            shifter.save(dry_run=False, sync=True)

    # Success messages
    if args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")
    elif args.sync:
        print("\n✅ Changes saved and synced with Intervals.icu")
    else:
        print("\n✅ Changes saved")

    return 0


if __name__ == "__main__":
    main()
