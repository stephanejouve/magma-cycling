"""ActivityDetectionMixin — detect and deduplicate completed activities."""

from datetime import date, datetime


class ActivityDetectionMixin:
    """Mixin for activity detection and deduplication logic."""

    def _detect_duplicate_activities(self, activities: list[dict]) -> list[dict]:
        """
        Detect and remove duplicate activities based on start_time.

        When multiple imports create different activity IDs for the same physical
        session (e.g., Wahoo + Zwift), keep only the best one.

        Tolerance: ±30 seconds on start_time (human starts instruments sequentially)

        Priority:
        1. Activity with paired_event_id (linked to planned workout)
        2. Source priority: Zwift > others
        3. Highest TSS (usually more accurate)

        Args:
            activities: List of activities to deduplicate

        Returns:
            Deduplicated list of activities
        """
        if not activities:
            return []

        # Parse start times
        activities_with_time = []
        for activity in activities:
            if activity is None:
                continue
            start_str = activity.get("start_date_local", "")
            if start_str:
                try:
                    # Parse ISO format: 2026-02-17T17:30:00
                    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    activities_with_time.append((start_dt, activity))
                except (ValueError, AttributeError):
                    # If parsing fails, keep activity (no duplicate detection)
                    activities_with_time.append((None, activity))

        # Sort by start time
        activities_with_time.sort(key=lambda x: x[0] if x[0] else datetime.min)

        # Group by proximity (±30 seconds tolerance)
        groups = []
        current_group = []
        last_time = None

        for start_dt, activity in activities_with_time:
            if start_dt is None:
                # Can't group, add as single
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([activity])
                last_time = None
                continue

            if last_time is None or abs((start_dt - last_time).total_seconds()) <= 30:
                # Within tolerance, add to current group
                current_group.append(activity)
                last_time = start_dt
            else:
                # Too far, start new group
                if current_group:
                    groups.append(current_group)
                current_group = [activity]
                last_time = start_dt

        # Don't forget last group
        if current_group:
            groups.append(current_group)

        # Detect and resolve duplicates
        deduplicated = []
        for group in groups:
            if len(group) == 1:
                # No duplicate
                deduplicated.append(group[0])
            else:
                # Multiple activities within ±30s = DUPLICATE
                ids = [a["id"] for a in group]
                start_times = [a.get("start_date_local", "")[:19] for a in group]
                print(f"  ⚠️  Doublon détecté ({len(group)} activités, ±30s)")
                print(f"     IDs: {', '.join(str(i) for i in ids)}")
                print(f"     Start times: {', '.join(start_times)}")

                # Apply priority rules
                # Priority 1: paired_event_id present
                with_event = [a for a in group if a.get("paired_event_id")]
                if with_event:
                    selected = with_event[0]
                    print(
                        f"     → Sélection: {selected['id']} (paired_event_id: {selected.get('paired_event_id')})"
                    )
                else:
                    # Priority 2: Source = Zwift
                    zwift = [a for a in group if "zwift" in str(a.get("source", "")).lower()]
                    if zwift:
                        selected = zwift[0]
                        print(f"     → Sélection: {selected['id']} (source Zwift)")
                    else:
                        # Priority 3: Highest TSS
                        selected = max(group, key=lambda a: a.get("icu_training_load", 0))
                        print(
                            f"     → Sélection: {selected['id']} (TSS le plus élevé: {selected.get('icu_training_load')})"
                        )

                deduplicated.append(selected)

                # Log ignored duplicates
                ignored = [a for a in group if a != selected]
                for ign in ignored:
                    print(
                        f"     ✗ Ignoré: {ign['id']} (TSS: {ign.get('icu_training_load')}, source: {ign.get('source', 'N/A')})"
                    )

        return deduplicated

    def check_activities(self, check_date: date) -> tuple[list[dict], list[dict]]:
        """
        Check for new completed activities on given date.

        Retrieves both:
        - Planned activities (paired with WORKOUT events)
        - Unplanned activities (no event association)

        Args:
            check_date: Date to check

        Returns:
            Tuple of (new_activities, completed_activities):
            - new_activities: List of new activities to analyze
            - completed_activities: All completed activities on this date
        """
        # Suppress output if not in verbose mode (for MCP usage)
        if not self.verbose:
            import contextlib
            import os

            with open(os.devnull, "w") as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    return self._check_activities_internal(check_date)
        else:
            return self._check_activities_internal(check_date)

    def _check_activities_internal(self, check_date: date) -> tuple[list[dict], list[dict]]:
        """Internal implementation with prints."""
        print(f"\n🔍 Vérification activités du {check_date.strftime('%d/%m/%Y')}...")

        # Get all activities for the date (includes both planned and unplanned)
        all_activities = self.client.get_activities(
            oldest=check_date.isoformat(), newest=check_date.isoformat()
        )

        # Filter out activities that are ignored or incomplete
        completed_activities = [
            act
            for act in all_activities
            if act is not None  # Skip None entries
            and not act.get("icu_ignore_time", False)  # Not ignored
            and act.get("type") in ["Ride", "VirtualRide"]  # Cycling activities only
        ]

        # Detect and remove duplicates (same start_time)
        completed_activities = self._detect_duplicate_activities(completed_activities)

        # Filter new activities (not yet analyzed)
        # Use activity ID (not event ID) for tracking
        new_activities = []
        planned_count = 0
        unplanned_count = 0

        for activity in completed_activities:
            # Convert activity ID to comparable format (tracker uses event IDs from old format)
            # For new format, we use the event ID if available, otherwise the activity ID
            tracking_id = activity.get("paired_event_id") or activity["id"]

            # Check if already analyzed
            if self.tracker.is_analyzed(tracking_id, check_date):
                continue

            new_activities.append(activity)

            # Count planned vs unplanned
            if activity.get("paired_event_id"):
                planned_count += 1
            else:
                unplanned_count += 1

        print(f"  ✅ {len(completed_activities)} activité(s) complétée(s)")
        print(f"  📋 {planned_count} planifiée(s), {unplanned_count} non planifiée(s)")
        print(f"  🆕 {len(new_activities)} nouvelle(s) activité(s) à analyser")

        # Return both new activities (for analysis) and all completed activities (for status updates)
        return new_activities, completed_activities
