"""Body measurements mixin for WithingsClient."""

import logging
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class MeasurementsMixin:
    """Weight, body composition, blood pressure, and training readiness."""

    def get_measurements(
        self,
        start_date: date,
        end_date: date | None = None,
        measure_types: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Get weight and body composition measurements.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive, default: today)
            measure_types: List of measurement type IDs (default: [1] for weight)
                          1=Weight, 4=Height, 5=Fat Free Mass, 6=Fat Ratio, 8=Fat Mass Weight,
                          76=Muscle Mass, 77=Hydration, 88=Bone Mass

        Returns:
            List of measurements as dictionaries

        Example:
            >>> measurements = client.get_measurements(
            ...     start_date=date(2026, 2, 1),
            ...     end_date=date(2026, 2, 22),
            ...     measure_types=[1, 6, 8]  # Weight, fat ratio, fat mass
            ... )
        """
        if end_date is None:
            end_date = date.today()

        if measure_types is None:
            measure_types = [1]  # Default to weight only

        startdate = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        enddate = int(datetime.combine(end_date, datetime.max.time()).timestamp())

        params = {
            "action": "getmeas",
            "startdate": startdate,
            "enddate": enddate,
            "meastypes": ",".join(map(str, measure_types)),
        }

        body = self._make_request("measure", params)

        measurements = []
        measuregrps = body.get("measuregrps", [])

        for grp in measuregrps:
            measure_date_ts = grp.get("date")
            if not measure_date_ts:
                continue

            measure_dt = datetime.fromtimestamp(measure_date_ts)
            measure_date_obj = measure_dt.date()

            # Parse measures in this group
            weight_kg = None
            fat_mass_kg = None
            muscle_mass_kg = None
            bone_mass_kg = None
            body_water_kg = None

            for measure in grp.get("measures", []):
                measure_type = measure.get("type")
                value = measure.get("value")
                unit = measure.get("unit", 0)

                if value is None:
                    continue

                # Calculate actual value: value * 10^unit
                actual_value = value * (10**unit)

                if measure_type == 1:  # Weight
                    weight_kg = actual_value
                elif measure_type == 8:  # Fat Mass
                    fat_mass_kg = actual_value
                elif measure_type == 76:  # Muscle Mass
                    muscle_mass_kg = actual_value
                elif measure_type == 77:  # Hydration (Body Water)
                    body_water_kg = actual_value
                elif measure_type == 88:  # Bone Mass
                    bone_mass_kg = actual_value

            if weight_kg is not None:
                measurements.append(
                    {
                        "date": measure_date_obj.isoformat(),
                        "datetime": measure_dt.isoformat(),
                        "weight_kg": round(weight_kg, 2),
                        "fat_mass_kg": round(fat_mass_kg, 2) if fat_mass_kg else None,
                        "muscle_mass_kg": round(muscle_mass_kg, 2) if muscle_mass_kg else None,
                        "bone_mass_kg": round(bone_mass_kg, 2) if bone_mass_kg else None,
                        "body_water_kg": round(body_water_kg, 2) if body_water_kg else None,
                    }
                )

        logger.info(f"Retrieved {len(measurements)} weight measurements")
        return measurements

    def get_latest_weight(self) -> dict[str, Any] | None:
        """Get most recent weight measurement.

        Returns:
            Latest weight measurement dict, or None if not available

        Example:
            >>> weight = client.get_latest_weight()
            >>> if weight:
            ...     print(f"Current weight: {weight['weight_kg']} kg")
        """
        # Get measurements from last 30 days
        end = date.today()
        start = end - timedelta(days=30)

        measurements = self.get_measurements(start, end, measure_types=[1, 6, 8, 76, 77, 88])

        if not measurements:
            return None

        # Return most recent
        return max(measurements, key=lambda m: m["datetime"])

    def get_blood_pressure(
        self,
        start_date: date,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get blood pressure measurements.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive, default: today)

        Returns:
            List of blood pressure measurements as dictionaries.
            Each dict contains: date, datetime, systolic, diastolic, heart_pulse (optional).

        Example:
            >>> bp_data = client.get_blood_pressure(date(2026, 2, 1), date(2026, 2, 28))
            >>> for bp in bp_data:
            ...     print(f"{bp['date']}: {bp['systolic']}/{bp['diastolic']}")
        """
        if end_date is None:
            end_date = date.today()

        startdate = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        enddate = int(datetime.combine(end_date, datetime.max.time()).timestamp())

        params = {
            "action": "getmeas",
            "startdate": startdate,
            "enddate": enddate,
            "meastypes": "9,10,11",  # 9=diastolic, 10=systolic, 11=heart_pulse
        }

        body = self._make_request("measure", params)

        measurements = []
        measuregrps = body.get("measuregrps", [])

        for grp in measuregrps:
            measure_date_ts = grp.get("date")
            if not measure_date_ts:
                continue

            measure_dt = datetime.fromtimestamp(measure_date_ts)
            measure_date_obj = measure_dt.date()

            systolic = None
            diastolic = None
            heart_pulse = None

            for measure in grp.get("measures", []):
                measure_type = measure.get("type")
                value = measure.get("value")
                unit = measure.get("unit", 0)

                if value is None:
                    continue

                actual_value = value * (10**unit)

                if measure_type == 9:  # Diastolic
                    diastolic = round(actual_value)
                elif measure_type == 10:  # Systolic
                    systolic = round(actual_value)
                elif measure_type == 11:  # Heart Pulse
                    heart_pulse = round(actual_value)

            # Only include if both systolic and diastolic are present
            if systolic is not None and diastolic is not None:
                measurements.append(
                    {
                        "date": measure_date_obj.isoformat(),
                        "datetime": measure_dt.isoformat(),
                        "systolic": systolic,
                        "diastolic": diastolic,
                        "heart_pulse": heart_pulse,
                    }
                )

        logger.info(f"Retrieved {len(measurements)} blood pressure measurements")
        return measurements

    def evaluate_training_readiness(self, sleep_data: dict[str, Any]) -> dict[str, Any]:
        """Evaluate training readiness based on sleep quality.

        Based on sleep science and training adaptation principles:
        - Minimum 7h sleep for intense training
        - Deep sleep >= 60 min for recovery
        - Sleep score >= 75 for optimal performance

        Args:
            sleep_data: Sleep session dict from get_sleep() or get_last_night_sleep()

        Returns:
            Training readiness evaluation dict

        Example:
            >>> sleep = client.get_last_night_sleep()
            >>> readiness = client.evaluate_training_readiness(sleep)
            >>> print(readiness['recommended_intensity'])
            'all_systems_go'
        """
        sleep_hours = sleep_data.get("total_sleep_hours", 0)
        sleep_score = sleep_data.get("sleep_score")
        deep_sleep_min = sleep_data.get("deep_sleep_minutes", 0) or 0

        veto_reasons = []
        recommendations = []

        # Check sleep duration
        sufficient_duration = sleep_hours >= 7.0
        if not sufficient_duration:
            veto_reasons.append(f"Sommeil insuffisant ({sleep_hours:.1f}h < 7h)")

        # Check deep sleep
        deep_sleep_ok = deep_sleep_min >= 60
        if not deep_sleep_ok and deep_sleep_min > 0:
            veto_reasons.append(f"Sommeil profond insuffisant ({deep_sleep_min:.0f}min < 60min)")

        # Check sleep score
        good_score = sleep_score is not None and sleep_score >= 75

        # Determine recommended intensity
        if sleep_hours < 5.5:
            recommended_intensity = "recovery_only"
            recommendations.append("Récupération uniquement - sommeil très insuffisant")
        elif not sufficient_duration:
            recommended_intensity = "endurance_max"
            recommendations.append("Zone endurance maximum - éviter haute intensité")
        elif not good_score:
            recommended_intensity = "moderate"
            recommendations.append("Intensité modérée - qualité sommeil sous-optimale")
        else:
            recommended_intensity = "all_systems_go"
            if deep_sleep_ok:
                recommendations.append("Conditions optimales pour séance intensive")
            else:
                recommendations.append("Bonne condition, attention à la récupération")

        ready_for_intense = sufficient_duration and good_score and deep_sleep_ok

        return {
            "date": sleep_data.get("date"),
            "sleep_hours": sleep_hours,
            "sleep_score": sleep_score,
            "deep_sleep_minutes": deep_sleep_min,
            "ready_for_intense": ready_for_intense,
            "recommended_intensity": recommended_intensity,
            "veto_reasons": veto_reasons,
            "recommendations": recommendations,
            "sufficient_duration": sufficient_duration,
            "deep_sleep_ok": deep_sleep_ok,
        }
