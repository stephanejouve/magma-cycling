"""
Intervals.icu bidirectional sync for training plans and calendars.

This module provides bidirectional synchronization between local training plans/
calendars and the Intervals.icu platform.

Author: Claude Code (Sprint R3 Completion)
Created: 2026-01-18
Status: Production
Priority: P1
Version: 1.0.0

Metadata:
    Created: 2026-01-18
    Author: Cyclisme Training Logs Team
    Category: PLANNING
    Status: Production
    Priority: P1
    Version: 1.0.0
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from cyclisme_training_logs.config import create_intervals_client
from cyclisme_training_logs.planning.calendar import TrainingCalendar
from cyclisme_training_logs.planning.planning_manager import TrainingPlan

logger = logging.getLogger(__name__)


@dataclass
class SyncStatus:
    """
    Status of sync operation with Intervals.icu.

    Attributes:
        success: Whether sync operation succeeded
        events_created: Number of events created in Intervals.icu
        events_updated: Number of events updated in Intervals.icu
        events_deleted: Number of events deleted from Intervals.icu
        errors: List of error messages encountered
        warnings: List of warning messages
    """

    success: bool
    events_created: int = 0
    events_updated: int = 0
    events_deleted: int = 0
    errors: list[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all status fields
        """
        return {
            "success": self.success,
            "events_created": self.events_created,
            "events_updated": self.events_updated,
            "events_deleted": self.events_deleted,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class IntervalsSync:
    """
    Manager for bidirectional sync with Intervals.icu.

    This class handles synchronization of training plans and calendars between
    the local system and Intervals.icu platform, including:
    - Pushing training plans to Intervals.icu calendar
    - Syncing calendar events bidirectionally
    - Updating individual workout sessions
    - Fetching sync status and validation

    Attributes:
        client: IntervalsClient instance for API communication

    Example:
        >>> from cyclisme_training_logs.planning import IntervalsSync, PlanningManager
        >>> manager = PlanningManager()
        >>> plan = manager.create_training_plan(
        ...     start_date=date(2026, 1, 20),
        ...     end_date=date(2026, 2, 16),
        ...     objectives=[]
        ... )
        >>> sync = IntervalsSync()
        >>> status = sync.push_plan_to_intervals(plan)
        >>> print(f"Created {status.events_created} events")
    """

    def __init__(self):
        """
        Initialize IntervalsSync with configured API client.

        Raises:
            ValueError: If Intervals.icu credentials are not configured
        """
        self.client = create_intervals_client()
        logger.info("IntervalsSync initialized")

    def push_plan_to_intervals(self, plan: TrainingPlan) -> SyncStatus:
        """
        Push training plan to Intervals.icu calendar.

        Creates calendar events in Intervals.icu for all objectives/deadlines
        in the training plan. Each objective becomes a WORKOUT or NOTE event
        depending on its type.

        Args:
            plan: TrainingPlan to push to Intervals.icu

        Returns:
            SyncStatus with operation results

        Example:
            >>> manager = PlanningManager()
            >>> plan = manager.create_training_plan(
            ...     start_date=date(2026, 1, 20),
            ...     end_date=date(2026, 2, 16),
            ...     objectives=[]
            ... )
            >>> manager.add_deadline(
            ...     plan_id=plan.name,
            ...     date=date(2026, 2, 2),
            ...     event_name="Gran Fondo Test Event",
            ...     priority="high"
            ... )
            >>> sync = IntervalsSync()
            >>> status = sync.push_plan_to_intervals(plan)
            >>> assert status.success
            >>> assert status.events_created >= 1
        """
        status = SyncStatus(success=False)

        try:
            logger.info(f"Pushing plan {plan.name} to Intervals.icu")

            # Push each objective as a calendar event
            for objective in plan.objectives:
                event_data = {
                    "category": "NOTE",  # Use NOTE for objectives/milestones
                    "name": objective.name,
                    "description": (
                        f"Training objective: {objective.objective_type.value}\n"
                        f"Priority: {objective.priority.value}\n"
                        f"Target: {objective.target_value or 'N/A'}"
                    ),
                    "start_date_local": objective.target_date.strftime("%Y-%m-%d"),
                }

                # If it's an event-type objective, use WORKOUT category
                if objective.objective_type.value == "event":
                    event_data["category"] = "WORKOUT"
                    event_data["description"] = f"Event: {objective.name}\n{objective.notes or ''}"

                created = self.client.create_event(event_data)
                if created:
                    status.events_created += 1
                    logger.info(f"Created event for objective: {objective.name}")
                else:
                    status.errors.append(f"Failed to create event for: {objective.name}")
                    logger.warning(f"Failed to create event for: {objective.name}")

            # Mark success if at least one event was created
            status.success = status.events_created > 0

            logger.info(
                f"Push complete: {status.events_created} events created, "
                f"{len(status.errors)} errors"
            )

        except Exception as e:
            status.errors.append(f"Push failed: {str(e)}")
            logger.error(f"Error pushing plan to Intervals.icu: {e}", exc_info=True)

        return status

    def sync_calendar(
        self,
        calendar: TrainingCalendar,
        start_date: date,
        end_date: date,
    ) -> SyncStatus:
        """
        Bidirectional sync of calendar with Intervals.icu.

        Synchronizes training sessions between local TrainingCalendar and
        Intervals.icu, handling both directions:
        - Local → Intervals: Push new/updated sessions
        - Intervals → Local: Import completed activities

        Args:
            calendar: TrainingCalendar to sync
            start_date: Start date for sync window
            end_date: End date for sync window

        Returns:
            SyncStatus with sync results

        Example:
            >>> calendar = TrainingCalendar(year=2026, rest_days=[6])
            >>> calendar.add_session(
            ...     date=date(2026, 1, 20),
            ...     workout_type=WorkoutType.ENDURANCE,
            ...     planned_tss=100,
            ...     name="S003-01-END"
            ... )
            >>> sync = IntervalsSync()
            >>> status = sync.sync_calendar(
            ...     calendar=calendar,
            ...     start_date=date(2026, 1, 20),
            ...     end_date=date(2026, 1, 26)
            ... )
            >>> assert status.success
        """
        status = SyncStatus(success=False)

        try:
            logger.info(f"Syncing calendar from {start_date} to {end_date}")

            # Fetch existing events from Intervals.icu
            oldest_str = start_date.strftime("%Y-%m-%d")
            newest_str = end_date.strftime("%Y-%m-%d")
            intervals_events = self.client.get_events(oldest=oldest_str, newest=newest_str)

            # Build map of existing events by date
            existing_events: dict[str, dict] = {}
            for event in intervals_events:
                if event.get("category") == "WORKOUT":
                    event_date = event.get("start_date_local")
                    existing_events[event_date] = event

            # Push local sessions to Intervals.icu
            for session_date in calendar.sessions:
                if start_date <= session_date <= end_date:
                    session = calendar.sessions[session_date]
                    session_date_str = session_date.strftime("%Y-%m-%d")

                    # Generate session name from date and type
                    session_name = f"{session_date_str}-{session.workout_type.value.upper()}"

                    event_data = {
                        "category": "WORKOUT",
                        "name": session_name,
                        "description": (
                            f"Type: {session.workout_type.value}\n"
                            f"Planned TSS: {session.planned_tss}\n"
                            f"Duration: {session.duration_min}min\n"
                            f"Intensity: {session.intensity_pct}% FTP\n"
                            f"{session.notes or ''}"
                        ),
                        "start_date_local": session_date_str,
                    }

                    if session_date_str in existing_events:
                        # Update existing event
                        event_id = existing_events[session_date_str]["id"]
                        updated = self.client.update_event(event_id, event_data)
                        if updated:
                            status.events_updated += 1
                            logger.info(f"Updated event: {session_name}")
                        else:
                            status.errors.append(f"Failed to update: {session_name}")
                    else:
                        # Create new event
                        created = self.client.create_event(event_data)
                        if created:
                            status.events_created += 1
                            logger.info(f"Created event: {session_name}")
                        else:
                            status.errors.append(f"Failed to create: {session_name}")

            # Fetch completed activities from Intervals.icu and update calendar
            activities = self.client.get_activities(oldest=oldest_str, newest=newest_str)
            for activity in activities:
                activity_date_str = activity.get("start_date_local", "")[:10]
                try:
                    activity_date = datetime.strptime(activity_date_str, "%Y-%m-%d").date()
                    if activity_date in calendar.sessions:
                        session = calendar.sessions[activity_date]
                        # Update actual TSS from activity
                        actual_tss = activity.get("icu_training_load")
                        if actual_tss and session.actual_tss != actual_tss:
                            session.actual_tss = actual_tss
                            logger.info(f"Updated actual TSS for {activity_date}: {actual_tss}")
                except (ValueError, AttributeError) as e:
                    status.warnings.append(f"Could not parse activity date: {activity_date_str}")
                    logger.warning(f"Could not parse activity date {activity_date_str}: {e}")

            status.success = True
            logger.info(
                f"Sync complete: {status.events_created} created, "
                f"{status.events_updated} updated, {len(status.errors)} errors"
            )

        except Exception as e:
            status.errors.append(f"Sync failed: {str(e)}")
            logger.error(f"Error syncing calendar: {e}", exc_info=True)

        return status

    def update_workout_intervals(
        self,
        workout_date: date,
        workout_data: dict[str, Any],
    ) -> SyncStatus:
        """
        Update a specific workout in Intervals.icu.

        Updates or creates a single workout event in Intervals.icu calendar.
        If a workout exists on the given date, it will be updated; otherwise
        a new workout will be created.

        Args:
            workout_date: Date of the workout to update
            workout_data: Workout data dict containing:
                - name: Workout name
                - description: Workout description/intervals
                - planned_tss: (optional) Planned TSS
                - workout_type: (optional) Workout type

        Returns:
            SyncStatus with update results

        Example:
            >>> sync = IntervalsSync()
            >>> status = sync.update_workout_intervals(
            ...     workout_date=date(2026, 1, 20),
            ...     workout_data={
            ...         "name": "S003-01-END-EnduranceBase",
            ...         "description": "60min @ 70% FTP",
            ...         "planned_tss": 100
            ...     }
            ... )
            >>> assert status.success
        """
        status = SyncStatus(success=False)

        try:
            workout_date_str = workout_date.strftime("%Y-%m-%d")
            logger.info(f"Updating workout on {workout_date_str}")

            # Check if workout already exists on this date
            events = self.client.get_events(oldest=workout_date_str, newest=workout_date_str)
            existing_workout = None
            for event in events:
                if event.get("category") == "WORKOUT" and event.get("name") == workout_data.get(
                    "name"
                ):
                    existing_workout = event
                    break

            # Prepare event data
            event_data = {
                "category": "WORKOUT",
                "name": workout_data.get("name", "Workout"),
                "description": workout_data.get("description", ""),
                "start_date_local": workout_date_str,
            }

            # Add planned TSS if provided
            if "planned_tss" in workout_data:
                event_data["description"] += f"\n\nPlanned TSS: {workout_data['planned_tss']}"

            if existing_workout:
                # Update existing workout
                event_id = existing_workout["id"]
                updated = self.client.update_event(event_id, event_data)
                if updated:
                    status.events_updated = 1
                    status.success = True
                    logger.info(f"Updated workout: {workout_data.get('name')}")
                else:
                    status.errors.append(f"Failed to update workout: {workout_data.get('name')}")
            else:
                # Create new workout
                created = self.client.create_event(event_data)
                if created:
                    status.events_created = 1
                    status.success = True
                    logger.info(f"Created workout: {workout_data.get('name')}")
                else:
                    status.errors.append(f"Failed to create workout: {workout_data.get('name')}")

        except Exception as e:
            status.errors.append(f"Update failed: {str(e)}")
            logger.error(f"Error updating workout: {e}", exc_info=True)

        return status

    def fetch_plan_status(
        self,
        plan: TrainingPlan,
    ) -> dict[str, Any]:
        """
        Fetch sync status and completion for a training plan.

        Retrieves the current status of a training plan in Intervals.icu,
        including which objectives have been completed (have paired activities)
        and overall plan progress.

        Args:
            plan: TrainingPlan to check status for

        Returns:
            Dictionary with status information:
                - plan_id: Plan identifier
                - start_date: Plan start date
                - end_date: Plan end date
                - objectives_total: Total number of objectives
                - objectives_completed: Number of completed objectives
                - completion_percent: Percentage complete (0-100)
                - objectives: List of objective status dicts

        Example:
            >>> manager = PlanningManager()
            >>> plan = manager.create_training_plan(
            ...     start_date=date(2026, 1, 20),
            ...     end_date=date(2026, 2, 16),
            ...     objectives=[]
            ... )
            >>> sync = IntervalsSync()
            >>> status = sync.fetch_plan_status(plan)
            >>> print(f"Plan completion: {status['completion_percent']}%")
        """
        try:
            logger.info(f"Fetching status for plan {plan.name}")

            # Fetch events from Intervals.icu for the plan date range
            oldest_str = plan.start_date.strftime("%Y-%m-%d")
            newest_str = plan.end_date.strftime("%Y-%m-%d")
            intervals_events = self.client.get_events(oldest=oldest_str, newest=newest_str)

            # Fetch activities to check for completions
            activities = self.client.get_activities(oldest=oldest_str, newest=newest_str)
            activity_dates = {
                datetime.strptime(a.get("start_date_local", "")[:10], "%Y-%m-%d").date()
                for a in activities
                if a.get("start_date_local")
            }

            # Build objective status list
            objectives_status = []
            completed_count = 0

            for objective in plan.objectives:
                # Check if there's an activity on the objective date
                is_completed = objective.target_date in activity_dates

                # Check if objective exists in Intervals.icu
                in_intervals = any(
                    event.get("name") == objective.name
                    and event.get("start_date_local") == objective.target_date.strftime("%Y-%m-%d")
                    for event in intervals_events
                )

                obj_status = {
                    "name": objective.name,
                    "target_date": objective.target_date.strftime("%Y-%m-%d"),
                    "priority": objective.priority.value,
                    "type": objective.objective_type.value,
                    "completed": is_completed,
                    "in_intervals": in_intervals,
                    "days_remaining": objective.days_remaining(),
                }

                if is_completed:
                    completed_count += 1

                objectives_status.append(obj_status)

            # Calculate completion percentage
            total_objectives = len(plan.objectives)
            completion_percent = (
                int((completed_count / total_objectives) * 100) if total_objectives > 0 else 0
            )

            status = {
                "plan_id": plan.name,
                "start_date": plan.start_date.strftime("%Y-%m-%d"),
                "end_date": plan.end_date.strftime("%Y-%m-%d"),
                "objectives_total": total_objectives,
                "objectives_completed": completed_count,
                "completion_percent": completion_percent,
                "objectives": objectives_status,
            }

            logger.info(
                f"Plan status: {completion_percent}% complete ({completed_count}/{total_objectives})"
            )

            return status

        except Exception as e:
            logger.error(f"Error fetching plan status: {e}", exc_info=True)
            return {
                "plan_id": plan.name,
                "error": str(e),
                "objectives_total": len(plan.objectives),
                "objectives_completed": 0,
                "completion_percent": 0,
            }
