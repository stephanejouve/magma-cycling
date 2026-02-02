#!/usr/bin/env python3
"""
Insertion de l'analyse IA dans workouts-history.md.

Insère l'analyse générée par IA dans le fichier workouts-history.md en
respectant l'ordre chronologique via TimelineInjector. Remplace le système
append-only par une injection intelligente basée sur les dates de workout.

Examples:
    CLI usage::

        # Insertion depuis presse-papier (workflow manuel)
        poetry run insert-analysis

        # Test sans modification
        poetry run insert-analysis --dry-run

        # Insertion depuis fichier
        poetry run insert-analysis --file analysis.md

        # Mode auto (pour backfill)
        poetry run insert-analysis --yes

    Programmatic usage with TimelineInjector::

        from cyclisme_training_logs.core.timeline_injector import TimelineInjector
        from cyclisme_training_logs.config import get_data_config

        # Initialisation injector avec config.py (recommandé)
        config = get_data_config()
        injector = TimelineInjector(
            history_file=config.workouts_history_path
        )

        # Injection chronologique
        result = injector.inject_chronologically(
            workout_entry=analysis_text,
            workout_date=date(2024, 8, 15)
        )

        if result.success:
            print(f"Injected at line {result.line_number}")
        else:
            print(f"Error: {result.error}")

Author: Claude Code
Created: 2024-11-15
Updated: 2025-12-26 (Migrated to TimelineInjector - chronological injection)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P1
    Version: v2
"""
import argparse
import logging
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from cyclisme_training_logs.config import get_data_config
from cyclisme_training_logs.core.duplicate_detector import (
    DuplicateDetectedError,
    check_and_handle_duplicates,
)
from cyclisme_training_logs.core.timeline_injector import TimelineInjector

logger = logging.getLogger(__name__)


class ClipboardReader:
    """Lecteur du presse-papier macOS."""

    @staticmethod
    def read_clipboard():
        """Read le contenu du presse-papier."""
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            return result.stdout
        except Exception as e:
            print(f"❌ Erreur lecture presse-papier : {e}")
            return None


class AnalysisParser:
    """Parse pour l'analyse de Claude.ai."""

    @staticmethod
    def extract_markdown_block(text):
        """Extract le bloc markdown de l'analyse."""
        # Nettoyer le texte

        text = text.strip()

        # Cas 1 : Le texte est déjà un bloc markdown propre (commence par ###)
        if text.startswith("###"):
            return text

        # Cas 2 : Le texte contient un bloc de code markdown (```markdown ... ```)
        markdown_block_pattern = r"```(?:markdown)?\s*\n(.*?)\n```"
        match = re.search(markdown_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Cas 3 : Chercher la première ligne commençant par ###
        lines = text.split("\n")
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("###"):
                start_idx = i
                break

        if start_idx is not None:
            # Prendre tout depuis ### jusqu'à la fin ou jusqu'à un marqueur de fin
            remaining = "\n".join(lines[start_idx:])
            return remaining.strip()

        # Cas 4 : Échec - retourner le texte brut
        print("⚠️  Impossible de détecter automatiquement le bloc markdown")
        print("   Vérification manuelle recommandée")
        return text

    @staticmethod
    def detect_session_type(text):
        """Détecter le type de session (exécutée, repos, annulation).

        Returns:
            str: "executed", "rest", "cancelled", ou "unknown"
        """
        text_lower = text.lower()

        # Détecter repos
        if any(marker in text_lower for marker in ["repos planifié", "jour de repos", "rest day"]):
            return "rest"

        # Détecter annulation
        if any(
            marker in text_lower for marker in ["séance annulée", "session annulée", "cancelled"]
        ):
            return "cancelled"

        # Détecter séance exécutée (présence sections techniques)
        if "#### Exécution" in text or "#### Charge d'Entraînement" in text:
            return "executed"

        return "unknown"

    @staticmethod
    def count_sessions(text):
        """Compter le nombre de sessions dans le markdown.

        Returns:
            int: Nombre de sessions détectées.
        """
        # Compter les lignes commençant par ### (titres de session)

        import re

        sessions = re.findall(r"^###\s+", text, re.MULTILINE)
        return len(sessions)

    @staticmethod
    def validate_analysis(text):
        """Validate que le texte est bien une analyse formatée (supporte batch et types multiples)."""
        # Détecter nombre de sessions

        num_sessions = AnalysisParser.count_sessions(text)

        if num_sessions == 0:
            print("⚠️  Aucune session détectée (pas de ### trouvé)")
            return False

        print(f"   📊 {num_sessions} session(s) détectée(s)")

        # Détecter type(s) de session
        session_type = AnalysisParser.detect_session_type(text)
        print(f"   📝 Type détecté : {session_type}")

        # Validation adaptée selon le type
        if session_type == "executed":
            # Validation stricte pour séances exécutées
            required_sections = [
                "Date :",
                "#### Métriques Pré-séance",
                "#### Exécution",
                "#### Exécution Technique",
                "#### Charge d'Entraînement",
                "#### Validation Objectifs",
                "#### Points d'Attention",
                "#### Recommandations Progression",
                "#### Métriques Post-séance",
            ]

            missing = []
            for section in required_sections:
                if section not in text:
                    missing.append(section)

            if missing:
                print("⚠️  Sections manquantes dans l'analyse :")
                for m in missing:
                    print(f"   - {m}")
                return False

        elif session_type in ["rest", "cancelled"]:
            # Validation allégée pour repos/annulations
            required_sections = ["Date :"]

            missing = []
            for section in required_sections:
                if section not in text:
                    missing.append(section)

            if missing:
                print("⚠️  Sections manquantes (validation allégée) :")
                for m in missing:
                    print(f"   - {m}")
                return False

        else:
            # Type inconnu : validation minimale
            print("⚠️  Type de session inconnu, validation minimale")
            if "Date :" not in text:
                print("   - Date obligatoire manquante")
                return False

        return True

    @staticmethod
    def extract_date_from_analysis(text):
        """Extract la date de l'analyse pour détecter les doublons."""
        match = re.search(r"Date\s*:\s*(\d{2}/\d{2}/\d{4})", text)

        if match:
            return match.group(1)
        return None


class WorkoutHistoryManager:
    """Gestionnaire de workouts-history.md."""

    def __init__(self, logs_dir=None, yes_confirm=False):
        """
        Initialize WorkoutHistoryManager.

        Args:
            logs_dir: Legacy parameter, use data repo config instead
            yes_confirm: Auto-confirm all prompts (for non-interactive mode).
        """
        from cyclisme_training_logs.config import get_data_config

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
        date = AnalysisParser.extract_date_from_analysis(analysis_text)
        if not date:
            return False

        # Chercher dans le contenu existant
        if activity_id:
            # New format: Pattern includes ID to differentiate same-name activities
            # Pattern : ### NOM\nID : ACTIVITY_ID\nDate : DATE
            pattern = (
                rf"###\s*{re.escape(workout_name)}\s*\n"
                rf"ID\s*:\s*{re.escape(activity_id)}\s*\n"
                rf"Date\s*:\s*{re.escape(date)}"
            )
        else:
            # Old format fallback: Pattern without ID (backward compatibility)
            # Pattern : ### NOM\nDate : DATE
            pattern = rf"###\s*{re.escape(workout_name)}\s*\nDate\s*:\s*{re.escape(date)}"

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
                    config = get_data_config()

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


def main():
    """Command-line entry point for inserting analysis into weekly reports."""
    parser = argparse.ArgumentParser(
        description="Insérer l'analyse Claude.ai dans workouts-history.md"
    )

    parser.add_argument("--dry-run", action="store_true", help="Mode test : affiche sans modifier")
    parser.add_argument("--file", help="Lire depuis un fichier au lieu du presse-papier")
    parser.add_argument(
        "--logs-dir", default=None, help="Répertoire des logs (défaut: utilise config.py)"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirmer automatiquement l'insertion (mode non-interactif)",
    )

    args = parser.parse_args()

    print("📋 Insertion de l'analyse dans workouts-history.md")
    print()

    # Lire l'analyse
    if args.file:
        print(f"📂 Lecture depuis {args.file}...")
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ Fichier non trouvé : {args.file}")
            sys.exit(1)
        with open(file_path, encoding="utf-8") as f:
            raw_text = f.read()
    else:
        print("📋 Lecture du presse-papier...")
        raw_text = ClipboardReader.read_clipboard()
        if not raw_text:
            print("❌ Presse-papier vide")
            sys.exit(1)

    print("   ✅ Contenu récupéré")
    print()

    # Parser l'analyse
    print("🔍 Extraction du bloc markdown...")
    analysis = AnalysisParser.extract_markdown_block(raw_text)

    if not analysis:
        print("❌ Impossible d'extraire l'analyse")
        sys.exit(1)

    print("   ✅ Bloc extrait")
    print()

    # Valider
    print("✓  Validation de l'analyse...")
    num_sessions = AnalysisParser.count_sessions(analysis)

    if not AnalysisParser.validate_analysis(analysis):
        print()
        response = input("   Continuer malgré les avertissements ? (y/N) : ")
        if response.lower() != "y":
            print("❌ Insertion annulée")
            sys.exit(1)
    else:
        print("   ✅ Format valide")

    # Message si mode batch
    if num_sessions > 1:
        print(f"   🔄 Mode BATCH : {num_sessions} sessions seront insérées ensemble")
    print()

    # Afficher un aperçu
    lines = analysis.split("\n")
    preview_lines = lines[:10] if len(lines) > 10 else lines
    print("📄 Aperçu de l'analyse :")
    print("-" * 60)
    for line in preview_lines:
        print(line)
    if len(lines) > 10:
        print(f"... ({len(lines) - 10} lignes supplémentaires)")
    print("-" * 60)
    print()

    if args.dry_run:
        print("🧪 Mode DRY-RUN : Aucune modification effectuée")
        print("   L'analyse est valide et prête à être insérée")
        sys.exit(0)

    # Confirmer
    if args.yes:
        print("✓ Insertion automatique activée (--yes)")
        response = "y"
    else:
        response = input("Insérer cette analyse ? (Y/n) : ")
        if response.lower() == "n":
            print("❌ Insertion annulée")
            sys.exit(0)

    print()

    # Insérer
    print("✍️  Insertion dans workouts-history.md...")
    manager = WorkoutHistoryManager(args.logs_dir, yes_confirm=args.yes)

    if manager.insert_analysis(analysis):
        print("   ✅ Analyse insérée avec succès !")
        print()

        # Afficher le diff
        print("📊 Vérification des modifications...")
        manager.show_diff()

        print()
        print("=" * 60)
        print("✅ INSERTION TERMINÉE")
        print("=" * 60)
        print()
        print("📝 ÉTAPES SUIVANTES :")
        print()
        print("1. Vérifier les modifications :")
        print(f"   git diff {args.logs_dir}/workouts-history.md")
        print()
        print("2. Ajouter au commit :")
        print(f"   git add {args.logs_dir}/workouts-history.md")
        print()
        print("3. Commit :")
        date = AnalysisParser.extract_date_from_analysis(analysis)
        print(f'   git commit -m "Analyse: Séance du {date}"')
        print()
        print("4. Push (optionnel) :")
        print("   git push")
        print()
        print("=" * 60)

    else:
        print("❌ Échec de l'insertion")
        sys.exit(1)


if __name__ == "__main__":
    main()
