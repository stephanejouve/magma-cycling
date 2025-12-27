"""
Détection et suppression des doublons dans workouts-history.md

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-27
PRIORITY: P1
DOCSTRING: v2

Utilisé en mode paranoid pour valider les insertions TimelineInjector.
Détecte les doublons après insertion et peut les supprimer automatiquement
ou lever une erreur (fail-fast).

Examples:
    Quick scan for duplicates::

        from cyclisme_training_logs.core.duplicate_detector import DuplicateDetector
        from pathlib import Path

        detector = DuplicateDetector(
            history_file=Path("~/training-logs/workouts-history.md"),
            check_window=50
        )

        duplicates = detector.quick_scan()
        if duplicates:
            print(f"Doublons détectés: {[d['id'] for d in duplicates]}")

    Auto-fix duplicates::

        from cyclisme_training_logs.core.duplicate_detector import check_and_handle_duplicates
        from pathlib import Path

        check_and_handle_duplicates(
            history_file=Path("~/training-logs/workouts-history.md"),
            auto_fix=True,
            check_window=50
        )

    Fail-fast mode (default)::

        from cyclisme_training_logs.core.duplicate_detector import (
            check_and_handle_duplicates,
            DuplicateDetectedError
        )

        try:
            check_and_handle_duplicates(history_file=path, auto_fix=False)
        except DuplicateDetectedError as e:
            print(f"Erreur: {e}")
            # Lancer clean_duplicates_multi.py

Author: Claude Code
Created: 2025-12-27
Updated: 2025-12-27 (Initial implementation)
"""

from pathlib import Path
import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DuplicateDetectedError(Exception):
    """Exception levée quand des doublons sont détectés."""

    def __init__(self, duplicates: List[Dict]):
        self.duplicates = duplicates
        ids = [d['id'] for d in duplicates]
        super().__init__(f"Doublons détectés: {', '.join(ids)}")


class DuplicateDetector:
    """Détection rapide des doublons dans workouts-history.md"""

    def __init__(self, history_file: Path, check_window: int = 50):
        """
        Args:
            history_file: Chemin vers workouts-history.md
            check_window: Nombre d'entrées à scanner (0 = tout le fichier)
        """
        self.history_file = history_file
        self.check_window = check_window
        self.pattern = re.compile(r'^### (S\d{3}-\d{2}(?:-\w+)*(?:-V\d{3})?)\s*$')

    def quick_scan(self) -> List[Dict]:
        """
        Scan rapide des N dernières entrées pour détecter doublons.

        Returns:
            Liste des doublons détectés avec métadata
        """
        if not self.history_file.exists():
            return []

        content = self.history_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Trouver toutes les entrées
        entries = []
        for i, line in enumerate(lines):
            match = self.pattern.match(line)
            if match:
                entries.append({
                    'id': match.group(1),
                    'line': i + 1,
                    'line_index': i
                })

        # Limiter au window si spécifié
        if self.check_window > 0:
            entries = entries[:self.check_window]

        # Détecter doublons
        seen = {}
        duplicates = []

        for entry in entries:
            entry_id = entry['id']
            if entry_id in seen:
                duplicates.append({
                    'id': entry_id,
                    'first_line': seen[entry_id]['line'],
                    'duplicate_line': entry['line']
                })
            else:
                seen[entry_id] = entry

        return duplicates

    def find_entry_bounds(self, line_index: int, lines: List[str]) -> tuple:
        """
        Trouve les bornes (début, fin) d'une entrée à partir d'une ligne.

        Args:
            line_index: Index de ligne (0-based) du début de l'entrée
            lines: Liste des lignes du fichier

        Returns:
            (start_index, end_index) de l'entrée complète
        """
        start = line_index

        # Chercher la fin (prochaine entrée ou fin de fichier)
        end = len(lines) - 1
        for i in range(line_index + 1, len(lines)):
            if self.pattern.match(lines[i]):
                end = i - 1
                break

        return (start, end)

    def remove_duplicates(self, duplicates: List[Dict]) -> int:
        """
        Supprime les doublons du fichier.

        Args:
            duplicates: Liste des doublons à supprimer

        Returns:
            Nombre de lignes supprimées
        """
        if not duplicates:
            return 0

        content = self.history_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Identifier toutes les lignes à supprimer
        lines_to_remove = set()

        for dup in duplicates:
            # Trouver l'index 0-based de la ligne dupliquée
            dup_line_index = dup['duplicate_line'] - 1

            # Trouver les bornes complètes de l'entrée
            start, end = self.find_entry_bounds(dup_line_index, lines)

            # Marquer toutes les lignes de cette entrée
            for i in range(start, end + 1):
                lines_to_remove.add(i)

        # Construire nouveau contenu sans les doublons
        cleaned_lines = [
            line for i, line in enumerate(lines)
            if i not in lines_to_remove
        ]

        # Écrire le fichier nettoyé
        self.history_file.write_text('\n'.join(cleaned_lines), encoding='utf-8')

        logger.info(f"Supprimé {len(lines_to_remove)} lignes ({len(duplicates)} doublons)")

        return len(lines_to_remove)


def check_and_handle_duplicates(
    history_file: Path,
    auto_fix: bool = False,
    check_window: int = 50
) -> None:
    """
    Vérifie et gère les doublons selon la config.

    Args:
        history_file: Fichier workouts-history.md
        auto_fix: Si True, supprime automatiquement les doublons
        check_window: Nombre d'entrées à scanner

    Raises:
        DuplicateDetectedError: Si doublons détectés et auto_fix=False
    """
    detector = DuplicateDetector(history_file, check_window)
    duplicates = detector.quick_scan()

    if not duplicates:
        return

    # Doublons détectés
    dup_ids = [d['id'] for d in duplicates]

    if auto_fix:
        # Suppression automatique
        logger.warning(
            f"⚠️  {len(duplicates)} doublon(s) détecté(s): {', '.join(dup_ids)}"
        )
        lines_removed = detector.remove_duplicates(duplicates)
        logger.warning(
            f"✅ Doublons auto-supprimés ({lines_removed} lignes)"
        )
    else:
        # Erreur - fail fast
        logger.error(
            f"❌ {len(duplicates)} doublon(s) détecté(s): {', '.join(dup_ids)}"
        )
        logger.error(
            "Lancer: python3 scripts/maintenance/clean_duplicates_multi.py"
        )
        raise DuplicateDetectedError(duplicates)
