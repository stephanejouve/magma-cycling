#!/usr/bin/env python3
r"""
End-of-Week Workflow Orchestrator.

Workflow automatisé complet pour transition hebdomadaire :
1. Analyse semaine écoulée (weekly-analysis)
2. Génération planning semaine suivante (weekly-planner)
3. Appel AI provider pour génération workouts
4. Validation notation (format-planning intégré)
5. Upload workouts vers Intervals.icu
6. Archivage et commit (optionnel)

Examples:
    Mode clipboard (défaut) - copier-coller manuel::

        poetry run end-of-week --week-completed S075 --week-next S076

    Mode automatique avec Claude API::

        poetry run end-of-week --week-completed S075 --week-next S076 \\
            --provider claude_api --auto

    Dry-run (simulation)::

        poetry run end-of-week --week-completed S075 --week-next S076 --dry-run

    Avec archivage automatique::

        poetry run end-of-week --week-completed S075 --week-next S076 \\
            --provider clipboard --archive

Author: Claude Code
Created: 2026-01-10
Version: 1.0.0

Metadata:
    Category: I (Integration)
    Status: Production
    Priority: P1
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from cyclisme_training_logs.config import get_data_config, get_week_config


def calculate_week_start_date(week_id: str) -> date:
    """
    Calculate Monday start date from project week ID.

    The project uses sequential week numbering with multi-season support.
    Reference dates are read from .config.json (no hardcoded dates).

    Args:
        week_id: Week identifier (e.g., "S075")

    Returns:
        Date of Monday for that week

    Raises:
        FileNotFoundError: If .config.json doesn't exist
        ValueError: If .config.json is invalid or date is not a Monday

    Examples:
        >>> calculate_week_start_date("S001")
        date(2024, 8, 5)  # Season 2024-2025: Monday Aug 5, 2024
        >>> calculate_week_start_date("S075")
        date(2026, 1, 5)  # Season 2026: Monday Jan 5, 2026
        >>> calculate_week_start_date("S076")
        date(2026, 1, 12)  # Season 2026: Monday Jan 12, 2026
    """
    # Load reference date and offset from config (multi-season aware)
    week_config = get_week_config()
    reference_date, weeks_offset = week_config.get_reference_for_week(week_id)

    # Calculate target Monday
    target_monday = reference_date + timedelta(weeks=weeks_offset)

    # Validation: must be a Monday
    if target_monday.weekday() != 0:
        raise ValueError(f"Calculated date {target_monday} is not a Monday (got {target_monday})")

    return target_monday


class EndOfWeekWorkflow:
    """Orchestrateur workflow fin de semaine."""

    def __init__(
        self,
        week_completed: str,
        week_next: str,
        provider: str = "clipboard",
        dry_run: bool = False,
        auto: bool = False,
        archive: bool = False,
    ):
        """
        Initialize workflow.

        Args:
            week_completed: Semaine terminée (e.g., "S075")
            week_next: Semaine à planifier (e.g., "S076")
            provider: AI provider (clipboard, claude_api, mistral_api)
            dry_run: Mode simulation
            auto: Mode automatique (pas de confirmation)
            archive: Archiver et commiter automatiquement
        """
        self.week_completed = week_completed
        self.week_next = week_next
        self.provider = provider
        self.dry_run = dry_run
        self.auto = auto
        self.archive = archive

        # Calculate dates automatically
        self.completed_start_date = calculate_week_start_date(week_completed)
        self.completed_end_date = self.completed_start_date + timedelta(days=6)
        self.next_start_date = calculate_week_start_date(week_next)
        self.next_end_date = self.next_start_date + timedelta(days=6)

        # Configuration
        try:
            config = get_data_config()
            self.data_dir = config.data_repo_path
            self.reports_dir = config.data_repo_path / "weekly-reports"
            self.planning_dir = config.week_planning_dir
        except Exception as e:
            print(f"❌ Erreur configuration : {e}")
            sys.exit(1)

        # État du workflow
        self.reports: dict[str, str] = {}
        self.planning_prompt: str = ""
        self.workouts_content: str = ""
        self.workouts_file: Path | None = None
        self.validation_warnings: list[str] = []

    def run(self) -> bool:
        """
        Execute workflow complet.

        Returns:
            True si succès, False sinon
        """
        print("=" * 80)
        print(f"🏁 END-OF-WEEK WORKFLOW: {self.week_completed} → {self.week_next}")
        print("=" * 80)
        print()
        print("📅 Dates calculées automatiquement:")
        print(
            f"   {self.week_completed}: {self.completed_start_date.strftime('%d/%m/%Y')} → "
            f"{self.completed_end_date.strftime('%d/%m/%Y')}"
        )
        print(
            f"   {self.week_next}: {self.next_start_date.strftime('%d/%m/%Y')} → "
            f"{self.next_end_date.strftime('%d/%m/%Y')}"
        )
        print()

        try:
            # Step 1: Analyze completed week
            if not self._step1_analyze_completed_week():
                return False

            # Step 2: Generate planning prompt for next week
            if not self._step2_generate_planning_prompt():
                return False

            # Step 3: Get workouts from AI provider
            if not self._step3_get_ai_workouts():
                return False

            # Step 4: Validate workouts notation
            if not self._step4_validate_workouts():
                return False

            # Step 5: Upload workouts to Intervals.icu
            if not self._step5_upload_workouts():
                return False

            # Step 6: Archive and commit (optional)
            if self.archive and not self.dry_run:
                self._step6_archive_and_commit()

            # Success summary
            self._print_success_summary()
            return True

        except KeyboardInterrupt:
            print("\n\n⚠️  Workflow interrompu par l'utilisateur")
            return False
        except Exception as e:
            print(f"\n❌ Erreur workflow : {e}")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            return False

    def _step1_analyze_completed_week(self) -> bool:
        """Step 1: Analyze completed week with weekly-analysis."""
        print("\n" + "=" * 80)
        print(f"📊 STEP 1/6: Analyse Semaine {self.week_completed}")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation analyse semaine")
            self.reports = {
                "bilan_final": "[DRY-RUN] Bilan final simulé",
                "transition": "[DRY-RUN] Transition simulée",
            }
            return True

        try:
            completed_week_file = (
                self.reports_dir
                / self.week_completed
                / f"bilan_final_{self.week_completed.lower()}.md"
            )

            # Check if analysis already exists
            if completed_week_file.exists():
                print(f"  ✅ Analyse {self.week_completed} déjà existante")
                print(f"  📁 {completed_week_file}")

                # Load existing reports
                self._load_existing_reports()
                return True
            else:
                print(f"  ⚠️  Analyse {self.week_completed} introuvable")
                print("  💡 Vous devez d'abord exécuter:")
                print(
                    f"     poetry run weekly-analysis --week-id {self.week_completed} "
                    f"--start-date {self.completed_start_date.strftime('%Y-%m-%d')}"
                )
                return False

        except Exception as e:
            print(f"  ❌ Erreur analyse : {e}")
            return False

    def _load_existing_reports(self):
        """Load existing reports from completed week."""
        report_files = {
            "bilan_final": f"bilan_final_{self.week_completed.lower()}.md",
            "transition": f"transition_{self.week_completed.lower()}.md",
            "workout_history": f"workout_history_{self.week_completed.lower()}.md",
            "metrics_evolution": f"metrics_evolution_{self.week_completed.lower()}.md",
        }

        week_dir = self.reports_dir / self.week_completed

        for key, filename in report_files.items():
            filepath = week_dir / filename
            if filepath.exists():
                self.reports[key] = filepath.read_text(encoding="utf-8")
            else:
                self.reports[key] = f"[{filename} non trouvé]"

    def _step2_generate_planning_prompt(self) -> bool:
        """Step 2: Generate planning prompt for next week."""
        print("\n" + "=" * 80)
        print(f"✍️  STEP 2/6: Génération Prompt Planning {self.week_next}")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation génération prompt")
            self.planning_prompt = "[DRY-RUN] Prompt simulé"
            return True

        try:
            print("  ℹ️  Pour générer le prompt, utilisez:")
            print(
                f"     poetry run weekly-planner --week-id {self.week_next} "
                f"--start-date {self.next_start_date.strftime('%Y-%m-%d')}"
            )
            print()
            print("  💡 Le prompt sera copié dans votre clipboard")
            print()

            if not self.auto:
                response = input("  Avez-vous déjà exécuté weekly-planner ? (o/n) : ")
                if response.lower() != "o":
                    print("  ⚠️  Veuillez d'abord exécuter weekly-planner")
                    return False

            # In clipboard mode, prompt is already in clipboard from weekly-planner
            print("  ✅ Prompt de planification prêt")
            return True

        except Exception as e:
            print(f"  ❌ Erreur génération prompt : {e}")
            return False

    def _step3_get_ai_workouts(self) -> bool:
        """Step 3: Get workouts from AI provider."""
        print("\n" + "=" * 80)
        print(f"🤖 STEP 3/6: Génération Workouts via {self.provider.upper()}")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation génération workouts")
            self.workouts_content = "[DRY-RUN] Workouts simulés"
            return True

        if self.provider == "clipboard":
            return self._get_workouts_clipboard()
        elif self.provider == "claude_api":
            return self._get_workouts_claude_api()
        elif self.provider == "mistral_api":
            return self._get_workouts_mistral_api()
        else:
            print(f"  ❌ Provider non supporté : {self.provider}")
            return False

    def _get_workouts_clipboard(self) -> bool:
        """Get workouts from clipboard (manual copy-paste workflow)."""
        print("  📋 Mode CLIPBOARD - Workflow manuel")
        print()
        print("  1. Collez le prompt dans votre assistant IA (Claude, Mistral, etc.)")
        print("  2. Attendez la génération des 7 workouts")
        print("  3. Copiez la réponse COMPLÈTE dans votre clipboard")
        print()

        # Save to file for traceability
        workouts_file = self.planning_dir / f"{self.week_next}_workouts.txt"
        print("  4. Sauvegardez dans un fichier:")
        print(f"     pbpaste > {workouts_file}")
        print()

        if not self.auto:
            input("  Appuyez sur ENTRÉE une fois les workouts sauvegardés...")

        # Check if file exists
        if workouts_file.exists():
            self.workouts_content = workouts_file.read_text(encoding="utf-8")
            self.workouts_file = workouts_file
            print(f"  ✅ Workouts chargés : {len(self.workouts_content)} caractères")
            return True
        else:
            print(f"  ❌ Fichier workouts introuvable : {workouts_file}")
            return False

    def _get_workouts_api(self, provider_name: str) -> bool:
        """Get workouts from any AI API provider (AI-agnostic).

        Uses AIProviderFactory for provider-agnostic implementation.

        Args:
            provider_name: Provider name (claude_api, mistral_api, openai, ollama)

        Returns:
            True if workouts generated successfully
        """
        print(f"  🤖 Mode {provider_name.upper()} - Génération automatique")
        print()

        try:
            # Import dependencies
            import os

            from cyclisme_training_logs.ai_providers.factory import AIProviderFactory
            from cyclisme_training_logs.weekly_planner import WeeklyPlanner

            # Build provider config from environment
            config = {
                "claude_api_key": os.getenv("CLAUDE_API_KEY"),
                "claude_model": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
                "mistral_api_key": os.getenv("MISTRAL_API_KEY"),
                "mistral_model": os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "openai_model": os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
                "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                "ollama_model": os.getenv("OLLAMA_MODEL", "mistral:7b"),
            }

            # Validate provider config
            is_valid, message = AIProviderFactory.validate_provider_config(provider_name, config)
            if not is_valid:
                print(f"  ❌ Configuration invalide : {message}")
                return False

            print(f"  ✅ {message}")
            print()

            # Create analyzer via factory (AI-agnostic)
            analyzer = AIProviderFactory.create(provider_name, config)
            print(f"  ℹ️  Provider: {analyzer.get_provider_info()['provider']}")
            if "model" in analyzer.get_provider_info():
                print(f"  ℹ️  Modèle: {analyzer.get_provider_info()['model']}")
            print()

            # Step 1: Generate prompt with WeeklyPlanner
            print("  📝 Génération du prompt de planification...")
            planner = WeeklyPlanner(
                week_number=self.week_next, start_date=self.next_start_date, project_root=Path.cwd()
            )

            # Collect metrics and context
            planner.current_metrics = planner.collect_current_metrics()
            planner.previous_week_bilan = planner.load_previous_week_bilan()
            planner.context_files = planner.load_context_files()

            # Generate full prompt
            prompt = planner.generate_planning_prompt()
            print(f"  ✅ Prompt généré ({len(prompt)} caractères)")
            print()

            # Step 2: Call AI API (provider-agnostic)
            print(f"  🤖 Appel {provider_name.upper()} pour génération workouts...")
            print("  ⏳ Cela peut prendre 30-60 secondes...")
            print()

            workouts_response = analyzer.analyze_session(prompt)

            print(f"  ✅ Workouts générés ({len(workouts_response)} caractères)")
            print()

            # Step 3: Save to file
            workouts_file = self.planning_dir / f"{self.week_next}_workouts.txt"
            workouts_file.write_text(workouts_response, encoding="utf-8")

            self.workouts_content = workouts_response
            self.workouts_file = workouts_file

            print(f"  💾 Workouts sauvegardés : {workouts_file}")
            print()

            return True

        except Exception as e:
            print(f"  ❌ Erreur {provider_name.upper()} : {e}")
            if self.verbose:
                import traceback

                traceback.print_exc()
            return False

    def _get_workouts_claude_api(self) -> bool:
        """Get workouts from Claude API automatically."""
        return self._get_workouts_api("claude_api")

    def _get_workouts_mistral_api(self) -> bool:
        """Get workouts from Mistral API automatically."""
        return self._get_workouts_api("mistral_api")

    def _step4_validate_workouts(self) -> bool:
        """Step 4: Validate workouts notation with format-planning logic."""
        print("\n" + "=" * 80)
        print("🔍 STEP 4/6: Validation Notation Workouts")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation validation")
            return True

        try:
            # Use upload-workouts validation (already integrated)
            # Parse workouts to validate
            from cyclisme_training_logs.upload_workouts import WorkoutUploader

            # Create temporary uploader for validation only
            dummy_date = datetime.now()
            uploader = WorkoutUploader(self.week_next, dummy_date)

            if self.workouts_file:
                workouts = uploader.parse_workouts_file(self.workouts_file)
            else:
                print("  ❌ Pas de fichier workouts à valider")
                return False

            # Validation is already done in parse_workouts_file
            if not workouts:
                print("  ❌ Validation échouée - workouts incomplets ou mal formatés")
                print("  💡 Utilisez format-planning pour corriger")
                return False

            print("  ✅ Validation réussie")
            return True

        except Exception as e:
            print(f"  ❌ Erreur validation : {e}")
            return False

    def _step5_upload_workouts(self) -> bool:
        """Step 5: Upload workouts to Intervals.icu."""
        print("\n" + "=" * 80)
        print("📤 STEP 5/6: Upload Workouts vers Intervals.icu")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation upload")
            return True

        if not self.workouts_file:
            print("  ❌ Pas de fichier workouts à uploader")
            return False

        try:
            print(
                f"  📅 Semaine : {self.week_next} "
                f"({self.next_start_date.strftime('%d/%m/%Y')} → "
                f"{self.next_end_date.strftime('%d/%m/%Y')})"
            )
            print()

            if not self.auto:
                print("  ⚠️  Upload RÉEL vers Intervals.icu")
                print(f"  📁 Fichier : {self.workouts_file}")
                print()
                response = input("  Confirmer upload ? (o/n) : ")
                if response.lower() != "o":
                    print("  ⚠️  Upload annulé")
                    return False

            # Call upload-workouts
            print()
            print("  💡 Exécutez manuellement:")
            print(
                f"     poetry run upload-workouts --week-id {self.week_next} "
                f"--start-date {self.next_start_date.strftime('%Y-%m-%d')} "
                f"--file {self.workouts_file}"
            )
            print()

            if not self.auto:
                response = input("  Upload effectué avec succès ? (o/n) : ")
                return response.lower() == "o"
            else:
                # In auto mode, assume success (TODO: call programmatically)
                return True

        except Exception as e:
            print(f"  ❌ Erreur upload : {e}")
            return False

    def _step6_archive_and_commit(self):
        """Step 6: Archive and commit (optional)."""
        print("\n" + "=" * 80)
        print("📦 STEP 6/6: Archivage et Commit")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation archivage")
            return

        print("  ℹ️  Fonctionnalité en développement")
        print("  💡 Commitez manuellement avec:")
        print(f"     git add {self.reports_dir}/{self.week_completed}/ {self.planning_dir}/")
        print(
            f'     git commit -m "feat: Complete end-of-week {self.week_completed} → {self.week_next}"'
        )
        print()

    def _print_success_summary(self):
        """Print success summary."""
        print("\n" + "=" * 80)
        print("✅ WORKFLOW TERMINÉ AVEC SUCCÈS")
        print("=" * 80)
        print()
        print(f"  📊 Semaine analysée   : {self.week_completed}")
        print(f"  📅 Semaine planifiée  : {self.week_next}")
        print(f"  🤖 Provider utilisé   : {self.provider}")
        if self.workouts_file:
            print(f"  📁 Fichier workouts   : {self.workouts_file}")
        print()
        print("  🎯 Prochaines étapes:")
        print("     1. Vérifiez les workouts dans Intervals.icu")
        print("     2. Ajustez si nécessaire avec workflow-coach en servo-mode")
        print("     3. Commitez les changements (si --archive non utilisé)")
        print()
        print("=" * 80)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="End-of-Week Workflow - Automatisation transition hebdomadaire",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:

  # Mode clipboard (défaut) - copier-coller manuel
  %(prog)s --week-completed S075 --week-next S076

  # Mode automatique avec Claude API (en développement)
  %(prog)s --week-completed S075 --week-next S076 --provider claude_api --auto

  # Dry-run (simulation)
  %(prog)s --week-completed S075 --week-next S076 --dry-run

  # Avec archivage automatique
  %(prog)s --week-completed S075 --week-next S076 --archive

Workflow complet:
  1. Analyse semaine écoulée (weekly-analysis)
  2. Génération planning semaine suivante (weekly-planner)
  3. Appel AI provider pour génération workouts
  4. Validation notation (format-planning intégré)
  5. Upload workouts vers Intervals.icu
  6. Archivage et commit (optionnel)
        """,
    )

    parser.add_argument(
        "--week-completed",
        type=str,
        required=True,
        help="Semaine terminée (format SXXX, ex: S075)",
    )

    parser.add_argument(
        "--week-next",
        type=str,
        required=True,
        help="Semaine à planifier (format SXXX, ex: S076)",
    )

    parser.add_argument(
        "--provider",
        type=str,
        choices=["clipboard", "claude_api", "mistral_api"],
        default="clipboard",
        help="AI provider pour génération workouts (défaut: clipboard)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (pas d'actions réelles)",
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Mode automatique (pas de confirmations interactives)",
    )

    parser.add_argument(
        "--archive",
        action="store_true",
        help="Archiver et commiter automatiquement",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mode verbose (affiche détails erreurs)",
    )

    return parser.parse_args()


def main():
    """Point d'entrée du script."""
    args = parse_args()

    # Validate week formats
    if not args.week_completed.startswith("S") or len(args.week_completed) != 4:
        print(f"❌ Format semaine invalide : {args.week_completed}")
        print("   Utiliser le format SXXX (ex: S075)")
        return 1

    if not args.week_next.startswith("S") or len(args.week_next) != 4:
        print(f"❌ Format semaine invalide : {args.week_next}")
        print("   Utiliser le format SXXX (ex: S076)")
        return 1

    # Check week sequence
    completed_num = int(args.week_completed[1:])
    next_num = int(args.week_next[1:])

    if next_num != completed_num + 1:
        print(f"⚠️  Attention : {args.week_next} ne suit pas {args.week_completed}")
        if not args.auto:
            response = input("Continuer quand même ? (o/n) : ")
            if response.lower() != "o":
                return 1

    # Execute workflow
    workflow = EndOfWeekWorkflow(
        week_completed=args.week_completed,
        week_next=args.week_next,
        provider=args.provider,
        dry_run=args.dry_run,
        auto=args.auto,
        archive=args.archive,
    )

    success = workflow.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
