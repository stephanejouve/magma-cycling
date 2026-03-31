"""SessionUpdatesMixin — session matching and status updates via Control Tower."""

import re
from datetime import date, datetime, timedelta

from magma_cycling.config.athlete_profile import AthleteProfile
from magma_cycling.planning.calendar import TrainingCalendar, WorkoutType
from magma_cycling.planning.control_tower import planning_tower
from magma_cycling.planning.intervals_sync import IntervalsSync


class SessionUpdatesMixin:
    """Mixin for session ID extraction, activity matching, and status updates."""

    def check_planning_changes(self, week_id: str, start_date, end_date) -> dict:
        """
        Check for planning modifications by external coach.

        Args:
            week_id: Week identifier (e.g., "S077")
            start_date: Week start date
            end_date: Week end date

        Returns:
            Dict with sync status and diff
        """
        import json

        from pydantic import ValidationError

        print(f"\n🔍 Vérification modifications planning {week_id}...")

        try:
            # READ-ONLY ACCESS via Control Tower
            plan = planning_tower.read_week(week_id)
        except FileNotFoundError:
            print(f"  ⚠️  Planning {week_id} introuvable")
            return {"status": None, "diff": None}
        except (ValidationError, json.JSONDecodeError) as e:
            print(f"  ⚠️  Erreur chargement planning {week_id}: {e}")
            return {"status": None, "diff": None}

        # Create minimal calendar for sync check
        profile = AthleteProfile.from_env()
        calendar = TrainingCalendar(year=start_date.year, athlete_profile=profile)

        # Add planned sessions (simplified, no full description loading)
        workout_type_map = {
            "END": WorkoutType.ENDURANCE,
            "INT": WorkoutType.TEMPO,
            "PDC": WorkoutType.RECOVERY,
            "REC": WorkoutType.RECOVERY,
        }

        for session in plan.planned_sessions:
            session_date = session.session_date

            # Skip rest days
            if session_date.weekday() == 6:  # Sunday
                continue

            cal_session = calendar.add_session(
                session_date=session_date,
                workout_type=workout_type_map.get(session.session_type, WorkoutType.ENDURANCE),
                planned_tss=session.tss_planned,
                duration_min=session.duration_min,
            )

            # Add description hash for content change detection
            cal_session.description = session.description or ""
            cal_session.description_hash = session.description_hash

        # Check sync
        sync = IntervalsSync()
        status = sync.get_sync_status(calendar=calendar, start_date=start_date, end_date=end_date)

        if status.diff.has_changes():
            print(f"  ⚠️  {status.summary()}")
        else:
            print("  ✅ Aucune modification détectée")

        return {"status": status, "diff": status.diff}

    def _extract_session_id(self, activity_name: str) -> tuple[str, str] | None:
        """
        Extract week_id and session_id from activity name.

        Args:
            activity_name: Activity name (e.g., "S079-02-INT-SweetSpotModere-V001")

        Returns:
            Tuple of (week_id, session_id) or None if no match
            Example: ("S079", "S079-02")
        """
        # Pattern: S079-02-INT-SweetSpotModere-V001
        pattern = r"^(S\d{3})-(\d{2}[a-z]?)"
        match = re.match(pattern, activity_name)

        if match:
            week_id = match.group(1)
            session_num = match.group(2)
            session_id = f"{week_id}-{session_num}"
            return week_id, session_id

        return None

    def _find_matching_activity(
        self, workout: dict, activities: list[dict], tolerance_hours: int = 24
    ) -> dict | None:
        """
        Find activity matching a planned workout using intelligent matching.

        Matching criteria (in order):
        1. paired_event_id matches workout id (explicit pairing)
        2. Session code in activity name (e.g., "S077-03")
        3. Temporal tolerance (±24h by default)

        Args:
            workout: Planned workout from events API
            activities: List of completed activities
            tolerance_hours: Time tolerance in hours

        Returns:
            Matching activity or None
        """
        workout_id = workout.get("id")
        workout_date = datetime.fromisoformat(workout["start_date_local"].replace("Z", "+00:00"))
        workout_name = workout.get("name", "").upper()

        # Extract session code (e.g., "S077-03")
        workout_code = None
        if "-" in workout_name:
            parts = workout_name.split("-")
            if len(parts) >= 2:
                workout_code = f"{parts[0]}-{parts[1]}"  # "S077-03"

        for activity in activities:
            if activity is None:
                continue

            # Method 1: Explicit pairing via paired_event_id
            if activity.get("paired_event_id") == workout_id:
                return activity

            # Method 2: Session code matching + temporal tolerance
            if workout_code:
                activity_name = activity.get("name", "").upper()
                if "start_date_local" not in activity:
                    continue
                activity_date = datetime.fromisoformat(
                    activity["start_date_local"].replace("Z", "+00:00")
                )

                # Check temporal tolerance
                time_diff = abs((activity_date - workout_date).total_seconds() / 3600)
                if time_diff > tolerance_hours:
                    continue

                # Check if session code is in activity name
                if workout_code in activity_name:
                    return activity

        return None

    def update_completed_sessions(self, activities: list[dict]) -> dict:
        """
        Automatically update session status to 'completed' in local planning JSON.

        Enhanced with intelligent matching:
        1. Load planned workouts (events) from Intervals.icu
        2. Match activities to workouts using intelligent criteria
        3. Update session status from 'uploaded'/'pending' to 'completed'
        4. Save via Control Tower (automatic backup + audit)

        Args:
            activities: List of completed activities from Intervals.icu

        Returns:
            Dict mapping activity_id -> session_id for successfully matched activities
        """
        if not activities:
            return {}

        print("\n🔄 Mise à jour automatique des statuts de sessions...")

        # Determine date range from activities
        if not activities:
            return {}

        activity_dates = [
            datetime.fromisoformat(a["start_date_local"].replace("Z", "+00:00")).date()
            for a in activities
            if a is not None and "start_date_local" in a
        ]

        # If no valid dates found, return empty mapping
        if not activity_dates:
            return {}

        oldest = min(activity_dates)
        newest = max(activity_dates)

        # Expand range by 1 day for tolerance
        oldest = (oldest - timedelta(days=1)).isoformat()
        newest = (newest + timedelta(days=1)).isoformat()

        # Get planned workouts (events) from Intervals.icu
        try:
            events = self.client.get_events(oldest=oldest, newest=newest)
            workouts = [e for e in events if e.get("category") == "WORKOUT"]
            print(f"  ℹ️  {len(workouts)} workout(s) planifié(s) trouvé(s) sur Intervals.icu")
        except Exception as e:
            print(f"  ⚠️  Erreur récupération workouts planifiés: {e}")
            return {}

        # Group matched sessions by week_id for efficient batch updates
        activities_by_week = {}
        activity_to_session_map = {}  # Track activity_id -> session_id mapping

        for workout in workouts:
            workout_name = workout.get("name", "")

            # Extract session info from workout name
            session_info = self._extract_session_id(workout_name)
            if not session_info:
                continue

            week_id, session_id = session_info

            # Find matching activity using intelligent matching
            matched_activity = self._find_matching_activity(workout, activities)

            if matched_activity:
                activity_name = matched_activity.get("name", "")
                activity_id = matched_activity.get("id")

                if week_id not in activities_by_week:
                    activities_by_week[week_id] = []

                activities_by_week[week_id].append((session_id, activity_name))

                # Store mapping for return value
                if activity_id:
                    activity_to_session_map[activity_id] = session_id

        # Update each week via Control Tower (one permission/backup per week)
        for week_id, session_updates in activities_by_week.items():
            try:
                # MODIFY VIA CONTROL TOWER (automatic backup + audit)
                session_ids = ", ".join([sid for sid, _ in session_updates])
                with planning_tower.modify_week(
                    week_id,
                    requesting_script="daily-sync",
                    reason=f"Mark sessions completed from Intervals.icu: {session_ids}",
                ) as plan:
                    # Update all sessions for this week
                    for session_id, activity_name in session_updates:
                        session_found = False

                        for session in plan.planned_sessions:
                            if session.session_id == session_id:
                                # Only update if not already completed
                                if session.status != "completed":
                                    session.status = "completed"
                                    print(f"  ✅ {session_id} marqué comme 'completed'")
                                else:
                                    print(f"  ℹ️  {session_id} déjà marqué 'completed'")
                                session_found = True
                                break

                        if not session_found:
                            print(f"  ⚠️  Session {session_id} introuvable dans {week_id}")

                    # Auto-saved by Control Tower with backup + audit log

            except FileNotFoundError:
                print(f"  ⚠️  Planning {week_id} introuvable")
            except Exception as e:
                print(f"  ⚠️  Erreur mise à jour planning {week_id}: {e}")

        print("  ✅ Mise à jour automatique terminée")

        return activity_to_session_map

    def auto_complete_rest_sessions(self, check_date: date) -> list[str]:
        """Auto-complete rest sessions (TSS=0, duration=0) whose date has passed.

        Rest days are accomplished by definition — no activity needed.

        Args:
            check_date: Current date. Sessions before this date are eligible.

        Returns:
            List of session IDs that were auto-completed.
        """
        from magma_cycling.daily_sync import calculate_current_week_info

        completed_ids: list[str] = []

        # Determine current and previous week
        current_week_id, _ = calculate_current_week_info(check_date)
        current_num = int(current_week_id[1:])
        week_ids = [current_week_id]
        if current_num > 1:
            week_ids.append(f"S{current_num - 1:03d}")

        for week_id in week_ids:
            try:
                plan = planning_tower.read_week(week_id)
            except FileNotFoundError:
                continue

            sessions_to_complete = [
                s
                for s in plan.planned_sessions
                if s.tss_planned == 0
                and s.duration_min == 0
                and s.session_date < check_date
                and s.status == "planned"
            ]

            if not sessions_to_complete:
                continue

            session_ids = [s.session_id for s in sessions_to_complete]
            with planning_tower.modify_week(
                week_id,
                requesting_script="daily-sync",
                reason=f"Auto-complete rest sessions: {', '.join(session_ids)}",
            ) as mutable_plan:
                for session in mutable_plan.planned_sessions:
                    if session.session_id in session_ids:
                        session.status = "completed"
                        completed_ids.append(session.session_id)
                        print(f"  ✅ {session.session_id} (repos) → completed")

        return completed_ids
