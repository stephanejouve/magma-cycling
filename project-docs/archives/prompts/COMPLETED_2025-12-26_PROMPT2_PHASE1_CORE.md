# 🏗️ PROMPT CLAUDE CODE - MIGRATION V2 CORE INFRASTRUCTURE

**Phase :** Prompt 2 - Phase 1 (Core Infrastructure)
**Objectif :** Créer infrastructure v2 et résoudre dette technique Migration (M)
**Durée estimée :** 3-4 heures
**Priorité :** 🔥 CRITIQUE

---

## 🎯 MISSION

Migrer l'infrastructure core depuis le projet v2 (cyclisme-training-automation-v2) vers le projet actuel (cyclisme-training-logs) en 5 étapes :

1. **Créer `core/timeline_injector.py`** - Chronological injection
2. **Créer `core/data_aggregator.py`** - Abstract aggregation framework
3. **Créer `core/prompt_generator.py`** - Composable prompt system
4. **Créer `analyzers/daily_aggregator.py`** - Daily data aggregation
5. **Refactor 2 fichiers M→I** - insert_analysis.py + backfill_history.py

---

## 📁 CONTEXTE PROJET

### **Source Migration (v2)**
```
Location: /Users/stephanejouve/cyclisme-training-automation-v2/
Fichiers source:
  - src/core/markdown_parser.py → timeline_injector.py
  - src/core/data_aggregator.py → data_aggregator.py
  - src/core/prompt_generator.py → prompt_generator.py
  - src/analyzers/session_analyzer.py → daily_aggregator.py
```

### **Projet Actuel**
```
Location: ~/cyclisme-training-logs/
État actuel:
  - Gartner TIME intégré (7/45 fichiers v2)
  - Tests : 273/273 passing
  - Git : Clean (commit 5dc8fb4)
```

### **Fichiers en Migration**
```
🔵 insert_analysis.py (M/P1)
   STATUS: Migration (v1 → v2)
   MIGRATION_TARGET: core/timeline_injector.py

🔵 backfill_history.py (M/P2)
   STATUS: Migration (v1 → v2)
   MIGRATION_TARGET: core/timeline_injector.py
```

---

## 📋 ÉTAPE 1 : CRÉER `core/timeline_injector.py`

### **Fichier à créer :** `cyclisme_training_logs/core/timeline_injector.py`

**Source v2 :** `/Users/stephanejouve/cyclisme-training-automation-v2/src/core/markdown_parser.py`

**Objectif :** Injection chronologique d'analyses dans workouts-history.md

### **Contenu à implémenter :**

```python
"""
Chronological timeline injection for workout history entries.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P0
MIGRATION_SOURCE: cyclisme-training-automation-v2/src/core/markdown_parser.py
DOCSTRING: v2

Injecte les analyses de séance dans workouts-history.md en respectant
l'ordre chronologique. Remplace le système append-only actuel par une
insertion intelligente basée sur les dates de workout.

Examples:
    Basic chronological injection::

        from cyclisme_training_logs.core.timeline_injector import TimelineInjector
        from pathlib import Path

        # Initialiser
        injector = TimelineInjector(
            history_file=Path("~/training-logs/workouts-history.md")
        )

        # Injecter workout
        workout_entry = '''
        ### S073-01 (2025-01-06)
        **Durée:** 60min | **TSS:** 45 | **IF:** 1.2
        '''

        injector.inject_chronologically(workout_entry, workout_date="2025-01-06")

    Advanced usage with validation::

        # Avec vérification duplicates
        injector = TimelineInjector(
            history_file=Path("~/training-logs/workouts-history.md"),
            check_duplicates=True
        )

        # Injecter avec metadata
        result = injector.inject_chronologically(
            workout_entry,
            workout_date="2024-08-15",
            activity_id="i123456"
        )

        if result.success:
            print(f"Injected at line {result.line_number}")
        else:
            print(f"Error: {result.error}")

    Integration with existing workflow::

        from cyclisme_training_logs.core.timeline_injector import TimelineInjector
        from cyclisme_training_logs.config import DataRepoConfig

        # Configuration
        config = DataRepoConfig()
        injector = TimelineInjector(
            history_file=config.workouts_history_path
        )

        # Workflow existant
        analysis = generate_analysis()
        injector.inject_chronologically(analysis, workout_date=date)

Author: Claude Code
Created: 2025-12-26 (Migrated from v2)
"""

import re
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class InjectionResult:
    """Résultat d'une injection chronologique."""
    success: bool
    line_number: Optional[int] = None
    error: Optional[str] = None
    duplicate_found: bool = False


class TimelineInjector:
    """
    Injecteur chronologique pour historique workouts.

    Gère l'insertion d'entrées workout dans workouts-history.md en respectant
    l'ordre chronologique. Remplace le système append-only par une injection
    intelligente basée sur les dates.
    """

    # Pattern pour extraire date d'une entrée workout
    DATE_PATTERN = re.compile(r'###\s+S\d+-\d+\s+\((\d{4}-\d{2}-\d{2})\)')

    def __init__(
        self,
        history_file: Path,
        check_duplicates: bool = True
    ):
        """
        Initialiser l'injecteur.

        Args:
            history_file: Chemin vers workouts-history.md
            check_duplicates: Vérifier duplicates avant injection
        """
        self.history_file = Path(history_file)
        self.check_duplicates = check_duplicates

        if not self.history_file.exists():
            raise FileNotFoundError(
                f"History file not found: {self.history_file}"
            )

    def extract_date_from_entry(self, entry: str) -> Optional[date]:
        """
        Extraire la date d'une entrée workout.

        Args:
            entry: Contenu de l'entrée workout (markdown)

        Returns:
            Date extraite ou None si non trouvée
        """
        match = self.DATE_PATTERN.search(entry)
        if match:
            date_str = match.group(1)
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        return None

    def find_insertion_point(
        self,
        content_lines: List[str],
        target_date: date
    ) -> int:
        """
        Trouver le point d'insertion chronologique.

        Args:
            content_lines: Lignes du fichier history
            target_date: Date du workout à insérer

        Returns:
            Index de ligne où insérer (0 = début, len = fin)
        """
        # Parcourir les lignes pour trouver les dates
        last_earlier_date_index = 0

        for i, line in enumerate(content_lines):
            match = self.DATE_PATTERN.search(line)
            if match:
                existing_date_str = match.group(1)
                existing_date = datetime.strptime(
                    existing_date_str, '%Y-%m-%d'
                ).date()

                if existing_date < target_date:
                    # Cette entrée est plus ancienne, continuer
                    last_earlier_date_index = i
                elif existing_date >= target_date:
                    # Cette entrée est plus récente, insérer avant
                    return i

        # Si aucune entrée plus récente trouvée, insérer après la dernière
        # entrée plus ancienne
        return last_earlier_date_index + 1 if last_earlier_date_index > 0 else len(content_lines)

    def check_duplicate(
        self,
        content_lines: List[str],
        entry: str
    ) -> bool:
        """
        Vérifier si l'entrée existe déjà (duplicate).

        Args:
            content_lines: Lignes du fichier history
            entry: Entrée à vérifier

        Returns:
            True si duplicate détecté
        """
        # Extraire identifiant unique de l'entrée (ex: S073-01)
        entry_id_match = re.search(r'###\s+(S\d+-\d+)', entry)
        if not entry_id_match:
            return False

        entry_id = entry_id_match.group(1)

        # Chercher cet ID dans le contenu
        content = '\n'.join(content_lines)
        return entry_id in content

    def inject_chronologically(
        self,
        workout_entry: str,
        workout_date: Optional[date] = None
    ) -> InjectionResult:
        """
        Injecter une entrée workout dans l'ordre chronologique.

        Args:
            workout_entry: Contenu markdown de l'entrée
            workout_date: Date du workout (extraite si None)

        Returns:
            InjectionResult avec succès/erreur
        """
        # Extraire date si non fournie
        if workout_date is None:
            workout_date = self.extract_date_from_entry(workout_entry)

        if workout_date is None:
            return InjectionResult(
                success=False,
                error="Cannot extract date from entry"
            )

        # Lire contenu actuel
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return InjectionResult(
                success=False,
                error=f"Failed to read history file: {e}"
            )

        content_lines = content.split('\n')

        # Vérifier duplicates
        if self.check_duplicates:
            if self.check_duplicate(content_lines, workout_entry):
                return InjectionResult(
                    success=False,
                    error="Duplicate entry detected",
                    duplicate_found=True
                )

        # Trouver point d'insertion
        insertion_index = self.find_insertion_point(content_lines, workout_date)

        # Insérer l'entrée
        entry_lines = workout_entry.strip().split('\n')

        # Ajouter séparateur si nécessaire
        if insertion_index < len(content_lines) and content_lines[insertion_index].strip():
            entry_lines.append('')  # Ligne vide après l'entrée

        # Insérer
        for i, line in enumerate(entry_lines):
            content_lines.insert(insertion_index + i, line)

        # Écrire le nouveau contenu
        try:
            new_content = '\n'.join(content_lines)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            return InjectionResult(
                success=False,
                error=f"Failed to write history file: {e}"
            )

        return InjectionResult(
            success=True,
            line_number=insertion_index
        )

    def inject_multiple(
        self,
        entries: List[Tuple[str, date]]
    ) -> List[InjectionResult]:
        """
        Injecter plusieurs entrées en une fois.

        Args:
            entries: Liste de (workout_entry, workout_date)

        Returns:
            Liste de InjectionResult pour chaque entrée
        """
        results = []

        # Trier par date (plus ancien d'abord)
        sorted_entries = sorted(entries, key=lambda x: x[1])

        for entry, workout_date in sorted_entries:
            result = self.inject_chronologically(entry, workout_date)
            results.append(result)

            if not result.success:
                # Arrêter en cas d'erreur
                break

        return results


# Fonction utilitaire pour migration facile
def inject_workout_chronologically(
    workout_entry: str,
    history_file: Path,
    workout_date: Optional[date] = None
) -> InjectionResult:
    """
    Fonction utilitaire pour injection rapide.

    Args:
        workout_entry: Contenu markdown workout
        history_file: Chemin workouts-history.md
        workout_date: Date workout (extraite si None)

    Returns:
        InjectionResult
    """
    injector = TimelineInjector(history_file)
    return injector.inject_chronologically(workout_entry, workout_date)
```

### **Tests à créer :** `tests/test_timeline_injector.py`

```python
"""
Tests for TimelineInjector chronological injection.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""

import pytest
from pathlib import Path
from datetime import date
from cyclisme_training_logs.core.timeline_injector import (
    TimelineInjector,
    InjectionResult
)


@pytest.fixture
def sample_history_file(tmp_path):
    """Créer fichier history temporaire pour tests."""
    history = tmp_path / "workouts-history.md"
    content = """# Historique Entraînements

### S073-05 (2025-01-10)
**Durée:** 60min | **TSS:** 50

### S073-03 (2025-01-08)
**Durée:** 45min | **TSS:** 35

### S073-01 (2025-01-06)
**Durée:** 55min | **TSS:** 40
"""
    history.write_text(content)
    return history


def test_extract_date_from_entry():
    """Test extraction date depuis entrée workout."""
    injector = TimelineInjector(Path("dummy.md"))

    entry = "### S073-02 (2025-01-07)\n**Durée:** 50min"
    extracted = injector.extract_date_from_entry(entry)

    assert extracted == date(2025, 1, 7)


def test_chronological_injection_middle(sample_history_file):
    """Test injection au milieu de l'historique."""
    injector = TimelineInjector(sample_history_file)

    new_entry = """### S073-02 (2025-01-07)
**Durée:** 50min | **TSS:** 42"""

    result = injector.inject_chronologically(new_entry, date(2025, 1, 7))

    assert result.success

    # Vérifier ordre chronologique
    content = sample_history_file.read_text()
    assert content.index("S073-01") < content.index("S073-02")
    assert content.index("S073-02") < content.index("S073-03")


def test_duplicate_detection(sample_history_file):
    """Test détection duplicates."""
    injector = TimelineInjector(sample_history_file, check_duplicates=True)

    duplicate_entry = """### S073-01 (2025-01-06)
**Durée:** 55min | **TSS:** 40"""

    result = injector.inject_chronologically(duplicate_entry, date(2025, 1, 6))

    assert not result.success
    assert result.duplicate_found
```

---

## 📋 ÉTAPE 2 : CRÉER `core/data_aggregator.py`

### **Fichier à créer :** `cyclisme_training_logs/core/data_aggregator.py`

**Source v2 :** `/Users/stephanejouve/cyclisme-training-automation-v2/src/core/data_aggregator.py`

**Objectif :** Abstract base class pour agrégation multi-niveau (daily/weekly/cycle)

### **Contenu à implémenter :**

```python
"""
Abstract data aggregation framework for multi-level analysis.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P0
MIGRATION_SOURCE: cyclisme-training-automation-v2/src/core/data_aggregator.py
DOCSTRING: v2

Framework d'agrégation abstrait supportant analyses multi-niveaux :
daily (séance), weekly (semaine), cycle (4 semaines). Fournit base
réutilisable pour tous types d'analyses.

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

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AggregationResult:
    """Résultat d'une agrégation de données."""
    success: bool
    data: Dict[str, Any]
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

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialiser l'agrégateur.

        Args:
            data_dir: Répertoire données (défaut: ~/training-logs)
            config: Configuration optionnelle
        """
        self.data_dir = data_dir or Path.home() / 'training-logs'
        self.config = config or {}
        self.errors = []
        self.warnings = []

    @abstractmethod
    def collect_raw_data(self) -> Dict[str, Any]:
        """
        Collecter les données brutes nécessaires.

        Returns:
            Dict avec données brutes collectées
        """
        pass

    @abstractmethod
    def process_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traiter et analyser les données brutes.

        Args:
            raw_data: Données brutes collectées

        Returns:
            Dict avec données traitées
        """
        pass

    @abstractmethod
    def format_output(self, processed_data: Dict[str, Any]) -> str:
        """
        Formater la sortie (markdown, JSON, etc.).

        Args:
            processed_data: Données traitées

        Returns:
            Sortie formatée (généralement markdown)
        """
        pass

    def aggregate(self) -> AggregationResult:
        """
        Exécuter le pipeline d'agrégation complet.

        Template Method orchestrant les 3 étapes :
        1. Collecte données brutes
        2. Traitement
        3. Formatage sortie

        Returns:
            AggregationResult avec données et statut
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
                data={
                    'raw': raw_data,
                    'processed': processed_data,
                    'formatted': formatted_output
                },
                errors=self.errors,
                warnings=self.warnings
            )

        except Exception as e:
            logger.error(f"Aggregation failed: {e}")
            self.errors.append(str(e))

            return AggregationResult(
                success=False,
                data={},
                errors=self.errors,
                warnings=self.warnings
            )

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Valider les données (hook optionnel).

        Args:
            data: Données à valider

        Returns:
            True si données valides
        """
        return True

    def add_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ajouter metadata aux données (hook optionnel).

        Args:
            data: Données à enrichir

        Returns:
            Données avec metadata
        """
        from datetime import datetime

        data['_metadata'] = {
            'aggregator': self.__class__.__name__,
            'timestamp': datetime.now().isoformat(),
            'config': self.config
        }

        return data


class DailyDataAggregator(DataAggregator):
    """
    Agrégateur pour données quotidiennes (séance).

    Collecte et agrège :
    - Données activité Intervals.icu
    - Feedback athlète
    - État workflow
    - Métriques pré/post séance
    """

    def __init__(
        self,
        activity_id: str,
        data_dir: Optional[Path] = None
    ):
        """
        Initialiser agrégateur daily.

        Args:
            activity_id: ID activité Intervals.icu (ex: i123456)
            data_dir: Répertoire données
        """
        super().__init__(data_dir=data_dir)
        self.activity_id = activity_id

    def collect_raw_data(self) -> Dict[str, Any]:
        """Collecter données séance quotidienne."""
        # Implémentation dans daily_aggregator.py (Étape 4)
        raise NotImplementedError("Use DailyAggregator from analyzers/")

    def process_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traiter données daily."""
        raise NotImplementedError("Use DailyAggregator from analyzers/")

    def format_output(self, processed_data: Dict[str, Any]) -> str:
        """Formater sortie daily."""
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
    - bilan_final_sXXX.md
    """

    def __init__(
        self,
        week: str,
        start_date: str,
        data_dir: Optional[Path] = None
    ):
        """
        Initialiser agrégateur weekly.

        Args:
            week: Numéro semaine (ex: S073)
            start_date: Date début (YYYY-MM-DD)
            data_dir: Répertoire données
        """
        super().__init__(data_dir=data_dir)
        self.week = week
        self.start_date = start_date

    def collect_raw_data(self) -> Dict[str, Any]:
        """Collecter données hebdomadaires."""
        # Implémentation dans weekly_aggregator.py (Phase 2)
        raise NotImplementedError("Weekly aggregation not yet implemented (Phase 2)")

    def process_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traiter données weekly."""
        raise NotImplementedError("Weekly aggregation not yet implemented (Phase 2)")

    def format_output(self, processed_data: Dict[str, Any]) -> str:
        """Formater sortie weekly."""
        raise NotImplementedError("Weekly aggregation not yet implemented (Phase 2)")
```

### **Tests à créer :** `tests/test_data_aggregator.py`

```python
"""
Tests for DataAggregator abstract framework.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Author: Claude Code
Created: 2025-12-26
"""

import pytest
from pathlib import Path
from cyclisme_training_logs.core.data_aggregator import (
    DataAggregator,
    AggregationResult
)


class ConcreteAggregator(DataAggregator):
    """Implémentation concrète pour tests."""

    def collect_raw_data(self):
        return {"test": "data"}

    def process_data(self, raw_data):
        return {"processed": raw_data["test"].upper()}

    def format_output(self, processed_data):
        return f"Result: {processed_data['processed']}"


def test_aggregator_pipeline():
    """Test pipeline complet agrégation."""
    aggregator = ConcreteAggregator()
    result = aggregator.aggregate()

    assert result.success
    assert result.data['raw'] == {"test": "data"}
    assert result.data['processed'] == {"processed": "DATA"}
    assert result.data['formatted'] == "Result: DATA"


def test_aggregator_with_metadata():
    """Test ajout metadata."""
    aggregator = ConcreteAggregator()
    data = {"key": "value"}
    enriched = aggregator.add_metadata(data)

    assert '_metadata' in enriched
    assert enriched['_metadata']['aggregator'] == 'ConcreteAggregator'
```

---

## 📋 ÉTAPE 3 : CRÉER `core/prompt_generator.py`

### **Fichier à créer :** `cyclisme_training_logs/core/prompt_generator.py`

**Source v2 :** `/Users/stephanejouve/cyclisme-training-automation-v2/src/core/prompt_generator.py`

**Objectif :** Système de génération de prompts composables et réutilisables

### **Contenu :** (Fichier complet ~400 lignes)

```python
"""
Composable prompt generation system for AI analysis.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P1
MIGRATION_SOURCE: cyclisme-training-automation-v2/src/core/prompt_generator.py
DOCSTRING: v2

Système de génération de prompts composables pour analyses IA.
Supporte building blocks réutilisables (intro, context, data, instructions,
output_format) avec templates personnalisables.

Examples:
    Basic prompt generation::

        from cyclisme_training_logs.core.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        # Prompt simple
        prompt = generator.generate_daily_analysis_prompt(
            activity_id="i123456",
            workout_data={"duration": 3600, "tss": 45}
        )

        print(prompt)  # Prompt markdown complet

    Custom prompt with blocks::

        # Composition manuelle
        blocks = [
            generator.intro_block("Analyse séance"),
            generator.context_block({"FTP": 220, "Weight": 84}),
            generator.data_block(workout_data),
            generator.instructions_block("Analyser découplage"),
            generator.output_format_block("markdown")
        ]

        custom_prompt = "\\n\\n".join(blocks)

    Weekly prompt generation::

        # Prompt hebdomadaire (Phase 2)
        weekly_prompt = generator.generate_weekly_analysis_prompt(
            week="S073",
            workouts=[...],
            metrics={...}
        )

Author: Claude Code
Created: 2025-12-26 (Migrated from v2)
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import date, datetime


class PromptGenerator:
    """
    Générateur de prompts composables pour analyses IA.

    Building blocks réutilisables :
    - intro_block : Introduction analyse
    - context_block : Contexte athlète/entraînement
    - data_block : Données activité
    - instructions_block : Instructions spécifiques
    - output_format_block : Format sortie attendu
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialiser générateur.

        Args:
            templates_dir: Répertoire templates custom (optionnel)
        """
        self.templates_dir = templates_dir

    def intro_block(self, analysis_type: str) -> str:
        """
        Bloc introduction analyse.

        Args:
            analysis_type: Type analyse (daily, weekly, cycle)

        Returns:
            Bloc markdown introduction
        """
        intros = {
            "daily": "# Analyse Séance Quotidienne",
            "weekly": "# Analyse Hebdomadaire",
            "cycle": "# Analyse Cycle (4 semaines)"
        }

        return intros.get(analysis_type, "# Analyse")

    def context_block(self, athlete_data: Dict[str, Any]) -> str:
        """
        Bloc contexte athlète et entraînement.

        Args:
            athlete_data: Données athlète (FTP, poids, objectifs, etc.)

        Returns:
            Bloc markdown contexte
        """
        context = "## Contexte Athlète\n\n"

        if 'FTP' in athlete_data:
            context += f"- **FTP actuelle :** {athlete_data['FTP']}W\n"

        if 'weight' in athlete_data:
            context += f"- **Poids :** {athlete_data['weight']}kg\n"

        if 'goals' in athlete_data:
            context += f"- **Objectifs :** {athlete_data['goals']}\n"

        if 'resting_hr' in athlete_data:
            context += f"- **FC repos :** {athlete_data['resting_hr']} bpm\n"

        return context

    def data_block(self, workout_data: Dict[str, Any]) -> str:
        """
        Bloc données workout.

        Args:
            workout_data: Données activité (durée, TSS, puissance, etc.)

        Returns:
            Bloc markdown données
        """
        data = "## Données Séance\n\n"

        if 'duration' in workout_data:
            duration_min = workout_data['duration'] // 60
            data += f"- **Durée :** {duration_min} min\n"

        if 'tss' in workout_data:
            data += f"- **TSS :** {workout_data['tss']}\n"

        if 'normalized_power' in workout_data:
            data += f"- **Puissance normalisée :** {workout_data['normalized_power']}W\n"

        if 'average_power' in workout_data:
            data += f"- **Puissance moyenne :** {workout_data['average_power']}W\n"

        if 'intensity_factor' in workout_data:
            data += f"- **IF :** {workout_data['intensity_factor']:.2f}\n"

        return data

    def instructions_block(self, instructions: str) -> str:
        """
        Bloc instructions spécifiques analyse.

        Args:
            instructions: Instructions texte

        Returns:
            Bloc markdown instructions
        """
        return f"## Instructions\n\n{instructions}\n"

    def output_format_block(self, format_type: str = "markdown") -> str:
        """
        Bloc format sortie attendu.

        Args:
            format_type: Type format (markdown, json, etc.)

        Returns:
            Bloc markdown format
        """
        formats = {
            "markdown": """## Format Sortie

Répondre en markdown avec :

### SXXX-XX (YYYY-MM-DD)
**Durée:** XXmin | **TSS:** XX | **IF:** X.XX

#### Métriques Pré-séance
- CTL: XX
- ATL: XX
- TSB: XX

#### Exécution
- Découplage: X.X%
- RPE: X/10

#### Analyse
[Analyse détaillée]
""",
            "json": """## Format Sortie

Répondre en JSON :
```json
{
  "session_id": "SXXX-XX",
  "date": "YYYY-MM-DD",
  "metrics": {...},
  "analysis": "..."
}
```
"""
        }

        return formats.get(format_type, "")

    def generate_daily_analysis_prompt(
        self,
        activity_id: str,
        workout_data: Dict[str, Any],
        athlete_data: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None
    ) -> str:
        """
        Générer prompt complet analyse daily.

        Args:
            activity_id: ID activité Intervals.icu
            workout_data: Données workout
            athlete_data: Données athlète (optionnel)
            feedback: Feedback athlète (optionnel)

        Returns:
            Prompt markdown complet
        """
        blocks = [
            self.intro_block("daily"),
            ""
        ]

        # Contexte athlète si fourni
        if athlete_data:
            blocks.append(self.context_block(athlete_data))
            blocks.append("")

        # Données workout
        blocks.append(self.data_block(workout_data))
        blocks.append("")

        # Feedback si fourni
        if feedback:
            blocks.append(f"## Feedback Athlète\n\n{feedback}\n")
            blocks.append("")

        # Instructions
        instructions = """Analyser cette séance en détail :

1. **Métriques clés** : TSS, IF, découplage cardiovasculaire
2. **Qualité exécution** : Respect zones, pattern technique
3. **Recommandations** : Adaptations séance suivante
4. **Points vigilance** : Fatigue, récupération nécessaire"""

        blocks.append(self.instructions_block(instructions))
        blocks.append("")

        # Format sortie
        blocks.append(self.output_format_block("markdown"))

        return "\n".join(blocks)

    def generate_weekly_analysis_prompt(
        self,
        week: str,
        workouts: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> str:
        """
        Générer prompt analyse hebdomadaire (Phase 2).

        Args:
            week: Numéro semaine (S073)
            workouts: Liste workouts semaine
            metrics: Métriques CTL/ATL/TSB

        Returns:
            Prompt markdown complet
        """
        # Implémentation Phase 2
        raise NotImplementedError("Weekly prompt generation (Phase 2)")
```

---

## 📋 ÉTAPE 4 : CRÉER `analyzers/daily_aggregator.py`

### **Fichier à créer :** `cyclisme_training_logs/analyzers/daily_aggregator.py`

**Source v2 :** `/Users/stephanejouve/cyclisme-training-automation-v2/src/analyzers/session_analyzer.py`

**Objectif :** Implémentation concrète DailyDataAggregator

### **Contenu :** (Fichier complet ~300 lignes)

```python
"""
Daily workout data aggregator implementation.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P1
MIGRATION_SOURCE: cyclisme-training-automation-v2/src/analyzers/session_analyzer.py
DOCSTRING: v2

Implémentation concrète DataAggregator pour analyses quotidiennes.
Collecte données Intervals.icu, feedback athlète, état workflow,
métriques pré/post séance.

Examples:
    Basic daily aggregation::

        from cyclisme_training_logs.analyzers.daily_aggregator import DailyAggregator

        # Agréger données séance
        aggregator = DailyAggregator(activity_id="i123456")
        result = aggregator.aggregate()

        if result.success:
            print(result.data['formatted'])  # Markdown analysis

    Integration with workflow::

        from cyclisme_training_logs.analyzers.daily_aggregator import DailyAggregator
        from cyclisme_training_logs.config import DataRepoConfig

        # Configuration
        config = DataRepoConfig()

        # Agrégation
        aggregator = DailyAggregator(
            activity_id="i123456",
            data_dir=config.data_repo_path
        )

        # Exécution
        result = aggregator.aggregate()

        # Données disponibles
        workout_info = result.data['processed']['workout_info']
        metrics = result.data['processed']['metrics']
        feedback = result.data['processed']['feedback']

Author: Claude Code
Created: 2025-12-26 (Migrated from v2)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from cyclisme_training_logs.core.data_aggregator import DataAggregator
import logging

logger = logging.getLogger(__name__)


class DailyAggregator(DataAggregator):
    """
    Agrégateur concret pour analyses quotidiennes.

    Collecte et agrège :
    - Données activité Intervals.icu (API)
    - Feedback athlète (fichier JSON)
    - État workflow (fichier state)
    - Métriques pré/post séance (CTL/ATL/TSB)
    """

    def __init__(
        self,
        activity_id: str,
        data_dir: Optional[Path] = None
    ):
        """
        Initialiser agrégateur daily.

        Args:
            activity_id: ID activité Intervals.icu (ex: i123456)
            data_dir: Répertoire données (défaut: ~/training-logs)
        """
        super().__init__(data_dir=data_dir)
        self.activity_id = activity_id

    def collect_raw_data(self) -> Dict[str, Any]:
        """
        Collecter données brutes séance.

        Returns:
            Dict avec :
            - activity: Données Intervals.icu
            - feedback: Feedback athlète
            - workflow_state: État workflow
            - metrics: Métriques forme
        """
        raw_data = {}

        # 1. Données activité Intervals.icu
        try:
            activity_data = self._fetch_intervals_activity()
            raw_data['activity'] = activity_data
        except Exception as e:
            logger.error(f"Failed to fetch activity: {e}")
            self.errors.append(f"Activity fetch error: {e}")
            raw_data['activity'] = {}

        # 2. Feedback athlète
        try:
            feedback = self._load_feedback()
            raw_data['feedback'] = feedback
        except Exception as e:
            logger.warning(f"No feedback found: {e}")
            self.warnings.append("No athlete feedback available")
            raw_data['feedback'] = {}

        # 3. État workflow
        try:
            workflow_state = self._load_workflow_state()
            raw_data['workflow_state'] = workflow_state
        except Exception as e:
            logger.warning(f"No workflow state: {e}")
            raw_data['workflow_state'] = {}

        # 4. Métriques forme (CTL/ATL/TSB)
        try:
            metrics = self._fetch_fitness_metrics()
            raw_data['metrics'] = metrics
        except Exception as e:
            logger.warning(f"No fitness metrics: {e}")
            raw_data['metrics'] = {}

        return raw_data

    def process_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traiter données brutes.

        Args:
            raw_data: Données collectées

        Returns:
            Données traitées structurées
        """
        processed = {}

        # Traiter données activité
        activity = raw_data.get('activity', {})
        if activity:
            processed['workout_info'] = {
                'duration': activity.get('moving_time', 0),
                'tss': activity.get('training_load', 0),
                'normalized_power': activity.get('normalized_power', 0),
                'average_power': activity.get('average_power', 0),
                'intensity_factor': activity.get('if', 0),
                'average_hr': activity.get('average_hr', 0),
                'max_hr': activity.get('max_hr', 0)
            }

        # Traiter feedback
        feedback = raw_data.get('feedback', {})
        processed['feedback'] = {
            'rpe': feedback.get('rpe', 0),
            'sleep_quality': feedback.get('sleep_quality', ''),
            'motivation': feedback.get('motivation', ''),
            'comments': feedback.get('comments', '')
        }

        # Traiter métriques
        metrics = raw_data.get('metrics', {})
        processed['metrics'] = {
            'ctl': metrics.get('ctl', 0),
            'atl': metrics.get('atl', 0),
            'tsb': metrics.get('tsb', 0),
            'ramp_rate': metrics.get('ramp_rate', 0)
        }

        # Calculer métriques dérivées
        if 'workout_info' in processed:
            processed['derived_metrics'] = self._calculate_derived_metrics(
                processed['workout_info']
            )

        return processed

    def format_output(self, processed_data: Dict[str, Any]) -> str:
        """
        Formater sortie markdown.

        Args:
            processed_data: Données traitées

        Returns:
            Markdown formaté
        """
        output = []

        # Workout info
        workout = processed_data.get('workout_info', {})
        if workout:
            duration_min = workout.get('duration', 0) // 60
            output.append(f"**Durée:** {duration_min}min")
            output.append(f"**TSS:** {workout.get('tss', 0)}")
            output.append(f"**IF:** {workout.get('intensity_factor', 0):.2f}")
            output.append("")

        # Metrics
        metrics = processed_data.get('metrics', {})
        if metrics:
            output.append("#### Métriques")
            output.append(f"- CTL: {metrics.get('ctl', 0)}")
            output.append(f"- ATL: {metrics.get('atl', 0)}")
            output.append(f"- TSB: {metrics.get('tsb', 0)}")
            output.append("")

        # Feedback
        feedback = processed_data.get('feedback', {})
        if feedback.get('rpe'):
            output.append("#### Feedback")
            output.append(f"- RPE: {feedback.get('rpe')}/10")
            if feedback.get('comments'):
                output.append(f"- Notes: {feedback.get('comments')}")
            output.append("")

        return "\n".join(output)

    def _fetch_intervals_activity(self) -> Dict[str, Any]:
        """Fetch activité depuis Intervals.icu API."""
        # Utiliser sync_intervals existant
        from cyclisme_training_logs.sync_intervals import IntervalsAPI

        api = IntervalsAPI()
        return api.get_activity(self.activity_id)

    def _load_feedback(self) -> Dict[str, Any]:
        """Charger feedback athlète depuis fichier JSON."""
        feedback_file = self.data_dir / 'feedback' / f'{self.activity_id}.json'

        if not feedback_file.exists():
            return {}

        with open(feedback_file, 'r') as f:
            return json.load(f)

    def _load_workflow_state(self) -> Dict[str, Any]:
        """Charger état workflow."""
        state_file = self.data_dir / '.workflow_state.json'

        if not state_file.exists():
            return {}

        with open(state_file, 'r') as f:
            return json.load(f)

    def _fetch_fitness_metrics(self) -> Dict[str, Any]:
        """Fetch métriques forme depuis Intervals.icu."""
        from cyclisme_training_logs.sync_intervals import IntervalsAPI

        api = IntervalsAPI()
        return api.get_wellness_today()

    def _calculate_derived_metrics(self, workout: Dict[str, Any]) -> Dict[str, Any]:
        """Calculer métriques dérivées."""
        derived = {}

        # Calculer découplage si données disponibles
        if 'average_power' in workout and 'normalized_power' in workout:
            avg_power = workout['average_power']
            np = workout['normalized_power']

            if avg_power > 0:
                derived['decoupling'] = ((np - avg_power) / avg_power) * 100

        return derived
```

---

## 📋 ÉTAPE 5 : REFACTOR `insert_analysis.py` (M→I)

### **Fichier à modifier :** `cyclisme_training_logs/insert_analysis.py`

**Objectif :** Utiliser TimelineInjector au lieu d'append-only

### **Modifications à apporter :**

1. **Importer TimelineInjector**
```python
from cyclisme_training_logs.core.timeline_injector import TimelineInjector
```

2. **Remplacer méthode d'insertion**

**AVANT (append-only) :**
```python
def insert_analysis(analysis, history_file):
    # Append à la fin du fichier
    with open(history_file, 'a') as f:
        f.write(analysis)
```

**APRÈS (chronological) :**
```python
def insert_analysis(analysis, history_file, workout_date):
    # Injection chronologique
    injector = TimelineInjector(history_file)
    result = injector.inject_chronologically(analysis, workout_date)

    if not result.success:
        raise ValueError(f"Injection failed: {result.error}")

    return result
```

3. **Mettre à jour docstring**

**Modifier tag Gartner TIME :**
```python
"""
Insert AI analysis into workouts history with chronological ordering.

GARTNER_TIME: I  # ← M → I (Migration complétée)
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
RECENT_CHANGES: Refactored to use TimelineInjector (chronological injection)
DOCSTRING: v2

Insère analyses Claude.ai dans workouts-history.md en respectant l'ordre
chronologique. Remplace système append-only par TimelineInjector.

Examples:
    Command-line usage::

        poetry run insert-analysis --activity-id i123456

    Programmatic usage (new)::

        from cyclisme_training_logs.insert_analysis import insert_analysis
        from cyclisme_training_logs.core.timeline_injector import TimelineInjector
        from pathlib import Path

        # Nouvelle méthode chronologique
        analysis = generate_analysis()
        result = insert_analysis(
            analysis,
            history_file=Path("~/training-logs/workouts-history.md"),
            workout_date="2024-08-15"
        )

Author: Claude Code
Created: 2024-11-XX
Updated: 2025-12-26 (Refactored with TimelineInjector - Migration M→I complete)
"""
```

---

## 📋 ÉTAPE 6 : REFACTOR `backfill_history.py` (M→I)

### **Fichier à modifier :** `cyclisme_training_logs/backfill_history.py`

**Objectif :** Utiliser TimelineInjector pour backfill chronologique

### **Modifications similaires à insert_analysis.py :**

1. Importer TimelineInjector
2. Remplacer boucle append-only par injection chronologique
3. Mettre à jour tag Gartner TIME M → I
4. Ajouter Examples avec nouvelle méthode

---

## ✅ CRITÈRES DE SUCCÈS

### **Fichiers Créés (4 nouveaux)**
- [ ] `core/timeline_injector.py` (500+ lignes) avec docstring v2 + tag I
- [ ] `core/data_aggregator.py` (400+ lignes) avec docstring v2 + tag I
- [ ] `core/prompt_generator.py` (400+ lignes) avec docstring v2 + tag I
- [ ] `analyzers/daily_aggregator.py` (300+ lignes) avec docstring v2 + tag I

### **Tests Créés (4 fichiers)**
- [ ] `tests/test_timeline_injector.py`
- [ ] `tests/test_data_aggregator.py`
- [ ] `tests/test_prompt_generator.py`
- [ ] `tests/test_daily_aggregator.py`

### **Fichiers Refactorés (2 M→I)**
- [ ] `insert_analysis.py` utilise TimelineInjector + tag I
- [ ] `backfill_history.py` utilise TimelineInjector + tag I

### **Validation**
- [ ] Tous tests passent : `poetry run pytest` (273+ → 290+ tests)
- [ ] Validation Gartner tags : `poetry run python scripts/validate_gartner_tags.py`
- [ ] Chronological injection fonctionne : test backfill date ancienne
- [ ] Aucune régression workflow existant

### **Documentation**
- [ ] Docstrings v2 complètes (tous nouveaux fichiers)
- [ ] Examples réalistes et exécutables
- [ ] Tags Gartner TIME corrects (I pour tous nouveaux + refactorés)
- [ ] ARCHITECTURE.md mis à jour avec nouveaux composants

### **Git**
- [ ] Commit atomique avec message descriptif
- [ ] Push to origin/main
- [ ] Tag version `v2.1.0-core-infrastructure`

---

## 📊 RÉSULTATS ATTENDUS

### **Avant Prompt 2 Phase 1**
```
Docstring v2: 7/45 (15.5%)
Gartner I: 5 files (11%)
Gartner M: 2 files (4%)
Tests: 273 passing
```

### **Après Prompt 2 Phase 1**
```
Docstring v2: 13/49 (26.5%) ← +4 nouveaux + 2 refactorés
Gartner I: 11 files (22%) ← +6 (4 nouveaux + 2 M→I)
Gartner M: 0 files (0%) ← Dette technique résolue ✅
Tests: 290+ passing ← +17 nouveaux tests
```

### **Infrastructure v2 Créée**
```
✅ core/timeline_injector.py (chronological injection)
✅ core/data_aggregator.py (abstract framework)
✅ core/prompt_generator.py (composable prompts)
✅ analyzers/daily_aggregator.py (daily analysis)
✅ Fichiers M résolus (insert_analysis + backfill_history)
```

---

## 🚀 ÉTAPES SUIVANTES (Après validation)

### **Prompt 2 Phase 2 : Weekly Analysis**
- Créer `analyzers/weekly_aggregator.py`
- Créer `analyzers/weekly_analyzer.py`
- Créer `workflows/workflow_weekly.py`
- CLI `weekly-analysis` automatisé
- 6 reports générés automatiquement

### **Prompt 3 Priority 2 : Standardisation Suite**
- 10-15 fichiers P1-P2 standardisés
- Coverage v2 : 26.5% → 40%
- Compléter fichiers critiques

---

## 📝 NOTES IMPORTANTES

### **Migration v2 → Projet Actuel**

**Règles impératives :**
1. **Préserver docstrings v2 complètes** de cyclisme-training-automation-v2
2. **Adapter imports** : `from src.` → `from cyclisme_training_logs.`
3. **Ajouter note migration** : `# Migrated from cyclisme-training-automation-v2`
4. **Mettre à jour Examples** avec imports corrects
5. **Conserver metadata** Author/Created + ajouter Created migration

### **Chronological Injection**

**Test validation critique :**
```bash
# Backfill workout ancien
poetry run backfill-history --start-date 2024-08-15 --end-date 2024-08-15 --yes

# Vérifier ordre chronologique
grep -n "2024-08-15" ~/training-logs/workouts-history.md
grep -n "2025-01-" ~/training-logs/workouts-history.md

# Attendu : 2024-08-15 AVANT 2025-01-XX (ligne inférieure)
```

### **Tests Coverage**

**Minimum requis :**
- TimelineInjector : 80%+ coverage
- DataAggregator : 70%+ (abstrait)
- PromptGenerator : 60%+ (templates)
- DailyAggregator : 75%+ coverage

---

## 🎯 RÉSUMÉ MISSION

**Tu dois :**

1. ✅ Créer 4 fichiers core (timeline, aggregator, prompt, daily)
2. ✅ Créer 4 fichiers tests correspondants
3. ✅ Refactor 2 fichiers M → I (insert_analysis, backfill_history)
4. ✅ Valider chronological injection fonctionne
5. ✅ Tous tests passent (273 → 290+)
6. ✅ Git commit + push + tag v2.1.0

**Temps estimé :** 3-4 heures

**Résultat attendu :**
- Infrastructure v2 core complète ✅
- Dette technique M résolue ✅
- Coverage v2 : 15.5% → 26.5% ✅
- Base solide pour Phase 2 (Weekly) ✅

---

**Prêt à exécuter ?** 🚀
