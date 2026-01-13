"""
Weekly workout data aggregator with full TSS/IF enrichment.

Agrégateur hebdomadaire implémentant DataAggregator pour collecter
et traiter données complètes d'une semaine d'entraînement. Enrichit
automatiquement chaque activité avec détails complets (TSS, IF, NP)
via appels API individuels. Collecte 7 workouts, métriques évolution
(CTL/ATL/TSB), feedback athlète, et génère structure pour 6 reports.

Examples:
    Basic weekly aggregation::

        from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator
        from datetime import date

        # Agréger semaine S073
        aggregator = WeeklyAggregator(
            week="S073",
            start_date=date(2025, 1, 6)
        )

        result = aggregator.aggregate()

        if result.success:
            # Données disponibles
            workouts = result.data['processed']['workouts']
            metrics = result.data['processed']['metrics_evolution']
            learnings = result.data['processed']['learnings']

    Advanced with custom config::

        from pathlib import Path

        # Configuration personnalisée
        aggregator = WeeklyAggregator(
            week="S073",
            start_date=date(2025, 1, 6),
            data_dir=Path("~/training-logs"),
            config={
                'include_feedback': True,
                'compute_trends': True,
                'validate_compliance': True
            }
        )

        result = aggregator.aggregate()

        # Accès détaillé
        weekly_data = result.data['processed']
        print(f"Total TSS: {weekly_data['summary']['total_tss']}")
        print(f"Compliance: {weekly_data['compliance']['rate']:.1f}%")

    Integration with analyzer::

        from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer

        # Pipeline complet
        aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))
        aggregation = aggregator.aggregate()

        # Passer au analyzer
        analyzer = WeeklyAnalyzer(aggregation.data['processed'])
        reports = analyzer.generate_all_reports()

Author: Claude Code
Created: 2025-12-26 (Phase 2 - Weekly Analysis System)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P1
    Version: v2
"""

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from cyclisme_training_logs.api.intervals_client import IntervalsClient
from cyclisme_training_logs.config import get_intervals_config
from cyclisme_training_logs.core.data_aggregator import DataAggregator

logger = logging.getLogger(__name__)


class WeeklyAggregator(DataAggregator):
    """
    Agrégateur hebdomadaire pour analyse complète semaine.

    Collecte et agrège :
    - 7 workouts de la semaine (activités Intervals.icu enrichies avec TSS/IF/NP)
    - Métriques évolution quotidienne (CTL/ATL/TSB)
    - Feedback athlète pour chaque séance
    - Données wellness (sommeil, poids, HRV)
    - Compliance planifié vs exécuté

    Enrichissement TSS/IF :
    Appelle get_activity() pour chaque activité afin d'obtenir les valeurs
    complètes de training_load (TSS), intensity factor (IF), et normalized_power (NP).
    L'endpoint get_activities() ne retourne que les données basiques.

    Field Mapping (Intervals.icu API → format interne):
    - icu_training_load → tss (Training Stress Score)
    - icu_intensity (%) → if (Intensity Factor, normalisé 0.0-1.0)
    - icu_weighted_avg_watts → normalized_power (Normalized Power)
    - icu_average_watts → average_power (Average Power)
    - average_hr → average_hr (Average Heart Rate)
    - max_hr → max_hr (Max Heart Rate)

    Note: icu_intensity est en pourcentage (ex: 66.36%) et nécessite
    normalisation (/100) pour obtenir IF standard (ex: 0.66).

    Structure données pour 6 reports :
    1. workout_history - Chronologie détaillée
    2. metrics_evolution - Évolution métriques
    3. training_learnings - Enseignements techniques
    4. protocol_adaptations - Ajustements protocoles
    5. transition - Recommandations semaine suivante
    6. bilan_final - Synthèse globale
    """

    def __init__(
        self,
        week: str,
        start_date: date,
        data_dir: Path | None = None,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize agrégateur weekly.

        Args:
            week: Numéro semaine (ex: S073)
            start_date: Date début semaine (lundi)
            data_dir: Répertoire données (défaut: ~/training-logs)
            config: Configuration optionnelle
        """
        super().__init__(data_dir=data_dir, config=config)

        self.week = week
        self.start_date = start_date
        self.end_date = start_date + timedelta(days=6)
        self.api: IntervalsClient | None

        # Initialize Intervals.icu API with configuration
        try:
            intervals_config = get_intervals_config()
            if intervals_config.is_configured():
                self.api = IntervalsClient(
                    athlete_id=intervals_config.athlete_id, api_key=intervals_config.api_key
                )
                logger.info(
                    f"Intervals.icu API initialized for athlete {intervals_config.athlete_id}"
                )
            else:
                logger.warning(
                    "Intervals.icu API not configured (missing VITE_INTERVALS_ATHLETE_ID or VITE_INTERVALS_API_KEY)"
                )
                self.api = None
        except Exception as e:
            logger.warning(f"Failed to initialize Intervals API: {e}")
            self.api = None

    def collect_raw_data(self) -> dict[str, Any]:
        """
        Collect données brutes hebdomadaires.

        Returns:
            Dict avec :
            - activities: Liste 7 activités
            - metrics_daily: Évolution quotidienne CTL/ATL/TSB
            - feedback: Feedback athlète par séance
            - wellness: Données wellness quotidiennes
            - planned: Workouts planifiés.
        """
        raw_data: dict[str, Any] = {}

        # 1. Activités hebdomadaires
        try:
            logger.info(f"Fetching activities for week {self.week}")
            activities = self._fetch_weekly_activities()
            raw_data["activities"] = activities
            logger.info(f"Collected {len(activities)} activities")
        except Exception as e:
            logger.error(f"Failed to fetch activities: {e}")
            self.errors.append(f"Activities fetch error: {e}")
            raw_data["activities"] = []

        # 2. Métriques quotidiennes
        try:
            logger.info("Fetching daily metrics evolution")
            metrics_daily = self._fetch_daily_metrics()
            raw_data["metrics_daily"] = metrics_daily
        except Exception as e:
            logger.warning(f"Failed to fetch metrics: {e}")
            self.warnings.append(f"Metrics incomplete: {e}")
            raw_data["metrics_daily"] = []

        # 3. Feedback athlète
        try:
            feedback = self._load_weekly_feedback()
            raw_data["feedback"] = feedback
            logger.info(f"Loaded feedback for {len(feedback)} sessions")
        except Exception as e:
            logger.warning(f"No feedback found: {e}")
            self.warnings.append("No athlete feedback available")
            raw_data["feedback"] = {}

        # 4. Wellness data
        try:
            wellness = self._fetch_wellness_data()
            raw_data["wellness"] = wellness
        except Exception as e:
            logger.warning(f"No wellness data: {e}")
            raw_data["wellness"] = {}

        # 5. Planned workouts (compliance)
        if self.config.get("validate_compliance", True):
            try:
                planned = self._fetch_planned_workouts()
                raw_data["planned"] = planned
            except Exception as e:
                logger.warning(f"No planned workouts: {e}")
                raw_data["planned"] = []

        return raw_data

    def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process données brutes hebdomadaires.

        Args:
            raw_data: Données collectées

        Returns:
            Données structurées pour 6 reports.
        """
        processed: dict[str, Any] = {}

        # 1. Summary général
        processed["summary"] = self._compute_weekly_summary(raw_data["activities"])

        # 2. Workouts détaillés (pour workout_history)
        processed["workouts"] = self._process_workouts_detailed(
            raw_data["activities"], raw_data.get("feedback", {})
        )

        # 3. Metrics evolution (pour metrics_evolution)
        processed["metrics_evolution"] = self._process_metrics_evolution(
            raw_data.get("metrics_daily", [])
        )

        # 4. Training learnings (pour training_learnings)
        # Use processed workouts to include gear_metrics and other enriched data
        processed["learnings"] = self._extract_training_learnings(
            processed["workouts"], raw_data.get("feedback", {})
        )

        # 5. Protocol adaptations (pour protocol_adaptations)
        processed["protocol_adaptations"] = self._identify_protocol_changes(
            processed["learnings"], processed["metrics_evolution"]
        )

        # 6. Compliance (pour transition)
        if "planned" in raw_data:
            processed["compliance"] = self._compute_compliance(
                raw_data["activities"], raw_data["planned"]
            )

        # 7. Transition data (pour transition + bilan)
        processed["transition"] = self._prepare_transition_data(
            processed["summary"], processed["metrics_evolution"], processed["learnings"]
        )

        # 8. Wellness insights
        if raw_data.get("wellness"):
            processed["wellness_insights"] = self._analyze_wellness(raw_data["wellness"])

        return processed

    def format_output(self, processed_data: dict[str, Any]) -> str:
        """
        Format sortie markdown (summary).

        Args:
            processed_data: Données traitées

        Returns:
            Markdown summary.
        """
        summary = processed_data.get("summary", {})

        output = [f"# Semaine {self.week} - Summary\n"]

        # Période
        output.append(f"**Période :** {self.start_date} → {self.end_date}\n")

        # Metrics
        output.append("## Métriques Globales\n")
        output.append(f"- **Séances :** {summary.get('total_sessions', 0)}")
        output.append(f"- **TSS total :** {summary.get('total_tss', 0)}")
        output.append(f"- **Durée totale :** {summary.get('total_duration', 0) // 60} min")
        output.append(f"- **TSS moyen :** {summary.get('avg_tss', 0):.1f}")

        # CTL/ATL/TSB
        if "final_metrics" in summary:
            metrics = summary["final_metrics"]
            output.append("\n## Forme")
            output.append(f"- **CTL :** {metrics.get('ctl', 0):.1f}")
            output.append(f"- **ATL :** {metrics.get('atl', 0):.1f}")
            output.append(f"- **TSB :** {metrics.get('tsb', 0):.1f}")

        return "\n".join(output)

    # ==================== MÉTHODES PRIVÉES ====================

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
                    from cyclisme_training_logs.utils.metrics import (
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
                with open(feedback_file) as f:
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

    def _compute_weekly_summary(self, activities: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Calculate summary hebdomadaire.

        Note: Utilise champs Intervals.icu avec préfixe 'icu_':
        - icu_training_load (TSS)
        - icu_intensity (IF en %, nécessite normalisation).
        """
        # Defensive: filter out None values before summing

        summary = {
            "total_sessions": len(activities),
            "total_tss": sum((a.get("icu_training_load") or 0) for a in activities),
            "total_duration": sum((a.get("moving_time") or 0) for a in activities),
            "avg_tss": 0,
            "avg_if": 0,
            "total_distance": sum((a.get("distance") or 0) for a in activities),
            "avg_pedal_balance": None,
            "pedal_balance_imbalance": False,
        }

        if activities:
            summary["avg_tss"] = summary["total_tss"] / len(activities)

            # IF moyen (normaliser depuis pourcentage) - Defensive: handle None
            ifs = [
                (a.get("icu_intensity") or 0) / 100
                for a in activities
                if a.get("icu_intensity") and a.get("icu_intensity") > 0  # type: ignore[operator]  # Safe: checked for None in first condition
            ]
            if ifs:
                summary["avg_if"] = sum(ifs) / len(ifs)

            # Pedal balance moyen
            balances = [
                a.get("avg_lr_balance") for a in activities if a.get("avg_lr_balance") is not None
            ]
            if balances:
                avg_balance = sum(balances) / len(balances)
                summary["avg_pedal_balance"] = avg_balance
                # Déséquilibre si >52% ou <48% (tolérance 2%)
                summary["pedal_balance_imbalance"] = avg_balance > 52.0 or avg_balance < 48.0

        # Métriques finales (dernière journée)
        if activities:
            last_activity = activities[-1]

            # Extract wellness metrics from last activity
            from cyclisme_training_logs.utils.metrics import extract_wellness_metrics

            final_metrics = extract_wellness_metrics(last_activity)
            summary["final_metrics"] = final_metrics

        return summary

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
            from collections import Counter

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

    def _process_workouts_detailed(
        self, activities: list[dict[str, Any]], feedback: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Process workouts avec détails pour workout_history.

        Map champs Intervals.icu (icu_ prefix) vers format interne:
        - icu_training_load → tss
        - icu_intensity (%) → if (normalisé 0.0-1.0)
        - icu_weighted_avg_watts → normalized_power
        - icu_average_watts → average_power
        - avg_lr_balance → pedal_balance (%).
        """
        workouts = []

        for i, activity in enumerate(activities, 1):
            activity_id = str(activity.get("id", ""))

            # Normaliser IF depuis pourcentage (66.36% → 0.66)
            icu_intensity = activity.get("icu_intensity", 0)
            if_normalized = icu_intensity / 100 if icu_intensity > 10 else icu_intensity

            workout = {
                "session_number": i,
                "date": activity.get("start_date_local", ""),
                "activity_id": activity_id,
                "name": activity.get("name", "Unknown"),
                "type": activity.get("type", "Ride"),
                "duration": activity.get("moving_time", 0),
                "tss": activity.get("icu_training_load", 0),
                "if": if_normalized,
                "normalized_power": activity.get("icu_weighted_avg_watts", 0),
                "average_power": activity.get("icu_average_watts", 0),
                "average_hr": activity.get("average_hr", 0),
                "max_hr": activity.get("max_hr", 0),
                "pedal_balance": activity.get("avg_lr_balance"),  # Left/Right balance (%)
            }

            # Ajouter feedback si disponible
            if activity_id in feedback:
                workout["feedback"] = feedback[activity_id]

            # Ajouter métriques gear (Di2) si activité outdoor
            is_outdoor = activity.get("trainer") is False or activity.get("type") == "Ride"
            if is_outdoor and activity_id:
                try:
                    gear_metrics = self._extract_gear_metrics(activity_id)
                    if gear_metrics:
                        workout["gear_metrics"] = gear_metrics
                        logger.debug(
                            f"Extracted gear metrics for {activity_id}: "
                            f"{gear_metrics.get('shifts', 0)} shifts"
                        )
                except Exception as e:
                    logger.warning(f"Failed to extract gear metrics for {activity_id}: {e}")

            workouts.append(workout)

        return workouts

    def _process_metrics_evolution(self, metrics_daily: list[dict[str, Any]]) -> dict[str, Any]:
        """Process évolution métriques."""
        if not metrics_daily:
            return {}

        evolution = {"daily": metrics_daily, "trends": {}}

        # Calculer tendances - Defensive: handle None values
        if len(metrics_daily) >= 2:
            first = metrics_daily[0]
            last = metrics_daily[-1]

            # Calculate metrics change using centralized utility
            from cyclisme_training_logs.utils.metrics import calculate_metrics_change

            evolution["trends"] = calculate_metrics_change(first, last)  # type: ignore[assignment]  # Complex nested dict type inference

        return evolution

    def _extract_training_learnings(
        self, workouts: list[dict[str, Any]], feedback: dict[str, Any]
    ) -> list[str]:
        """Extract enseignements training (pour AI analysis).

        Args:
            workouts: Processed workouts with enriched data (tss, if, gear_metrics, etc.)
            feedback: Session feedback data
        """
        learnings = []

        # Patterns répétés - Defensive: handle None values
        high_tss_days = [w for w in workouts if (w.get("tss") or 0) > 80]

        if high_tss_days:
            learnings.append(f"{len(high_tss_days)} séances haute charge (TSS >80)")

        # IF élevés - Defensive: handle None values
        high_if_days = [w for w in workouts if (w.get("if") or 0) > 1.0]

        if high_if_days:
            learnings.append(f"{len(high_if_days)} séances intensité élevée (IF >1.0)")

        # Pedal balance imbalance - Defensive: handle None
        balances = [w.get("pedal_balance") for w in workouts if w.get("pedal_balance")]
        if balances:
            avg_balance = sum(balances) / len(balances)
            if avg_balance > 52.0:
                imbalance_pct = avg_balance - 50.0
                learnings.append(
                    f"Déséquilibre pédalage détecté: {avg_balance:.1f}% gauche "
                    f"(+{imbalance_pct:.1f}% vs équilibre)"
                )
            elif avg_balance < 48.0:
                imbalance_pct = 50.0 - avg_balance
                learnings.append(
                    f"Déséquilibre pédalage détecté: {avg_balance:.1f}% gauche "
                    f"(-{imbalance_pct:.1f}% vs équilibre)"
                )

        # Gear shift analysis (Di2) - Defensive: handle None
        outdoor_with_gears = [
            w for w in workouts if w.get("gear_metrics") and w["gear_metrics"].get("shifts")
        ]
        if outdoor_with_gears:
            total_shifts = sum(w["gear_metrics"]["shifts"] for w in outdoor_with_gears)
            total_duration_hours = sum(w.get("duration", 0) / 3600 for w in outdoor_with_gears)

            if total_duration_hours > 0:
                shifts_per_hour = total_shifts / total_duration_hours

                # Patterns de changement de vitesse
                if shifts_per_hour > 50:
                    learnings.append(
                        f"Changements de vitesse fréquents: {total_shifts} shifts "
                        f"({shifts_per_hour:.0f}/h) - considérer anticipation plus fluide"
                    )
                elif shifts_per_hour < 20 and total_shifts > 30:
                    learnings.append(
                        f"Bonne gestion des vitesses: {total_shifts} shifts "
                        f"({shifts_per_hour:.0f}/h) - changements bien anticipés"
                    )

                # Analyse ratio moyen pour sorties outdoor
                avg_ratios = [
                    w["gear_metrics"]["avg_gear_ratio"]
                    for w in outdoor_with_gears
                    if w["gear_metrics"].get("avg_gear_ratio")
                ]
                if avg_ratios:
                    overall_avg_ratio = sum(avg_ratios) / len(avg_ratios)
                    if overall_avg_ratio < 1.5:
                        learnings.append(
                            f"Développement faible moyen ({overall_avg_ratio:.2f}) - "
                            "terrain vallonné ou récupération"
                        )
                    elif overall_avg_ratio > 3.0:
                        learnings.append(
                            f"Développement élevé moyen ({overall_avg_ratio:.2f}) - "
                            "sorties plates ou tempo soutenu"
                        )

        # Feedback patterns - Defensive: handle None
        low_rpe = [
            fid for fid, f in feedback.items() if f.get("rpe") is not None and f.get("rpe") <= 3
        ]

        if low_rpe:
            learnings.append(f"{len(low_rpe)} séances RPE faible (≤3)")

        return learnings

    def _identify_protocol_changes(
        self, learnings: list[str], metrics_evolution: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify changements protocoles nécessaires."""
        adaptations = []

        # Check TSB trends - Defensive: handle None
        trends = metrics_evolution.get("trends", {})
        tsb_change = trends.get("tsb_change")

        if tsb_change is not None and tsb_change < -10:
            adaptations.append(
                {
                    "type": "recovery",
                    "reason": f"TSB dropped {tsb_change:.1f} points",
                    "recommendation": "Add recovery day next week",
                }
            )

        # Check pedal balance imbalance in learnings
        for learning in learnings:
            if "Déséquilibre pédalage" in learning:
                adaptations.append(
                    {
                        "type": "pedal_balance",
                        "reason": learning,
                        "recommendation": "Intégrer exercices unilatéraux (single leg drills) "
                        "et vérifier position/réglages",
                    }
                )
                break  # Only add once

        return adaptations

    def _compute_compliance(
        self, activities: list[dict[str, Any]], planned: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate compliance planifié vs exécuté."""
        compliance = {
            "planned_count": len(planned),
            "executed_count": len(activities),
            "rate": 0,
            "missed": [],
            "extra": [],
        }

        if planned:
            compliance["rate"] = (len(activities) / len(planned)) * 100

        # Identifier séances manquées (simplification)
        if len(activities) < len(planned):
            compliance["missed"] = planned[len(activities) :]

        return compliance

    def _prepare_transition_data(
        self, summary: dict[str, Any], metrics_evolution: dict[str, Any], learnings: list[str]
    ) -> dict[str, Any]:
        """Préparer données transition semaine suivante."""
        transition: dict[str, Any] = {
            "current_state": {
                "total_tss": summary.get("total_tss", 0),
                "avg_tss": summary.get("avg_tss", 0),
                "final_tsb": summary.get("final_metrics", {}).get("tsb", 0),
            },
            "recommendations": [],
            "focus_areas": learnings[:3] if learnings else [],
        }

        # Recommandations basées sur TSB
        tsb = transition["current_state"]["final_tsb"]

        # Handle None TSB gracefully
        if tsb is not None:
            if tsb < -15:
                transition["recommendations"].append("Recovery week recommended (TSB very low)")
            elif tsb > 10:
                transition["recommendations"].append("Ready for intensity increase (TSB positive)")

        return transition

    def _analyze_wellness(self, wellness: dict[str, Any]) -> dict[str, Any]:
        """Analyze données wellness."""
        insights = {"sleep_quality_avg": 0, "sleep_hours_avg": 0, "weight_trend": 0, "hrv_avg": 0}

        if not wellness:
            return insights

        # Moyennes - Defensive: handle None values
        sleep_qualities = [
            w["sleep_quality"]
            for w in wellness.values()
            if w.get("sleep_quality") is not None and w.get("sleep_quality") > 0
        ]

        if sleep_qualities:
            insights["sleep_quality_avg"] = sum(sleep_qualities) / len(sleep_qualities)

        sleep_hours = [
            w["sleep_hours"]
            for w in wellness.values()
            if w.get("sleep_hours") is not None and w.get("sleep_hours") > 0
        ]

        if sleep_hours:
            insights["sleep_hours_avg"] = sum(sleep_hours) / len(sleep_hours)

        # Tendance poids - Defensive: handle None values
        weights = [
            (date, w["weight"])
            for date, w in wellness.items()
            if w.get("weight") is not None and w.get("weight") > 0
        ]

        if len(weights) >= 2:
            weights.sort()
            insights["weight_trend"] = weights[-1][1] - weights[0][1]

        return insights
