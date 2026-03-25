"""
Weekly workout data aggregator with full TSS/IF enrichment.

Agrégateur hebdomadaire implémentant DataAggregator pour collecter
et traiter données complètes d'une semaine d'entraînement. Enrichit
automatiquement chaque activité avec détails complets (TSS, IF, NP)
via appels API individuels. Collecte 7 workouts, métriques évolution
(CTL/ATL/TSB), feedback athlète, et génère structure pour 6 reports.

Examples:
    Basic weekly aggregation::

        from magma_cycling.analyzers.weekly_aggregator import WeeklyAggregator
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

        from magma_cycling.analyzers.weekly_analyzer import WeeklyAnalyzer

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

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from magma_cycling.analyzers.aggregator.analysis import AnalysisMixin
from magma_cycling.analyzers.aggregator.data_collection import DataCollectionMixin
from magma_cycling.analyzers.aggregator.processing import ProcessingMixin
from magma_cycling.api.intervals_client import IntervalsClient
from magma_cycling.config import create_intervals_client
from magma_cycling.core.data_aggregator import DataAggregator

logger = logging.getLogger(__name__)


class WeeklyAggregator(
    DataCollectionMixin,
    ProcessingMixin,
    AnalysisMixin,
    DataAggregator,
):
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

        # Initialize Intervals.icu API with configuration (Sprint R9.B Phase 2)
        try:
            self.api = create_intervals_client()
            logger.info(f"Intervals.icu API initialized for athlete {self.api.athlete_id}")
        except ValueError:
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
