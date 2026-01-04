r"""
Abstract data aggregation framework for multi-level analysis.

Framework d'agrégation abstrait supportant analyses multi-niveaux :
daily (séance), weekly (semaine), cycle (4 semaines). Fournit base
réutilisable pour tous types d'analyses.

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I (Infrastructure)
    Status: Development
    Priority: P0
    Version: v2
    Migration Source: cyclisme-training-automation-v2/src/core/data_aggregator.py

Examples:
    Creating a custom aggregator::

        from cyclisme_training_logs.core.data_aggregator import DataAggregator
        from pathlib import Path

        class MyAggregator(DataAggregator):
            def collect_raw_data(self):
                # Collecte données brutes
                return {"workouts": [...], "metrics": {...}}

            def process_data(self, raw_data):
                # Traitement
                return {"summary": "...", "details": [...]}

            def format_output(self, processed_data):
                # Formatage markdown
                return "# My Analysis\\n\\n..."

        # Utilisation
        aggregator = MyAggregator(data_dir=Path("~/training-logs"))
        result = aggregator.aggregate()

    Daily aggregation example::

        from cyclisme_training_logs.analyzers.daily_aggregator import DailyAggregator

        # Analyse séance quotidienne
        daily = DailyAggregator(activity_id="i123456")
        daily_data = daily.aggregate()

        # Données disponibles
        print(daily_data["workout_info"])
        print(daily_data["metrics"])
        print(daily_data["feedback"])

    Weekly aggregation (future)::

        from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator

        # Analyse hebdomadaire
        weekly = WeeklyAggregator(week="S073", start_date="2025-01-06")
        weekly_data = weekly.aggregate()

        # 6 reports générés
        for report_name, content in weekly_data["reports"].items():
            print(f"Report: {report_name}")

Author: Claude Code
Created: 2025-12-26 (Migrated from v2)
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AggregationResult:
    """Résultat d'une agrégation de données."""

    success: bool
    data: dict[str, Any]
    errors: list[str]
    warnings: list[str]


class DataAggregator(ABC):
    """
    Base abstraite pour agrégateurs de données multi-niveaux.

    Pattern Template Method pour agrégation standardisée :
    1. collect_raw_data() - Collecte données brutes
    2. process_data() - Traitement et analyse
    3. format_output() - Formatage sortie (markdown, JSON, etc.)
    """

    def __init__(self, data_dir: Path | None = None, config: dict[str, Any] | None = None):
        """
        Initialize l'agrégateur.

        Args:
            data_dir: Répertoire données (défaut: ~/training-logs)
            config: Configuration optionnelle
        """
        self.data_dir = data_dir or Path.home() / "training-logs"

        self.config = config or {}
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @abstractmethod
    def collect_raw_data(self) -> dict[str, Any]:
        """
        Collect les données brutes nécessaires.

        Returns:
            Dict avec données brutes collectées.
        """
        pass

    @abstractmethod
    def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process et analyser les données brutes.

        Args:
            raw_data: Données brutes collectées

        Returns:
            Dict avec données traitées.
        """
        pass

    @abstractmethod
    def format_output(self, processed_data: dict[str, Any]) -> str:
        """
        Format la sortie (markdown, JSON, etc.).

        Args:
            processed_data: Données traitées

        Returns:
            Sortie formatée (généralement markdown).
        """
        pass

    def aggregate(self) -> AggregationResult:
        """
        Execute le pipeline d'agrégation complet.

        Template Method orchestrant les 3 étapes :
        1. Collecte données brutes
        2. Traitement
        3. Formatage sortie

        Returns:
            AggregationResult avec données et statut.
        """
        try:
            # Étape 1 : Collecte
            logger.info(f"Collecting raw data for {self.__class__.__name__}")
            raw_data = self.collect_raw_data()

            if not raw_data:
                self.warnings.append("No raw data collected")

            # Étape 2 : Traitement
            logger.info("Processing data")
            processed_data = self.process_data(raw_data)

            # Étape 3 : Formatage
            logger.info("Formatting output")
            formatted_output = self.format_output(processed_data)

            return AggregationResult(
                success=True,
                data={"raw": raw_data, "processed": processed_data, "formatted": formatted_output},
                errors=self.errors,
                warnings=self.warnings,
            )

        except Exception as e:
            import traceback

            tb_str = traceback.format_exc()
            logger.error(f"Aggregation failed: {e}")
            logger.error(f"Traceback:\n{tb_str}")
            self.errors.append(str(e))

            return AggregationResult(
                success=False, data={}, errors=self.errors, warnings=self.warnings
            )

    def validate_data(self, data: dict[str, Any]) -> bool:
        """
        Validate les données (hook optionnel).

        Args:
            data: Données à valider

        Returns:
            True si données valides.
        """
        return True

    def add_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Add metadata aux données (hook optionnel).

        Args:
            data: Données à enrichir

        Returns:
            Données avec metadata.
        """
        from datetime import datetime

        data["_metadata"] = {
            "aggregator": self.__class__.__name__,
            "timestamp": datetime.now().isoformat(),
            "config": self.config,
        }

        return data


class DailyDataAggregator(DataAggregator):
    """
    Agrégateur pour données quotidiennes (séance).

    Collecte et agrège :
    - Données activité Intervals.icu
    - Feedback athlète
    - État workflow
    - Métriques pré/post séance.
    """

    def __init__(self, activity_id: str, data_dir: Path | None = None):
        """
        Initialize agrégateur daily.

        Args:
            activity_id: ID activité Intervals.icu (ex: i123456)
            data_dir: Répertoire données.
        """
        super().__init__(data_dir=data_dir)

        self.activity_id = activity_id

    def collect_raw_data(self) -> dict[str, Any]:
        """Collect données séance quotidienne."""
        # Implémentation dans daily_aggregator.py (Étape 4)

        raise NotImplementedError("Use DailyAggregator from analyzers/")

    def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Process données daily."""
        raise NotImplementedError("Use DailyAggregator from analyzers/")

    def format_output(self, processed_data: dict[str, Any]) -> str:
        """Format sortie daily."""
        raise NotImplementedError("Use DailyAggregator from analyzers/")


class WeeklyDataAggregator(DataAggregator):
    """
    Agrégateur pour données hebdomadaires.

    Génère 6 reports :
    - workout_history_sXXX.md
    - metrics_evolution_sXXX.md
    - training_learnings_sXXX.md
    - protocol_adaptations_sXXX.md
    - transition_sXXX_sXXX.md
    - bilan_final_sXXX.md.
    """

    def __init__(self, week: str, start_date: str, data_dir: Path | None = None):
        """
        Initialize agrégateur weekly.

        Args:
            week: Numéro semaine (ex: S073)
            start_date: Date début (YYYY-MM-DD)
            data_dir: Répertoire données.
        """
        super().__init__(data_dir=data_dir)

        self.week = week
        self.start_date = start_date

    def collect_raw_data(self) -> dict[str, Any]:
        """Collect données hebdomadaires."""
        # Implémentation dans weekly_aggregator.py (Phase 2)

        raise NotImplementedError("Weekly aggregation not yet implemented (Phase 2)")

    def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Process données weekly."""
        raise NotImplementedError("Weekly aggregation not yet implemented (Phase 2)")

    def format_output(self, processed_data: dict[str, Any]) -> str:
        """Format sortie weekly."""
        raise NotImplementedError("Weekly aggregation not yet implemented (Phase 2)")
