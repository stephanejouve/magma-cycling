"""Gestionnaire d'insertion dans workouts-history.md."""

import logging
import re
import subprocess
from datetime import date
from pathlib import Path

from magma_cycling.core.duplicate_detector import (
    DuplicateDetectedError,
    check_and_handle_duplicates,
)
from magma_cycling.core.timeline_injector import TimelineInjector
from magma_cycling.inserter.parser import AnalysisParser

logger = logging.getLogger(__name__)


class WorkoutHistoryManager:
    """Gestionnaire de workouts-history.md."""

    def __init__(self, logs_dir=None, yes_confirm=False):
        """
        Initialize WorkoutHistoryManager.

        Args:
            logs_dir: Legacy parameter, use data repo config instead
            yes_confirm: Auto-confirm all prompts (for non-interactive mode).
        """
        from magma_cycling.config import get_data_config

        self.yes_confirm = yes_confirm

        # Use data repo config if available
        if logs_dir is None:
            try:
                config = get_data_config()
                self.history_file = config.workouts_history_path
                self.logs_dir = config.data_repo_path
            except FileNotFoundError:
                # Fallback to default logs directory (legacy)
                self.logs_dir = Path.cwd() / "logs"
                self.history_file = self.logs_dir / "workouts-history.md"
        else:
            # Legacy: explicit logs_dir provided
            self.logs_dir = Path(logs_dir)
            self.history_file = self.logs_dir / "workouts-history.md"

    def read_history(self):
        """Read le fichier d'historique."""
        if not self.history_file.exists():
            print(f"❌ Fichier non trouvé : {self.history_file}")
            return None

        with open(self.history_file, encoding="utf-8") as f:
            return f.read()

    def check_duplicate(self, content, analysis_text):
        """Verify si une entrée similaire existe déjà."""
        # Extraire le nom de la séance depuis l'analyse

        match = re.search(r"###\s*(.+?)\s*\n", analysis_text)
        if not match:
            return False

        workout_name = match.group(1).strip()

        # Extraire l'ID de l'activité
        id_match = re.search(r"ID\s*:\s*(.+?)\s*\n", analysis_text)
        if not id_match:
            # Fallback: old format without ID (backward compatibility)
            activity_id = None
        else:
            activity_id = id_match.group(1).strip()

        # Extraire la date
        date_str = AnalysisParser.extract_date_from_analysis(analysis_text)
        if not date_str:
            return False

        # Chercher dans le contenu existant
        if activity_id:
            # New format: Pattern includes ID to differentiate same-name activities
            # Pattern : ### NOM\nID : ACTIVITY_ID\nDate : DATE
            pattern = (
                rf"###\s*{re.escape(workout_name)}\s*\n"
                rf"ID\s*:\s*{re.escape(activity_id)}\s*\n"
                rf"Date\s*:\s*{re.escape(date_str)}"
            )
        else:
            # Old format fallback: Pattern without ID (backward compatibility)
            # Pattern : ### NOM\nDate : DATE
            pattern = rf"###\s*{re.escape(workout_name)}\s*\nDate\s*:\s*{re.escape(date_str)}"

        if re.search(pattern, content):
            return True

        return False

    def insert_analysis(self, analysis_text):
        """Insérer l'analyse dans workouts-history.md via TimelineInjector."""
        # Lire le fichier existant

        content = self.read_history()
        if content is None:
            return False

        # Vérifier les doublons (garde le prompt utilisateur)
        if self.check_duplicate(content, analysis_text):
            date_str = AnalysisParser.extract_date_from_analysis(analysis_text)
            print(f"⚠️  Une entrée similaire existe déjà pour la date {date_str}")
            if self.yes_confirm:
                print("   ✅ Overwrite confirmé (--yes)")
                response = "y"
            else:
                response = input("   Continuer quand même ? (y/N) : ")
                if response.lower() != "y":
                    print("❌ Insertion annulée")
                    return False

        # Extraire et convertir date pour TimelineInjector
        date_str = AnalysisParser.extract_date_from_analysis(analysis_text)
        if date_str:
            # Convertir format DD/MM/YYYY vers YYYY-MM-DD
            day, month, year = date_str.split("/")
            workout_date = date(int(year), int(month), int(day))
        else:
            # Fallback: utiliser date actuelle
            print("⚠️  Date non détectée, utilisation de la date du jour")
            workout_date = date.today()

        # Utiliser TimelineInjector pour insertion chronologique
        try:
            injector = TimelineInjector(
                history_file=self.history_file, check_duplicates=False  # Déjà fait ci-dessus
            )

            result = injector.inject_chronologically(
                workout_entry=analysis_text, workout_date=workout_date
            )

            if result.success:
                print(f"   ✅ Injection chronologique réussie (ligne {result.line_number})")

                # === NOUVEAU: Vérification doublons (mode paranoid) ===
                try:
                    # Late import from facade for backward-compatible test patching
                    # (tests patch magma_cycling.insert_analysis.get_data_config)
                    from magma_cycling import insert_analysis as _facade

                    config = _facade.get_data_config()

                    if config.paranoid_duplicate_check:
                        logger.info("🔍 Vérification doublons (mode paranoid)...")

                        check_and_handle_duplicates(
                            history_file=self.history_file,
                            auto_fix=config.auto_fix_duplicates,
                            check_window=config.duplicate_check_window,
                        )

                        logger.info("✅ Aucun doublon détecté")

                except DuplicateDetectedError as e:
                    # Doublons détectés en mode non-auto-fix
                    print(f"\n⚠️  ATTENTION: {e}")
                    print("Lancer: python3 scripts/maintenance/clean_duplicates_multi.py\n")
                    return False

                except Exception as e:
                    # Autre erreur durant check - ne pas bloquer l'insertion
                    logger.warning(f"⚠️  Erreur vérification doublons: {e}")
                    # Continuer quand même (insertion OK)

                # === FIN NOUVEAU ===

                return True
            else:
                print(f"   ❌ Erreur TimelineInjector: {result.error}")
                return False

        except Exception as e:
            print(f"   ❌ Erreur lors de l'injection: {e}")
            return False

    def show_diff(self):
        """Display le git diff."""
        try:
            result = subprocess.run(
                ["git", "diff", str(self.history_file)],
                capture_output=True,
                text=True,
                cwd=self.logs_dir.parent,
            )
            if result.stdout:
                print("\n" + "=" * 60)
                print("GIT DIFF")
                print("=" * 60)
                print(result.stdout)
            return True
        except Exception as e:
            print(f"⚠️  Impossible d'afficher git diff : {e}")
            return False
