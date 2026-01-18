r"""
Bidirectional sync between local TrainingCalendar and Intervals.icu.

Handles external coach modifications (add/remove/move/modify workouts).
Delegates to existing tools:
- upload_workouts.py for push operations (via CLI)
- intervals_client for pull operations

Examples:
    Check sync status to detect coach modifications::

        from cyclisme_training_logs.planning.intervals_sync import IntervalsSync
        from cyclisme_training_logs.planning.calendar import TrainingCalendar
        from cyclisme_training_logs.config.athlete_profile import AthleteProfile
        from datetime import date

        # Create local calendar
        profile = AthleteProfile.from_env()
        calendar = TrainingCalendar(year=2026, athlete_profile=profile)

        # Add sessions to calendar
        # ...

        # Check sync status with Intervals.icu
        sync = IntervalsSync()
        status = sync.get_sync_status(
            calendar=calendar,
            start_date=date(2026, 1, 20),
            end_date=date(2026, 1, 26)
        )

        print(status.summary())
        # ⚠️ Changements détectés:
        #   • 1 workouts supprimés par coach
        #   • 2 workouts modifiés par coach

        # Detail changes
        if status.diff.removed_remote:
            print("\\n🗑️ Workouts supprimés par coach:")
            for workout in status.diff.removed_remote:
                print(f"  • {workout['date']}: {workout['name']}")

Author: Stéphane Jouve
Created: 2026-01-18
Sprint: R3 - Module 3

Metadata:
    Status: Production
    Priority: P2
    Version: v1.0
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from difflib import unified_diff

from cyclisme_training_logs.config import create_intervals_client
from cyclisme_training_logs.planning.calendar import TrainingCalendar
from cyclisme_training_logs.upload_workouts import calculate_description_hash


@dataclass
class SyncStatus:
    """
    Status of sync operation.

    Attributes:
        success: Whether sync operation succeeded
        events_created: Number of events created in Intervals.icu
        events_updated: Number of events updated in Intervals.icu
        errors: List of error messages
        warnings: List of warning messages
    """

    success: bool
    events_created: int = 0
    events_updated: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CalendarDiff:
    """
    Difference between local and remote calendars.

    Detects changes made by external coach in Intervals.icu.

    Attributes:
        added_remote: Workouts added by coach (not in local)
        removed_remote: Workouts removed by coach (in local but not in remote)
        moved_remote: Workouts moved to different dates by coach
        modified_remote: Workouts modified by coach (TSS/description changes)

    Examples:
        >>> diff = CalendarDiff(
        ...     added_remote=[],
        ...     removed_remote=[{"date": date(2026, 1, 22), "name": "Tempo"}],
        ...     moved_remote=[],
        ...     modified_remote=[]
        ... )
        >>> diff.has_changes()
        True
    """

    added_remote: list[dict] = field(default_factory=list)
    removed_remote: list[dict] = field(default_factory=list)
    moved_remote: list[dict] = field(default_factory=list)
    modified_remote: list[dict] = field(default_factory=list)

    def has_changes(self) -> bool:
        """
        Check if any changes detected.

        Returns:
            True if any changes detected, False otherwise
        """
        return bool(
            self.added_remote or self.removed_remote or self.moved_remote or self.modified_remote
        )


@dataclass
class SyncStatusReport:
    """
    Synchronization status report.

    Attributes:
        last_check: Timestamp of last sync check
        is_synced: Whether local and remote are in sync
        diff: Detailed differences (if not synced)
        warnings: List of warning messages

    Examples:
        >>> diff = CalendarDiff(removed_remote=[{"date": "2026-01-22", "name": "Tempo"}])
        >>> report = SyncStatusReport(
        ...     last_check=datetime.now(),
        ...     is_synced=False,
        ...     diff=diff,
        ...     warnings=["Coach a supprimé des workouts"]
        ... )
        >>> print(report.summary())
        ⚠️ Changements détectés:
          • 1 workouts supprimés par coach
    """

    last_check: datetime
    is_synced: bool
    diff: CalendarDiff
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """
        Generate human-readable summary.

        Returns:
            Formatted summary string
        """
        if self.is_synced:
            return "✅ Calendrier synchronisé"

        lines = ["⚠️ Changements détectés:"]
        if self.diff.removed_remote:
            lines.append(f"  • {len(self.diff.removed_remote)} workouts supprimés par coach")
        if self.diff.added_remote:
            lines.append(f"  • {len(self.diff.added_remote)} workouts ajoutés par coach")
        if self.diff.modified_remote:
            lines.append(f"  • {len(self.diff.modified_remote)} workouts modifiés par coach")
        if self.diff.moved_remote:
            lines.append(f"  • {len(self.diff.moved_remote)} workouts déplacés par coach")

        return "\n".join(lines)


def calculate_description_diff(local_desc: str, remote_desc: str) -> str:
    """
    Calculate textual diff between local and remote descriptions.

    Args:
        local_desc: Local workout description
        remote_desc: Remote workout description from Intervals.icu

    Returns:
        Formatted diff string showing changes

    Examples:
        >>> local = "Main set 3x10m 90%"
        >>> remote = "Main set 4x10m 90%"
        >>> diff = calculate_description_diff(local, remote)
        >>> print(diff)
        - Main set 3x10m 90%
        + Main set 4x10m 90%
    """
    local_lines = local_desc.splitlines(keepends=True)
    remote_lines = remote_desc.splitlines(keepends=True)

    diff_lines = list(
        unified_diff(
            local_lines,
            remote_lines,
            fromfile="local",
            tofile="remote (Intervals.icu)",
            lineterm="",
        )
    )

    if not diff_lines:
        return "No differences"

    # Skip header lines (---/+++) and return clean diff
    return "\n".join(line.rstrip() for line in diff_lines[3:] if line.strip())


class IntervalsSync:
    """
    Bidirectional sync manager for Intervals.icu.

    Detects external coach modifications and provides sync status.
    Delegates push/pull to existing tools to avoid duplication:
    - Push: Use upload-workouts CLI command
    - Pull: Use intervals_client from config

    Use Cases:
        - Detect when coach deletes a workout
        - Detect when coach moves a workout to different date
        - Detect when coach modifies TSS or description
        - Monitor sync status between local plan and remote calendar

    Examples:
        >>> from cyclisme_training_logs.planning.calendar import TrainingCalendar
        >>> from cyclisme_training_logs.config.athlete_profile import AthleteProfile
        >>>
        >>> # Create local calendar
        >>> profile = AthleteProfile.from_env()
        >>> calendar = TrainingCalendar(year=2026, athlete_profile=profile)
        >>>
        >>> # Check sync status
        >>> sync = IntervalsSync()
        >>> status = sync.get_sync_status(
        ...     calendar=calendar,
        ...     start_date=date(2026, 1, 20),
        ...     end_date=date(2026, 1, 26)
        ... )
        >>>
        >>> if not status.is_synced:
        ...     print(status.summary())
        ...     # ⚠️ Changements détectés:
        ...     #   • 1 workouts supprimés par coach

    Notes:
        For pushing local plans to Intervals.icu, use the upload-workouts CLI:
            poetry run upload-workouts --week-id S077 --file S077_workouts.txt

        This class focuses on READ operations and change detection only.
    """

    def __init__(self):
        """Initialize sync manager with Intervals.icu client."""
        self.client = create_intervals_client()

    def fetch_remote_calendar(self, start_date: date, end_date: date) -> dict[date, dict]:
        """
        Fetch calendar from Intervals.icu (read-only).

        Delegates to intervals_client.get_events().

        Args:
            start_date: Start of period to fetch
            end_date: End of period to fetch

        Returns:
            Dict mapping dates to event data:
            {
                date(2026, 1, 20): {
                    "id": 89100872,
                    "name": "S077-01-END-Endurance",
                    "planned_tss": 80,
                    "description": "...",
                    "category": "WORKOUT",
                },
                ...
            }

        Examples:
            >>> sync = IntervalsSync()
            >>> calendar = sync.fetch_remote_calendar(
            ...     start_date=date(2026, 1, 20),
            ...     end_date=date(2026, 1, 26)
            ... )
            >>> len(calendar)  # Number of workouts
            3
        """
        events = self.client.get_events(
            oldest=start_date.strftime("%Y-%m-%d"),
            newest=end_date.strftime("%Y-%m-%d"),
        )

        # Transform to dict by date
        calendar = {}
        for event in events:
            if event.get("category") == "WORKOUT":
                # Parse date from start_date_local (ISO format)
                date_str = event.get("start_date_local", "")[:10]  # YYYY-MM-DD
                try:
                    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    calendar[event_date] = event
                except ValueError:
                    # Skip events with invalid dates
                    continue

        return calendar

    def detect_changes(
        self, local_calendar: TrainingCalendar, start_date: date, end_date: date
    ) -> CalendarDiff:
        """
        Detect changes between local and remote calendars.

        Identifies workouts added, removed, moved, or modified by external coach.

        Args:
            local_calendar: Local TrainingCalendar instance
            start_date: Start of period to check
            end_date: End of period to check

        Returns:
            CalendarDiff with detected changes

        Examples:
            >>> from cyclisme_training_logs.planning.calendar import TrainingCalendar
            >>> from cyclisme_training_logs.config.athlete_profile import AthleteProfile
            >>>
            >>> profile = AthleteProfile.from_env()
            >>> calendar = TrainingCalendar(year=2026, athlete_profile=profile)
            >>>
            >>> sync = IntervalsSync()
            >>> diff = sync.detect_changes(calendar, start_date, end_date)
            >>>
            >>> if diff.removed_remote:
            ...     print(f"⚠️ Coach deleted {len(diff.removed_remote)} workouts:")
            ...     for workout in diff.removed_remote:
            ...         print(f"  • {workout['date']}: {workout['name']}")
        """
        # Fetch remote state
        remote = self.fetch_remote_calendar(start_date, end_date)

        # Build local state dict
        local = {}
        current = start_date
        while current <= end_date:
            if current in local_calendar.sessions:
                session = local_calendar.sessions[current]
                # Get description if available (from planned session metadata)
                description = getattr(session, "description", "")
                local[current] = {
                    "date": current,
                    "name": f"{current}-{session.workout_type.value.upper()}",
                    "planned_tss": session.planned_tss,
                    "type": session.workout_type.value,
                    "duration_min": session.duration_min,
                    "description": description,
                    "description_hash": (
                        calculate_description_hash(description) if description else None
                    ),
                }
            current += timedelta(days=1)

        # Detect differences
        added_remote = []
        removed_remote = []
        modified_remote = []

        # Check removed (in local but not in remote)
        for local_date, local_workout in local.items():
            if local_date not in remote:
                removed_remote.append(local_workout)

        # Check added (in remote but not in local)
        for remote_date, remote_workout in remote.items():
            if remote_date not in local:
                added_remote.append(
                    {
                        "date": remote_date,
                        "name": remote_workout.get("name", "Unnamed"),
                        "id": remote_workout.get("id"),
                    }
                )

        # Check modified (same date but different content)
        for check_date in set(local.keys()) & set(remote.keys()):
            local_workout = local[check_date]
            remote_workout = remote[check_date]

            # Calculate remote description hash
            remote_description = remote_workout.get("description", "")
            remote_hash = (
                calculate_description_hash(remote_description) if remote_description else None
            )
            local_hash = local_workout.get("description_hash")

            # Detect modifications via hash comparison
            content_modified = False
            if local_hash and remote_hash and local_hash != remote_hash:
                content_modified = True
            elif not local_hash:
                # Fallback: Check if workout TYPE changed (e.g., TEMPO → RECOVERY)
                local_type = local_workout.get("type", "").upper()
                remote_name = remote_workout.get("name", "").upper()

                # Map workout types to common name patterns
                type_patterns = {
                    "ENDURANCE": ["END", "ENDURANCE"],
                    "TEMPO": ["TEMPO", "SWEET", "SST"],
                    "THRESHOLD": ["THRESHOLD", "FTP", "SEUIL"],
                    "VO2MAX": ["VO2", "INTERVALLE"],
                    "RECOVERY": ["RECOVERY", "REC", "RECUPERATION"],
                    "REST": ["REST", "REPOS"],
                }

                # Check if remote name contains expected type pattern
                expected_patterns = type_patterns.get(local_type.upper(), [local_type])
                type_matches = any(pattern in remote_name for pattern in expected_patterns)
                if not type_matches:
                    content_modified = True

            if content_modified:
                # Calculate textual diff
                local_desc = local_workout.get("description", "N/A")
                textual_diff = calculate_description_diff(local_desc, remote_description)

                modified_remote.append(
                    {
                        "date": check_date,
                        "local": local_workout,
                        "remote": {
                            "name": remote_workout.get("name"),
                            "id": remote_workout.get("id"),
                            "description": remote_description,
                            "description_hash": remote_hash,
                        },
                        "diff": textual_diff,
                    }
                )

        # Moved detection: TODO (complex pattern matching)
        # For now, empty (Phase 2 feature)
        moved_remote = []

        return CalendarDiff(
            added_remote=added_remote,
            removed_remote=removed_remote,
            moved_remote=moved_remote,
            modified_remote=modified_remote,
        )

    def get_sync_status(
        self, calendar: TrainingCalendar, start_date: date, end_date: date
    ) -> SyncStatusReport:
        """
        Get synchronization status between local and remote.

        Detects if external coach has made changes to calendar.

        Args:
            calendar: Local TrainingCalendar instance
            start_date: Start of period to check
            end_date: End of period to check

        Returns:
            SyncStatusReport with detailed status and warnings

        Examples:
            >>> from cyclisme_training_logs.planning.calendar import TrainingCalendar
            >>> from cyclisme_training_logs.config.athlete_profile import AthleteProfile
            >>>
            >>> profile = AthleteProfile.from_env()
            >>> calendar = TrainingCalendar(year=2026, athlete_profile=profile)
            >>>
            >>> sync = IntervalsSync()
            >>> status = sync.get_sync_status(calendar, start_date, end_date)
            >>>
            >>> print(status.summary())
            # ⚠️ Changements détectés:
            #   • 1 workouts supprimés par coach
            #   • 2 workouts modifiés par coach
            >>>
            >>> if status.warnings:
            ...     for warning in status.warnings:
            ...         print(f"⚠️ {warning}")
        """
        diff = self.detect_changes(calendar, start_date, end_date)

        warnings = []
        if diff.removed_remote:
            warnings.append(
                f"Coach a supprimé {len(diff.removed_remote)} workout(s) - vérifier calendrier"
            )
        if diff.modified_remote:
            warnings.append(
                f"Coach a modifié {len(diff.modified_remote)} workout(s) - TSS plan possiblement impacté"
            )
        if diff.added_remote:
            warnings.append(
                f"Coach a ajouté {len(diff.added_remote)} workout(s) - plan local incomplet"
            )

        return SyncStatusReport(
            last_check=datetime.now(),
            is_synced=not diff.has_changes(),
            diff=diff,
            warnings=warnings,
        )
