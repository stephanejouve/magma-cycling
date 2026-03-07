"""Data formatting methods for PromptGenerator."""

from datetime import datetime


class DataFormattingMixin:
    """Structured data formatting for prompt generation."""

    def format_activity_data(self, activity):
        """Format les données d'activité pour le prompt."""
        date = datetime.fromisoformat(activity["start_date_local"].replace("Z", "+00:00"))

        # Vérifier si l'activité vient de Strava
        is_strava = activity.get("source") == "STRAVA"

        # Détecter l'environnement indoor/outdoor
        activity_type = activity.get("type", "")
        is_indoor = activity_type == "VirtualRide"

        data = {
            "id": activity.get("id", "Non spécifié"),
            "name": activity.get("name", "Séance"),
            "type": activity.get("type", "Cyclisme"),
            "date": date.strftime("%d/%m/%Y"),
            "date_iso": date.strftime("%Y-%m-%d"),
            "duration_min": activity.get("moving_time", 0) // 60,
            "tss": activity.get("icu_training_load", 0),
            "intensity": activity.get("icu_intensity", 0) / 100.0,
            "avg_power": activity.get("icu_average_watts", 0),
            "np": activity.get("icu_weighted_avg_watts", 0),
            "avg_cadence": activity.get("average_cadence", 0),
            "avg_hr": activity.get("average_heartrate", 0),
            "max_hr": activity.get("max_heartrate", 0),
            "decoupling": activity.get("decoupling", None),
            "avg_temp": activity.get("average_temp"),  # Temperature in °C
            "min_temp": activity.get("min_temp"),
            "max_temp": activity.get("max_temp"),
            "has_weather": activity.get("has_weather", False),
            "description": activity.get("description", ""),
            "tags": activity.get("tags", []),
            "feel": activity.get("feel"),  # 1-5 scale Intervals.icu (1=Excellent, 5=Poor)
            "is_strava": is_strava,
            "source": activity.get("source", "Unknown"),
            "environment": "indoor" if is_indoor else "outdoor",
            "is_indoor": is_indoor,
        }

        return data

    def format_wellness_data(self, wellness):
        """Format les données wellness."""
        if not wellness:
            return {
                "ctl": 0,
                "atl": 0,
                "tsb": 0,
                "weight": 0,
                "sleep_seconds": 0,
                "comments": "",
            }

        from magma_cycling.utils.metrics import extract_wellness_metrics

        metrics = extract_wellness_metrics(wellness)

        return {
            "ctl": metrics["ctl"],
            "atl": metrics["atl"],
            "tsb": metrics["tsb"],
            "weight": wellness.get("weight", 0),
            "sleep_seconds": wellness.get("sleepSecs", 0),
            "sleep_quality": wellness.get("sleepQuality", 0),
            "comments": wellness.get("comments", ""),
        }

    def format_planned_workout(self, planned_event):
        """Format le workout planifié pour le prompt.

        Args:
            planned_event: L'événement contenant le workout planifié

        Returns:
            Dict avec les informations formatées ou None.
        """
        if not planned_event or not planned_event.get("workout_doc"):
            return None

        workout_doc = planned_event["workout_doc"]

        # Extraire les données principales
        formatted = {
            "name": planned_event.get("name", "Workout planifié"),
            "description": planned_event.get("description", ""),
            "duration_min": workout_doc.get("duration", 0) // 60,
            "tss_planned": planned_event.get("icu_training_load", 0),
            "avg_watts_planned": workout_doc.get("average_watts", 0),
            "np_planned": workout_doc.get("normalized_power", 0),
            "intensity_planned": (
                planned_event.get("icu_intensity", 0) / 100.0
                if planned_event.get("icu_intensity")
                else 0
            ),
            "joules": workout_doc.get("joules", 0),
        }

        # Formater la structure des intervalles
        steps = workout_doc.get("steps", [])
        intervals = []

        for _i, step in enumerate(steps):
            if "reps" in step:
                # C'est un bloc d'intervalles répétés
                reps = step["reps"]
                sub_steps = step.get("steps", [])
                interval_desc = []
                for sub in sub_steps:
                    power_info = self._format_power(sub.get("power", {}))
                    cadence = sub.get("cadence", {}).get("value", 0)
                    duration_min = sub.get("duration", 0) / 60
                    interval_desc.append(f"{duration_min:.0f}min @ {power_info} / {cadence}rpm")
                intervals.append(f"{reps}x ({' → '.join(interval_desc)})")
            else:
                # Step simple
                power_info = self._format_power(step.get("power", {}))
                cadence = step.get("cadence", {}).get("value", 0)
                duration_min = step.get("duration", 0) / 60
                step_type = ""
                if step.get("warmup"):
                    step_type = "[Warmup] "
                elif step.get("cooldown"):
                    step_type = "[Cooldown] "
                intervals.append(f"{step_type}{duration_min:.0f}min @ {power_info} / {cadence}rpm")

        formatted["intervals"] = intervals

        # Répartition des zones (time in zones)
        zone_times = workout_doc.get("zoneTimes", [])
        zones_str = []
        for zone in zone_times:
            if zone.get("secs", 0) > 0 and not zone.get("gap"):  # Ignorer Sweet Spot (gap=true)
                zone_name = zone.get("name", zone.get("id", "Z?"))
                zone_min = zone["secs"] / 60
                zones_str.append(f"{zone_name}: {zone_min:.0f}min")

        formatted["zone_distribution"] = ", ".join(zones_str) if zones_str else "N/A"

        return formatted

    def format_athlete_feedback(self, feedback):
        """Format le feedback pour inclusion dans le prompt."""
        if not feedback:
            return None

        parts = []

        if feedback.get("rpe"):
            parts.append(f"**RPE** : {feedback['rpe']}/10")

        if feedback.get("ressenti_general"):
            parts.append(f"**Ressenti** : {feedback['ressenti_general']}")

        if feedback.get("difficultes"):
            parts.append(f"**Difficultés** :\n{feedback['difficultes']}")

        if feedback.get("points_positifs"):
            parts.append(f"**Points positifs** :\n{feedback['points_positifs']}")

        if feedback.get("contexte"):
            parts.append(f"**Contexte** : {feedback['contexte']}")

        if feedback.get("sensations_physiques"):
            sensations = ", ".join(feedback["sensations_physiques"])
            parts.append(f"**Sensations physiques** : {sensations}")

        if feedback.get("notes_libres"):
            parts.append(f"**Notes libres** :\n{feedback['notes_libres']}")

        return "\n\n".join(parts) if parts else None
