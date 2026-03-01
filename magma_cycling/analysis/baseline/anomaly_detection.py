"""Anomaly detection methods for BaselineAnalyzer."""

from typing import Any


class AnomalyDetectionMixin:
    """Détection activités non-planifiées."""

    def detect_unsolicited_activities(self) -> list[dict[str, Any]]:
        """Detect activities without paired workout event (unsolicited/spontaneous).

        Unsolicited activities are activities completed that don't match any
        planned workout in the calendar. These can be:
        - Spontaneous bonus workouts
        - Outdoor rides replacing planned indoor sessions (not marked as replaced)
        - Extra activities added on rest days

        Returns:
            List of unsolicited activity dicts with metadata
        """
        print("\n📥 Detecting unsolicited activities...")

        if not self.activities_data:
            print("   ⚠️  No activities data loaded")
            return []

        # Get all paired activity IDs from WORKOUT events
        # Empty events_data is valid - means no paired workouts exist
        workout_events = (
            [e for e in self.events_data if e.get("category") == "WORKOUT"]
            if self.events_data
            else []
        )
        paired_activity_ids = {
            e.get("paired_activity_id") for e in workout_events if e.get("paired_activity_id")
        }

        # Find activities NOT in paired set
        unsolicited = []
        for activity in self.activities_data:
            activity_id = activity.get("id")
            if activity_id and activity_id not in paired_activity_ids:
                date = activity.get("start_date_local", "").split("T")[0]
                unsolicited.append(
                    {
                        "date": date,
                        "activity_id": activity_id,
                        "name": activity.get("name", "Unnamed"),
                        "type": activity.get("type", "Unknown"),
                        "tss": activity.get("icu_training_load") or 0,
                        "duration_seconds": activity.get("moving_time") or 0,
                        "distance_meters": activity.get("distance") or 0,
                        "avg_power": activity.get("average_watts"),
                        "normalized_power": activity.get("normalized_power"),
                    }
                )

        # Sort by date
        unsolicited.sort(key=lambda x: x["date"])

        print(f"   ✅ Found {len(unsolicited)} unsolicited activities")
        if unsolicited:
            total_tss = sum(a["tss"] for a in unsolicited)
            print(f"   ✅ Total unsolicited TSS: {total_tss:.0f}")

        return unsolicited
