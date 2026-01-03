"""
Daily workout data aggregation for AI analysis.

Agrégateur concret pour analyses quotidiennes (séance). Collecte et agrège
toutes les données nécessaires pour l'analyse IA d'une séance : activité
Intervals.icu, feedback athlète, état workflow, métriques fitness.

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I (Infrastructure)
    Status: Development
    Priority: P0
    Version: v2
    Migration Source: cyclisme-training-automation-v2/src/analyzers/session_analyzer.py

Examples:
    Basic daily aggregation::

        from cyclisme_training_logs.analyzers.daily_aggregator import DailyAggregator
        from pathlib import Path

        # Analyser une séance
        aggregator = DailyAggregator(
            activity_id="i123456789",
            data_dir=Path("~/training-logs")
        )

        result = aggregator.aggregate()

        if result.success:
            print(result.data['formatted'])
        else:
            print(f"Errors: {result.errors}")

    Integration with workflow::

        from cyclisme_training_logs.analyzers.daily_aggregator import DailyAggregator
        from cyclisme_training_logs.core.prompt_generator import PromptGenerator

        # Étape 1 : Agréger données
        aggregator = DailyAggregator(activity_id="i123456789")
        result = aggregator.aggregate()

        # Étape 2 : Générer prompt
        generator = PromptGenerator()
        prompt = generator.generate_daily_analysis_prompt(
            activity_id="i123456789",
            workout_data=result.data['processed']['workout'],
            athlete_data=result.data['processed']['athlete'],
            feedback=result.data['processed']['feedback']
        )

        # Étape 3 : Envoyer à IA pour analyse
        # (via clipboard ou API providers)

    Custom data directory::

        from cyclisme_training_logs.analyzers.daily_aggregator import DailyAggregator
        from pathlib import Path

        aggregator = DailyAggregator(
            activity_id="i123456789",
            data_dir=Path("/custom/path/training-logs")
        )

        result = aggregator.aggregate()

Author: Claude Code
Created: 2025-12-26 (Migrated from v2)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.data_aggregator import DataAggregator

logger = logging.getLogger(__name__)


class DailyAggregator(DataAggregator):
    """
    Agrégateur concret pour données quotidiennes (séance).

    Collecte et agrège :
    - Données activité Intervals.icu (power, HR, duration, TSS, IF, NP)
    - Feedback athlète (RPE, sensations, notes)
    - État workflow (étapes complétées, timestamps)
    - Métriques fitness pré/post séance (CTL, ATL, TSB)
    - Power zones et FTP actuelle

    Utilise le pattern Template Method de DataAggregator :
    1. collect_raw_data() - Charge depuis fichiers et API
    2. process_data() - Calcule métriques dérivées
    3. format_output() - Génère markdown pour historique
    """

    def __init__(
        self,
        activity_id: str,
        data_dir: Path | None = None,
        intervals_api_key: str | None = None,
        athlete_id: str | None = None,
    ):
        """
        Initialiser agrégateur daily.

        Args:
            activity_id: ID activité Intervals.icu (ex: i123456789)
            data_dir: Répertoire données (défaut: ~/training-logs)
            intervals_api_key: Clé API Intervals.icu (optionnel, lu depuis config)
            athlete_id: ID athlète (optionnel, lu depuis config)
        """
        super().__init__(data_dir=data_dir)
        self.activity_id = activity_id
        self.intervals_api_key = intervals_api_key
        self.athlete_id = athlete_id

        # Chemins fichiers
        self.feedback_file = self.data_dir / "daily-feedback.json"
        self.workflow_state_file = self.data_dir / ".workflow_state.json"
        self.power_zones_file = self.data_dir / "power-zones.json"

    def collect_raw_data(self) -> dict[str, Any]:
        """
        Collecter données séance quotidienne.

        Returns:
            Dict avec clés:
                - activity: Données Intervals.icu
                - feedback: Feedback athlète
                - workflow_state: État workflow
                - fitness_metrics: CTL/ATL/TSB
                - power_zones: Zones puissance.
        """
        raw_data = {}

        # 1. Données activité Intervals.icu
        logger.info(f"Fetching activity data for {self.activity_id}")
        activity = self._fetch_intervals_activity()
        raw_data["activity"] = activity

        # 2. Feedback athlète
        logger.info("Loading athlete feedback")
        feedback = self._load_feedback()
        raw_data["feedback"] = feedback

        # 3. État workflow
        logger.info("Loading workflow state")
        workflow_state = self._load_workflow_state()
        raw_data["workflow_state"] = workflow_state

        # 4. Métriques fitness (CTL/ATL/TSB)
        logger.info("Fetching fitness metrics")
        fitness_metrics = self._fetch_fitness_metrics()
        raw_data["fitness_metrics"] = fitness_metrics

        # 5. Power zones
        logger.info("Loading power zones")
        power_zones = self._load_power_zones()
        raw_data["power_zones"] = power_zones

        return raw_data

    def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Traiter données daily.

        Args:
            raw_data: Données brutes collectées

        Returns:
            Dict avec données structurées:
                - workout: Métriques séance
                - athlete: Contexte athlète
                - feedback: Feedback formaté
                - analysis_context: Contexte pour prompt IA.
        """
        processed = {}

        # 1. Métriques workout
        activity = raw_data.get("activity", {})
        processed["workout"] = {
            "activity_id": self.activity_id,
            "date": activity.get("start_date_local", ""),
            "duration": activity.get("moving_time", 0),
            "tss": activity.get("tss", 0),
            "normalized_power": activity.get("np", 0),
            "average_power": activity.get("average_watts", 0),
            "intensity_factor": activity.get("intensity", 0.0),
            "average_hr": activity.get("average_hr", 0),
            "max_hr": activity.get("max_hr", 0),
            "workout_type": activity.get("type", ""),
            "name": activity.get("name", ""),
        }

        # 2. Contexte athlète
        power_zones = raw_data.get("power_zones", {})
        fitness = raw_data.get("fitness_metrics", {})

        from cyclisme_training_logs.utils.metrics import extract_wellness_metrics

        fitness_metrics = extract_wellness_metrics(fitness)
        processed["athlete"] = {
            "FTP": power_zones.get("ftp", 0),
            "weight": activity.get("athlete_weight", 0),
            "resting_hr": activity.get("resting_hr", 0),
            "ctl": fitness_metrics["ctl"],
            "atl": fitness_metrics["atl"],
            "tsb": fitness_metrics["tsb"],
        }

        # 3. Feedback athlète
        feedback = raw_data.get("feedback", {})
        processed["feedback"] = feedback.get("notes", "")

        # 4. Métriques dérivées
        derived = self._calculate_derived_metrics(processed["workout"], processed["athlete"])
        processed["derived_metrics"] = derived

        # 5. Contexte analyse
        processed["analysis_context"] = {
            "workout_date": processed["workout"]["date"],
            "fitness_state": self._classify_fitness_state(processed["athlete"]),
            "intensity_level": self._classify_intensity(processed["workout"]),
            "workflow_complete": raw_data.get("workflow_state", {}).get("step_3_completed", False),
        }

        return processed

    def format_output(self, processed_data: dict[str, Any]) -> str:
        """
        Formater sortie daily en markdown.

        Args:
            processed_data: Données traitées

        Returns:
            Markdown formaté pour workouts-history.md.
        """
        workout = processed_data["workout"]
        athlete = processed_data["athlete"]
        feedback = processed_data["feedback"]
        derived = processed_data["derived_metrics"]

        # Header
        output = f"### {workout['name']} ({workout['date']})\n"
        output += f"**Durée:** {workout['duration']//60}min | "
        output += f"**TSS:** {workout['tss']} | "
        output += f"**IF:** {workout['intensity_factor']:.2f}\n\n"

        # Métriques pré-séance
        output += "#### Métriques Pré-séance\n"
        output += f"- CTL: {athlete['ctl']:.1f}\n"
        output += f"- ATL: {athlete['atl']:.1f}\n"
        output += f"- TSB: {athlete['tsb']:.1f}\n\n"

        # Exécution
        output += "#### Exécution\n"
        output += f"- Puissance moyenne: {workout['average_power']}W\n"
        output += f"- Puissance normalisée: {workout['normalized_power']}W\n"
        output += f"- FC moyenne: {workout['average_hr']} bpm\n"
        output += f"- Découplage: {derived.get('decoupling', 0.0):.1f}%\n\n"

        # Feedback
        if feedback:
            output += "#### Feedback Athlète\n"
            output += f"{feedback}\n\n"

        return output

    def _fetch_intervals_activity(self) -> dict[str, Any]:
        """
        Récupérer données activité depuis Intervals.icu.

        Returns:
            Dict avec données activité.
        """
        # TODO: Implémenter appel API Intervals.icu
        # Pour l'instant, retourner données mock
        logger.warning("Using mock activity data (API not implemented)")
        return {
            "id": self.activity_id,
            "start_date_local": datetime.now().isoformat(),
            "moving_time": 3600,
            "tss": 45,
            "np": 180,
            "average_watts": 175,
            "intensity": 0.82,
            "average_hr": 140,
            "max_hr": 165,
            "type": "Ride",
            "name": "Morning Ride",
        }

    def _load_feedback(self) -> dict[str, Any]:
        """
        Charger feedback athlète depuis fichier.

        Returns:
            Dict avec feedback.
        """
        if not self.feedback_file.exists():
            logger.info("No feedback file found")
            return {}

        try:
            with open(self.feedback_file, encoding="utf-8") as f:
                feedback_data = json.load(f)

            # Trouver feedback pour cette activité
            for entry in feedback_data.get("entries", []):
                if entry.get("activity_id") == self.activity_id:
                    return entry

            return {}

        except Exception as e:
            logger.error(f"Error loading feedback: {e}")
            self.errors.append(f"Failed to load feedback: {e}")
            return {}

    def _load_workflow_state(self) -> dict[str, Any]:
        """
        Charger état workflow depuis fichier.

        Returns:
            Dict avec état workflow.
        """
        if not self.workflow_state_file.exists():
            logger.info("No workflow state file found")
            return {}

        try:
            with open(self.workflow_state_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading workflow state: {e}")
            self.errors.append(f"Failed to load workflow state: {e}")
            return {}

    def _fetch_fitness_metrics(self) -> dict[str, Any]:
        """
        Récupérer métriques fitness depuis Intervals.icu.

        Returns:
            Dict avec CTL/ATL/TSB.
        """
        # TODO: Implémenter appel API Intervals.icu
        logger.warning("Using mock fitness metrics (API not implemented)")
        return {"ctl": 45.2, "atl": 38.5, "tsb": 6.7}

    def _load_power_zones(self) -> dict[str, Any]:
        """
        Charger zones puissance depuis fichier.

        Returns:
            Dict avec zones et FTP.
        """
        if not self.power_zones_file.exists():
            logger.warning("No power zones file found")
            return {"ftp": 220}

        try:
            with open(self.power_zones_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading power zones: {e}")
            self.errors.append(f"Failed to load power zones: {e}")
            return {"ftp": 220}

    def _calculate_derived_metrics(
        self, workout: dict[str, Any], athlete: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Calculer métriques dérivées.

        Args:
            workout: Données workout
            athlete: Données athlète

        Returns:
            Dict avec métriques calculées.
        """
        derived = {}

        # Découplage cardiovasculaire (approximation)
        if workout["average_hr"] > 0 and workout["average_power"] > 0:
            # Formule simplifiée
            derived["decoupling"] = 0.0  # TODO: Implémenter calcul réel
        else:
            derived["decoupling"] = 0.0

        # Efficience (W/kg)
        if athlete["weight"] > 0:
            derived["power_to_weight"] = workout["average_power"] / athlete["weight"]
        else:
            derived["power_to_weight"] = 0.0

        # Variability Index (NP / AP)
        if workout["average_power"] > 0:
            derived["variability_index"] = workout["normalized_power"] / workout["average_power"]
        else:
            derived["variability_index"] = 1.0

        return derived

    def _classify_fitness_state(self, athlete: dict[str, Any]) -> str:
        """
        Classifier état fitness basé sur TSB.

        Args:
            athlete: Données athlète avec CTL/ATL/TSB

        Returns:
            État: 'fresh', 'optimal', 'fatigued', 'overreached'.
        """
        tsb = athlete.get("tsb", 0)

        if tsb > 10:
            return "fresh"
        elif tsb >= -10:
            return "optimal"
        elif tsb >= -20:
            return "fatigued"
        else:
            return "overreached"

    def _classify_intensity(self, workout: dict[str, Any]) -> str:
        """
        Classifier intensité workout basé sur IF.

        Args:
            workout: Données workout

        Returns:
            Intensité: 'recovery', 'endurance', 'tempo', 'threshold', 'vo2max'.
        """
        intensity_factor = workout.get("intensity_factor", 0.0)

        if intensity_factor < 0.55:
            return "recovery"
        elif intensity_factor < 0.75:
            return "endurance"
        elif intensity_factor < 0.85:
            return "tempo"
        elif intensity_factor < 0.95:
            return "threshold"
        else:
            return "vo2max"
