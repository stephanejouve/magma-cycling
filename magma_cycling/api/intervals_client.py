"""
Unified Intervals.icu API client.

Client API unifié pour Intervals.icu.

This module provides a single, canonical implementation of the Intervals.icu API client,
replacing multiple duplicated implementations across the codebase.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)


class IntervalsClient:
    """
    Unified client for Intervals.icu API.

    Client unifié pour l'API Intervals.icu.

    This class provides methods to interact with the Intervals.icu REST API,
    including fetching activities, wellness data, events, and creating workouts.

    Attributes:
        athlete_id: Intervals.icu athlete ID (format: i123456)
        session: Configured requests.Session with authentication

    Example:
        >>> client = IntervalsClient(athlete_id="iXXXXXX", api_key="your_key")
        >>> activities = client.get_activities(oldest="2025-12-22", newest="2025-12-28")
        >>> wellness = client.get_wellness(oldest="2025-12-22", newest="2025-12-28")
    """

    BASE_URL = "https://intervals.icu/api/v1"

    def __init__(self, athlete_id: str, api_key: str):
        """
        Initialize the Intervals.icu API client.

        Args:
            athlete_id: Intervals.icu athlete ID (format: i123456)
            api_key: API key for authentication

        Raises:
            ValueError: If athlete_id or api_key is empty.
        """
        if not athlete_id or not api_key:
            raise ValueError("athlete_id and api_key are required")

        self.athlete_id = athlete_id
        self.session = requests.Session()
        self.session.auth = ("API_KEY", api_key)
        self.session.headers.update({"Content-Type": "application/json"})

    def get_athlete(self) -> dict[str, Any]:
        """
        Get athlete profile information.

        Récupérer les informations du profil athlète.

        Returns:
            Athlete profile data including name, FTP, weight, etc.

        Raises:
            requests.HTTPError: If API request fails

        Example:
            >>> athlete = client.get_athlete()
            >>> print(f"FTP: {athlete.get('ftp')}")
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}"

        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def update_athlete(self, athlete_data: dict[str, Any]) -> dict[str, Any]:
        """
        Update athlete profile information.

        Mettre à jour les informations du profil athlète.

        Args:
            athlete_data: Dictionary with fields to update (e.g., {"ftp": 223})
                Common fields: ftp, weight, max_hr, resting_hr, fthr, etc.

        Returns:
            Updated athlete profile data

        Raises:
            requests.HTTPError: If API request fails

        Example:
            >>> client.update_athlete({"ftp": 223})
            >>> client.update_athlete({"ftp": 223, "weight": 75})
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}"

        response = self.session.put(url, json=athlete_data)
        response.raise_for_status()
        logger.info(f"Updated athlete profile: {athlete_data}")
        return response.json()

    def get_activities(
        self, oldest: str | None = None, newest: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get activities (workouts) for a date range.

        Récupérer les activités (séances) pour une période.

        Args:
            oldest: Start date in YYYY-MM-DD format (optional)
            newest: End date in YYYY-MM-DD format (optional)

        Returns:
            List of activities with basic metrics (TSS, duration, etc.)

        Raises:
            requests.HTTPError: If API request fails

        Example:
            >>> activities = client.get_activities(
            ...     oldest="2025-12-22",
            ...     newest="2025-12-28"
            ... )
            >>> print(f"Found {len(activities)} activities")
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/activities"

        params = {}
        if oldest:
            params["oldest"] = oldest
        if newest:
            params["newest"] = newest

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_activity(self, activity_id: str) -> dict[str, Any]:
        """
        Get complete details for a single activity.

        Récupérer les détails complets d'une activité.

        Args:
            activity_id: Activity ID (format: i107424849 or numeric string)

        Returns:
            Complete activity data including power curves, intervals, etc.

        Raises:
            requests.HTTPError: If API request fails or activity not found

        Example:
            >>> activity = client.get_activity("i107424849")
            >>> print(f"TSS: {activity.get('icu_training_load')}")
        """
        url = f"{self.BASE_URL}/activity/{activity_id}"

        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_activity_streams(self, activity_id: str) -> list[dict[str, Any]]:
        """
        Get time-series streams for a single activity.

        Récupérer les données temporelles (streams) d'une activité.

        Args:
            activity_id: Activity ID (format: i107424849 or numeric string)

        Returns:
            List of stream dicts, each containing 'type' and 'data' fields.
            Available streams: watts, heartrate, cadence, distance, altitude,
            velocity_smooth, torque, left_right_balance, FrontGear, RearGear,
            GearRatio, etc.

        Raises:
            requests.HTTPError: If API request fails or activity not found

        Example:
            >>> streams = client.get_activity_streams("i107424849")
            >>> for stream in streams:
            ...     print(f"{stream['type']}: {len(stream['data'])} points")
        """
        url = f"{self.BASE_URL}/activity/{activity_id}/streams"

        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_activity_intervals(self, activity_id: str) -> list[dict[str, Any]]:
        """
        Get interval/lap data for a single activity.

        Récupérer les données d'intervalles/laps d'une activité.

        Args:
            activity_id: Activity ID (format: i107424849 or numeric string)

        Returns:
            List of interval dicts with aggregated metrics (avg power, HR, cadence, etc.)

        Raises:
            requests.HTTPError: If API request fails or activity not found

        Example:
            >>> intervals = client.get_activity_intervals("i107424849")
            >>> for iv in intervals:
            ...     print(f"{iv.get('type')}: {iv.get('average_watts')}W")
        """
        url = f"{self.BASE_URL}/activity/{activity_id}/intervals"

        response = self.session.get(url)
        response.raise_for_status()
        data = response.json()
        # API returns {"id": ..., "icu_intervals": [...], "icu_groups": [...]}
        return data.get("icu_intervals", [])

    def put_activity_intervals(
        self, activity_id: str, intervals: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Replace interval/lap data for an activity on Intervals.icu.

        Sends custom interval boundaries; Intervals.icu recalculates all metrics
        (watts, HR, cadence, torque, L/R balance, TSS) per block.

        Args:
            activity_id: Activity ID (format: i107424849 or numeric string)
            intervals: List of interval dicts with keys: type, label,
                start_index, end_index

        Returns:
            Updated interval data from Intervals.icu

        Raises:
            requests.HTTPError: If API request fails or activity not found
        """
        url = f"{self.BASE_URL}/activity/{activity_id}/intervals"

        response = self.session.put(url, json=intervals)
        response.raise_for_status()
        return response.json()

    def get_wellness(
        self, oldest: str | None = None, newest: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get wellness data (CTL, ATL, TSB, weight, sleep, etc.).

        Récupérer les données wellness (CTL, ATL, TSB, poids, sommeil, etc.).

        Args:
            oldest: Start date in YYYY-MM-DD format (optional)
            newest: End date in YYYY-MM-DD format (optional)

        Returns:
            List of wellness data, one entry per day

        Raises:
            requests.HTTPError: If API request fails

        Note:
            Returns a list of dicts, not a dict keyed by date.
            Each dict has an 'id' field with the date.

        Example:
            >>> wellness = client.get_wellness(
            ...     oldest="2025-12-22",
            ...     newest="2025-12-28"
            ... )
            >>> for day in wellness:
            ...     print(f"{day['id']}: CTL={day.get('ctl')}")
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/wellness"

        params = {}
        if oldest:
            params["oldest"] = oldest
        if newest:
            params["newest"] = newest

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_events(
        self, oldest: str | None = None, newest: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get calendar events (planned workouts, notes, etc.).

        Récupérer les événements du calendrier (workouts planifiés, notes, etc.).

        Args:
            oldest: Start date in YYYY-MM-DD format (optional)
            newest: End date in YYYY-MM-DD format (optional)

        Returns:
            List of events (category can be WORKOUT, NOTE, etc.)

        Raises:
            requests.HTTPError: If API request fails

        Example:
            >>> events = client.get_events(
            ...     oldest="2025-12-29",
            ...     newest="2026-01-04"
            ... )
            >>> workouts = [e for e in events if e.get('category') == 'WORKOUT']
        """
        url = f"{self.BASE_URL}/athlete/{self.athlete_id}/events"

        params = {}
        if oldest:
            params["oldest"] = oldest
        if newest:
            params["newest"] = newest

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_planned_workout(
        self, activity_id: str, activity_date: datetime
    ) -> dict[str, Any] | None:
        """
        Find the planned workout associated with a completed activity.

        Trouver le workout planifié associé à une activité réalisée.

        Searches for events in a ±2 day window around the activity date,
        looking for an event with matching paired_activity_id.

        Args:
            activity_id: Activity ID (format: i107424849)
            activity_date: Date of the completed activity

        Returns:
            Event dict if found, None otherwise

        Example:
            >>> from datetime import datetime
            >>> date = datetime(2025, 12, 30)
            >>> planned = client.get_planned_workout("i107424849", date)
            >>> if planned:
            ...     print(f"Planned workout: {planned.get('name')}")
        """
        # Search in a ±2 day window around the activity

        oldest = (activity_date - timedelta(days=2)).strftime("%Y-%m-%d")
        newest = (activity_date + timedelta(days=2)).strftime("%Y-%m-%d")

        events = self.get_events(oldest=oldest, newest=newest)

        # Find event with matching paired_activity_id
        for event in events:
            if event.get("paired_activity_id") == activity_id:
                return event

        return None

    def create_event(self, event_data: dict[str, Any]) -> dict[str, Any] | None:
        r"""
        Create a calendar event (planned workout, note, etc.).

        Créer un événement du calendrier (workout planifié, note, etc.).

        Args:
            event_data: Event data dict containing:
                - category: "WORKOUT", "NOTE", etc.
                - name: Event name
                - description: Content (Intervals.icu format for workouts)
                - start_date_local: Date in YYYY-MM-DD format
                - (optional) other fields like workout_doc, etc.

        Returns:
            Created event with assigned ID, or None if creation failed

        Raises:
            requests.HTTPError: If API request fails

        Example:
            >>> event = {
            ...     "category": "WORKOUT",
            ...     "name": "S074-01-END-EnduranceBase",
            ...     "description": "10min @ 60% FTP\\n45min @ 70% FTP\\n5min @ 50% FTP",
            ...     "start_date_local": "2025-12-29"
            ... }
            >>> created = client.create_event(event)
            >>> if created:
            ...     print(f"Created event ID: {created.get('id')}")
        """
        try:
            url = f"{self.BASE_URL}/athlete/{self.athlete_id}/events"
            response = self.session.post(url, json=event_data)
            response.raise_for_status()

            created_event = response.json()
            logger.info(f"Created event: {created_event.get('id')} - {created_event.get('name')}")
            return created_event

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error creating event: {e}")
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Error detail: {error_detail}")
                except Exception:
                    logger.error(f"Response: {e.response.text}")
            logger.error(f"Event data: {event_data}")
            return None

        except Exception as e:
            logger.error(f"Error creating event: {e}")
            logger.error(f"Event data: {event_data}")
            return None

    def delete_event(self, event_id: int) -> bool:
        """Delete a calendar event.

        Args:
            event_id: Event ID to delete

        Returns:
            True if deletion successful, False otherwise

        Example:
            >>> success = client.delete_event(event_id=12345)
            >>> if success:
            ...     print("Event deleted")
        """
        try:
            url = f"{self.BASE_URL}/athlete/{self.athlete_id}/events/{event_id}"
            response = self.session.delete(url)
            response.raise_for_status()
            logger.info(f"Deleted event ID: {event_id}")
            return True

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error deleting event {event_id}: {e}")
            if e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False

        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}")
            return False

    def update_event(self, event_id: int, event_data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an existing calendar event.

        Args:
            event_id: Event ID to update
            event_data: Updated event data (partial update supported)

        Returns:
            Updated event data, or None if update failed

        Example:
            >>> updated = client.update_event(
            ...     event_id=12345,
            ...     event_data={"name": "S074-05-CANCELLED", "description": "Cancelled due to fatigue"}
            ... )
        """
        try:
            url = f"{self.BASE_URL}/athlete/{self.athlete_id}/events/{event_id}"
            response = self.session.put(url, json=event_data)
            response.raise_for_status()

            updated_event = response.json()
            logger.info(f"Updated event ID: {event_id}")
            return updated_event

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error updating event {event_id}: {e}")
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Error detail: {error_detail}")
                except Exception:
                    logger.error(f"Response: {e.response.text}")
            return None

        except Exception as e:
            logger.error(f"Error updating event {event_id}: {e}")
            return None
