"""DataMixin for WeeklyAggregator — API and filesystem data fetching."""

import json
import logging
from collections import Counter
from datetime import timedelta
from typing import Any

logger = logging.getLogger(__name__)


class DataMixin:
    """Data fetching methods for weekly aggregation."""

    def _fetch_weekly_activities(self) -> list[dict[str, Any]]:
        """
        Fetch activités semaine depuis Intervals.icu avec détails complets.

        Enrichit chaque activité avec données détaillées (TSS, IF, NP) via
        appel get_activity() individuel, car get_activities() ne retourne
        que les champs basiques.

        Returns:
            Liste activités enrichies avec training_load, if, normalized_power.
        """
        if not self.api:
            logger.warning("No API available, returning empty activities")
            return []

        start_str = self.start_date.isoformat()
        end_str = self.end_date.isoformat()

        # Fetch liste activités (données basiques)
        activities_basic = self.api.get_activities(oldest=start_str, newest=end_str)

        logger.info(f"Found {len(activities_basic)} activities, fetching detailed data...")

        # Enrichir chaque activité avec détails complets
        activities_detailed = []
        for activity in activities_basic:
            activity_id = activity.get("id")
            if not activity_id:
                logger.warning(f"Activity without ID: {activity.get('name', 'Unknown')}")
                activities_detailed.append(activity)
                continue

            try:
                # Fetch détails complets (inclut TSS, IF, NP)
                detailed = self.api.get_activity(activity_id)
                activities_detailed.append(detailed)
                logger.debug(
                    f"Enriched activity {activity_id}: TSS={detailed.get('training_load', 0)}, IF={detailed.get('if', 0)}"
                )
            except Exception as e:
                logger.warning(f"Failed to fetch details for activity {activity_id}: {e}")
                # Fallback to basic data
                activities_detailed.append(activity)

        # Trier par date
        activities_detailed.sort(key=lambda x: x.get("start_date_local", ""))

        logger.info(f"Successfully enriched {len(activities_detailed)} activities with TSS/IF data")
        return activities_detailed

    def _fetch_daily_metrics(self) -> list[dict[str, Any]]:
        """Fetch métriques quotidiennes (CTL/ATL/TSB)."""
        if not self.api:
            return []

        metrics = []
        current_date = self.start_date

        while current_date <= self.end_date:
            try:
                date_str = current_date.isoformat()
                wellness_data = self.api.get_wellness(oldest=date_str, newest=date_str)

                # API returns list - convert to dict keyed by date
                if isinstance(wellness_data, list) and len(wellness_data) > 0:
                    wellness = wellness_data[0]  # Take first element
                elif isinstance(wellness_data, dict):
                    wellness = wellness_data
                else:
                    wellness = None

                if wellness:
                    from magma_cycling.utils.metrics import (
                        extract_wellness_metrics,
                    )

                    wellness_metrics = extract_wellness_metrics(wellness)
                    ramp_rate = wellness.get("ramp_rate")

                    metrics.append(
                        {
                            "date": date_str,
                            "ctl": wellness_metrics["ctl"],
                            "atl": wellness_metrics["atl"],
                            "tsb": wellness_metrics["tsb"],
                            "ramp_rate": ramp_rate if ramp_rate is not None else 0,
                        }
                    )
            except Exception as e:
                logger.warning(f"No metrics for {current_date}: {e}")

            current_date += timedelta(days=1)

        return metrics

    def _load_weekly_feedback(self) -> dict[str, Any]:
        """Load feedback athlète pour la semaine."""
        feedback_dir = self.data_dir / "feedback"

        if not feedback_dir.exists():
            return {}

        feedback = {}
        for feedback_file in feedback_dir.glob("*.json"):
            try:
                with open(feedback_file, encoding="utf-8") as f:
                    data = json.load(f)
                    activity_id = feedback_file.stem
                    feedback[activity_id] = data
            except Exception as e:
                logger.warning(f"Failed to load {feedback_file}: {e}")

        return feedback

    def _fetch_wellness_data(self) -> dict[str, Any]:
        """Fetch données wellness (sommeil, poids, HRV)."""
        if not self.api:
            return {}

        wellness = {}
        current_date = self.start_date

        while current_date <= self.end_date:
            try:
                date_str = current_date.isoformat()
                wellness_data = self.api.get_wellness(oldest=date_str, newest=date_str)

                # API returns list - convert to dict keyed by date
                if isinstance(wellness_data, list) and len(wellness_data) > 0:
                    data = wellness_data[0]  # Take first element
                elif isinstance(wellness_data, dict):
                    data = wellness_data
                else:
                    data = None

                if data:
                    wellness[date_str] = {
                        "sleep_quality": data.get("sleepQuality", 0),
                        "sleep_hours": (
                            data.get("sleepSecs", 0) / 3600 if data.get("sleepSecs") else 0
                        ),
                        "weight": data.get("weight", 0),
                        "hrv": data.get("hrvSDNN", 0),
                        "resting_hr": data.get("restingHR", 0),
                    }
            except Exception as e:
                logger.warning(f"No wellness for {current_date}: {e}")

            current_date += timedelta(days=1)

        return wellness

    def _fetch_planned_workouts(self) -> list[dict[str, Any]]:
        """Fetch workouts planifiés pour compliance check."""
        if not self.api:
            return []

        start_str = self.start_date.isoformat()
        end_str = self.end_date.isoformat()

        try:
            planned = self.api.get_events(oldest=start_str, newest=end_str)
            # Filter for WORKOUT category
            if planned:
                planned = [e for e in planned if e.get("category") == "WORKOUT"]
            return planned
        except Exception as e:
            logger.warning(f"Failed to fetch planned workouts: {e}")
            return []

    def _extract_gear_metrics(self, activity_id: str) -> dict[str, Any] | None:
        """
        Extract gear metrics (Di2) from activity streams.

        Extrait métriques de changements de vitesse depuis les streams.

        Args:
            activity_id: Activity ID

        Returns:
            Dict avec métriques gear ou None si pas disponibles:
            - shifts: Nombre total de changements
            - front_shifts: Changements plateau avant
            - rear_shifts: Changements pignon arrière
            - avg_gear_ratio: Ratio moyen
            - gear_ratio_distribution: Distribution des ratios utilisés
        """
        if not self.api:
            return None

        try:
            # Fetch streams
            streams = self.api.get_activity_streams(activity_id)

            # Find gear streams
            front_gear_stream = next((s for s in streams if s.get("type") == "FrontGear"), None)
            rear_gear_stream = next((s for s in streams if s.get("type") == "RearGear"), None)
            gear_ratio_stream = next((s for s in streams if s.get("type") == "GearRatio"), None)

            if not (front_gear_stream and rear_gear_stream):
                return None  # Pas de données gear disponibles

            front_data = front_gear_stream.get("data", [])
            rear_data = rear_gear_stream.get("data", [])
            ratio_data = gear_ratio_stream.get("data", []) if gear_ratio_stream else []

            # Remove None values and calculate metrics
            front_clean = [f for f in front_data if f is not None]
            rear_clean = [r for r in rear_data if r is not None]
            ratio_clean = [r for r in ratio_data if r is not None]

            if not front_clean or not rear_clean:
                return None

            # Count shifts (changes in gear values)
            front_shifts = sum(
                1 for i in range(1, len(front_clean)) if front_clean[i] != front_clean[i - 1]
            )
            rear_shifts = sum(
                1 for i in range(1, len(rear_clean)) if rear_clean[i] != rear_clean[i - 1]
            )

            total_shifts = front_shifts + rear_shifts

            # Calculate average gear ratio
            avg_ratio = sum(ratio_clean) / len(ratio_clean) if ratio_clean else None

            # Build gear ratio distribution (top 5 most used)
            ratio_counts = Counter(round(r, 2) for r in ratio_clean if r)
            top_ratios = dict(ratio_counts.most_common(5))

            return {
                "shifts": total_shifts,
                "front_shifts": front_shifts,
                "rear_shifts": rear_shifts,
                "avg_gear_ratio": round(avg_ratio, 2) if avg_ratio else None,
                "gear_ratio_distribution": top_ratios,
            }

        except Exception as e:
            logger.warning(f"Error extracting gear metrics for {activity_id}: {e}")
            return None
