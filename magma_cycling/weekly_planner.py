#!/usr/bin/env python3
"""
Script de Planification Hebdomadaire.

Génère un prompt pour votre assistant IA afin de créer les entraînements de la semaine.
Supporte tous les providers: Claude API, Mistral API, OpenAI, Ollama, Clipboard.
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from magma_cycling.config import create_intervals_client
from magma_cycling.utils.cli import cli_main
from magma_cycling.workflows.planner.context_loading import ContextLoadingMixin
from magma_cycling.workflows.planner.output import OutputMixin
from magma_cycling.workflows.planner.periodization import PeriodizationMixin
from magma_cycling.workflows.planner.prompt import PromptMixin


class WeeklyPlanner(
    ContextLoadingMixin,
    PeriodizationMixin,
    PromptMixin,
    OutputMixin,
):
    """Générateur de prompt pour planification hebdomadaire."""

    def __init__(self, week_number: str, start_date: datetime, project_root: Path):
        """Initialize the weekly planner.

        Args:
            week_number: Week identifier (e.g., "S074")
            start_date: Start date of the week (Monday)
            project_root: Root directory of the project
        """
        self.week_number = week_number

        self.start_date = start_date
        self.end_date = start_date + timedelta(days=6)
        self.project_root = project_root

        # Chemins importants
        self.references_dir = project_root / "references"

        # Get directories from data config
        from magma_cycling.config import get_data_config

        try:
            config = get_data_config()
            self.planning_dir = config.week_planning_dir
            self.weekly_reports_dir = config.data_repo_path / "weekly-reports"
        except FileNotFoundError:
            # Fallback to legacy paths
            self.logs_dir = project_root / "logs"
            self.planning_dir = self.logs_dir / "data" / "week_planning"
            self.weekly_reports_dir = self.logs_dir / "weekly_reports"

        self.planning_dir.mkdir(parents=True, exist_ok=True)

        # État collecté
        self.current_metrics: dict[str, Any] = {}
        self.context_files: dict[str, str] = {}
        self.previous_week_bilan = ""

        # API Intervals.icu
        self.api = None
        self._init_api()

    def _init_api(self):
        """Initialize l'API Intervals.icu (Sprint R9.B Phase 2 - centralized)."""
        try:
            self.api = create_intervals_client()
            print("✅ API Intervals.icu connectée", file=sys.stderr)
        except ValueError as e:
            print(f"⚠️ API non disponible : {e}", file=sys.stderr)
            print("   Les métriques seront approximatives", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ API non disponible : {e}", file=sys.stderr)
            print("   Les métriques seront approximatives", file=sys.stderr)

    def _previous_week_number(self) -> str:
        """Calculate le numéro de la semaine précédente."""
        current_num = int(self.week_number[1:])

        return f"S{current_num - 1:03d}"

    def _next_week_number(self) -> str:
        """Calculate le numéro de la semaine suivante."""
        current_num = int(self.week_number[1:])

        return f"S{current_num + 1:03d}"

    def _week_after_next(self) -> str:
        """Calculate le numéro de la semaine après la suivante."""
        current_num = int(self.week_number[1:])

        return f"S{current_num + 2:03d}"

    def collect_current_metrics(self) -> dict:
        """Collect les métriques actuelles depuis API."""
        print("\n📊 Collecte des métriques actuelles...", file=sys.stderr)

        if not self.api:
            print("  ⚠️ API non disponible, métriques approximatives", file=sys.stderr)
            return self._mock_current_metrics()

        try:
            # Date actuelle pour wellness
            today = datetime.now().strftime("%Y-%m-%d")

            # Wellness actuel
            wellness = self.api.get_wellness(oldest=today, newest=today)

            if wellness and len(wellness) > 0:
                current = wellness[0]

                from magma_cycling.utils.metrics import (
                    extract_wellness_metrics,
                )

                wellness_metrics = extract_wellness_metrics(current)
                metrics = {
                    "ctl": wellness_metrics["ctl"],
                    "atl": wellness_metrics["atl"],
                    "tsb": wellness_metrics["tsb"],
                    "weight": current.get("weight", 0),
                    "resting_hr": current.get("restingHR", 0),
                    "hrv": current.get("hrv", 0),
                    "date": today,
                }

                print(
                    f"  ✅ Métriques collectées (CTL: {metrics['ctl']:.0f}, TSB: {metrics['tsb']:+.0f})"
                )
                return metrics
            else:
                print("  ⚠️ Aucune donnée wellness disponible", file=sys.stderr)
                return self._mock_current_metrics()

        except Exception as e:
            print(f"  ⚠️ Erreur collecte métriques : {e}", file=sys.stderr)
            return self._mock_current_metrics()

    def _mock_current_metrics(self) -> dict:
        """Métriques mockées si API indisponible."""
        return {
            "ctl": 0,
            "atl": 0,
            "tsb": 0,
            "weight": 0,
            "resting_hr": 0,
            "hrv": 0,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "note": "Métriques approximatives (API indisponible)",
        }

    def run(self):
        """Execute le workflow complet."""
        print("=" * 70, file=sys.stderr)

        print(f"📅 PLANIFICATION HEBDOMADAIRE {self.week_number}", file=sys.stderr)
        print(
            f"Période : {self.start_date.strftime('%d/%m/%Y')} → {self.end_date.strftime('%d/%m/%Y')}"
        )
        print("=" * 70, file=sys.stderr)

        # Étape 1 : Collecter métriques
        self.current_metrics = self.collect_current_metrics()

        # Étape 2 : Charger bilan semaine précédente
        self.previous_week_bilan = self.load_previous_week_bilan()

        # Étape 3 : Charger contexte
        self.context_files = self.load_context_files()

        # Étape 4 : Générer prompt
        prompt = self.generate_planning_prompt()

        # Étape 4.5 : Créer JSON template du planning
        self.save_planning_json()

        # Étape 5 : Copier dans presse-papier
        print("\n📋 Copie dans le presse-papier...", file=sys.stderr)
        if self.copy_to_clipboard(prompt):
            print("  ✅ Prompt copié (Cmd+V pour coller)", file=sys.stderr)
        else:
            print("  ⚠️ Copie manuelle nécessaire", file=sys.stderr)
            print("\n" + "=" * 70, file=sys.stderr)
            print(prompt, file=sys.stderr)
            print("=" * 70, file=sys.stderr)

        # Instructions
        print("\n" + "=" * 70, file=sys.stderr)
        print("📝 PROCHAINES ÉTAPES (MÉTHODE RECOMMANDÉE) :", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(file=sys.stderr)
        print("1. Choisir votre assistant IA (Claude, Mistral, OpenAI, Ollama)", file=sys.stderr)
        print("2. Coller le prompt (Cmd+V)", file=sys.stderr)
        print("3. Attendre que l'IA génère les 7 entraînements", file=sys.stderr)
        print("4. Copier la réponse COMPLÈTE de l'IA", file=sys.stderr)
        print(file=sys.stderr)
        print("5. Sauvegarder dans un fichier :", file=sys.stderr)
        workouts_file = self.planning_dir / f"{self.week_number}_workouts.txt"
        print(f"   pbpaste > {workouts_file}", file=sys.stderr)
        print(file=sys.stderr)
        print("6. Uploader depuis le fichier (PLUS FIABLE que clipboard) :", file=sys.stderr)
        print(f"   poetry run upload-workouts --week-id {self.week_number} \\", file=sys.stderr)
        print(f"     --start-date {self.start_date.strftime('%Y-%m-%d')} \\", file=sys.stderr)
        print(f"     --file {workouts_file}", file=sys.stderr)
        print(file=sys.stderr)
        print("💡 Pourquoi utiliser --file ?", file=sys.stderr)
        print("   • Clipboard volatile (peut être écrasé)", file=sys.stderr)
        print("   • Fichier = traçabilité et possibilité de rejouer", file=sys.stderr)
        print("   • Moins d'erreurs de manipulation", file=sys.stderr)
        print(file=sys.stderr)
        print("💡 Tip: Utilisez 'workflow-coach' pour automatisation complète", file=sys.stderr)
        print(file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"✅ Planification {self.week_number} prête !", file=sys.stderr)
        print("=" * 70, file=sys.stderr)


@cli_main
def main():
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(
        description="Générer prompt de planification hebdomadaire pour assistant IA"
    )
    parser.add_argument(
        "--week-id", type=str, required=True, help="Numéro de semaine (format SXXX, ex: S072)"
    )
    parser.add_argument(
        "--start-date", type=str, required=True, help="Date de début (lundi) au format YYYY-MM-DD"
    )
    parser.add_argument(
        "--project-root", type=str, help="Racine du projet (défaut: répertoire parent du script)"
    )

    args = parser.parse_args()

    # Validation format semaine
    if not args.week_id.startswith("S") or len(args.week_id) != 4:
        print(f"❌ Format semaine invalide : {args.week_id}", file=sys.stderr)
        print("   Utiliser le format SXXX (ex: S072)", file=sys.stderr)
        sys.exit(1)

    # Parsing date
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Format date invalide : {args.start_date}", file=sys.stderr)
        print("   Utiliser le format YYYY-MM-DD (ex: 2024-11-24)", file=sys.stderr)
        sys.exit(1)

    # Vérifier que c'est un lundi
    if start_date.weekday() != 0:
        print(f"⚠️ Attention : {args.start_date} n'est pas un lundi", file=sys.stderr)
        print(f"   Jour détecté : {start_date.strftime('%A')}", file=sys.stderr)
        response = input("Continuer quand même ? (o/n) : ")
        if response.lower() != "o":
            sys.exit(0)

    # Déterminer project_root
    if args.project_root:
        project_root = Path(args.project_root)
    else:
        project_root = Path(__file__).parent.parent

    if not project_root.exists():
        print(f"❌ Répertoire projet non trouvé : {project_root}", file=sys.stderr)
        sys.exit(1)

    # Exécuter planification
    planner = WeeklyPlanner(args.week_id, start_date, project_root)
    planner.run()


if __name__ == "__main__":
    main()
