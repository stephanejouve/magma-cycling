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
        from cyclisme_training_logs.config import get_data_config

        # Configuration
        config = get_data_config()
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
        self.history_file = Path(history_file).expanduser()
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

        Maintient l'ordre chronologique (ancien → récent) dans le fichier.

        Args:
            content_lines: Lignes du fichier history
            target_date: Date du workout à insérer

        Returns:
            Index de ligne où insérer (0 = début, len = fin)
        """
        # Déterminer ordre existant (chronologique ou reverse)
        dates_found = []
        date_indices = []

        for i, line in enumerate(content_lines):
            match = self.DATE_PATTERN.search(line)
            if match:
                existing_date_str = match.group(1)
                existing_date = datetime.strptime(
                    existing_date_str, '%Y-%m-%d'
                ).date()
                dates_found.append(existing_date)
                date_indices.append(i)

        # Si aucune date trouvée, insérer au début
        if not dates_found:
            return 0

        # Déterminer si ordre chronologique ou reverse
        is_chronological = all(
            dates_found[i] <= dates_found[i+1]
            for i in range(len(dates_found)-1)
        ) if len(dates_found) > 1 else True

        # Trouver position d'insertion selon l'ordre
        for i, (existing_date, line_idx) in enumerate(zip(dates_found, date_indices)):
            if is_chronological:
                # Ordre chronologique (ancien → récent)
                if target_date < existing_date:
                    # Insérer avant cette entrée
                    return line_idx
            else:
                # Ordre reverse chronologique (récent → ancien)
                if target_date > existing_date:
                    # Insérer avant cette entrée
                    return line_idx

        # Si pas de position trouvée, insérer à la fin
        return len(content_lines)

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
