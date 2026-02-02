#!/usr/bin/env python3
r"""
End-of-Week Workflow Orchestrator.

Workflow automatisé complet pour transition hebdomadaire :
1. Analyse semaine écoulée (weekly-analysis)
1b. Évaluation PID & Training Intelligence (pid-daily-evaluation)
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


def calculate_weekly_transition(reference_date: date | None = None) -> tuple[str, str, date, date]:
    """
    Calculate week IDs for weekly transition (completed → next).

    Logic:
    - If Sunday (day 6) or Monday (day 0): transition from current week to next
    - Otherwise: transition from current week to next (for manual runs)

    Args:
        reference_date: Reference date for calculation (default: today)

    Returns:
        Tuple of (week_completed, week_next, completed_start_date, next_start_date)

    Examples:
        >>> # Running on Sunday 2026-01-25 or Monday 2026-01-26
        >>> calculate_weekly_transition(date(2026, 1, 25))
        ('S077', 'S078', date(2026, 1, 19), date(2026, 1, 26))
    """
    if reference_date is None:
        reference_date = date.today()

    # Get week config
    week_config = get_week_config()
    s001_date = week_config.get_s001_date_obj("S001")

    # Calculate weeks offset from S001
    delta = reference_date - s001_date
    weeks_offset = delta.days // 7

    # Current week is the week containing reference_date
    current_week_num = weeks_offset + 1
    week_completed = f"S{current_week_num:03d}"
    week_next = f"S{current_week_num + 1:03d}"

    # Calculate start dates
    completed_start_date = s001_date + timedelta(weeks=weeks_offset)
    next_start_date = s001_date + timedelta(weeks=weeks_offset + 1)

    return week_completed, week_next, completed_start_date, next_start_date


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

            # Step 1b: PID evaluation and intelligence learning
            if not self._step1b_pid_evaluation():
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

            # Step 5b: Save planning JSON with uploaded workouts data
            if not self.dry_run:
                self._step5b_save_planning_json()

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
                # Analysis doesn't exist - run it automatically
                print(f"  ⚠️  Analyse {self.week_completed} introuvable")
                print("  🤖 Lancement automatique de weekly-analysis...")
                print()

                try:
                    from cyclisme_training_logs.workflows.workflow_weekly import (
                        run_weekly_analysis,
                    )

                    # Run weekly-analysis programmatically (Phase 2 - modern system)
                    run_weekly_analysis(
                        week=self.week_completed,
                        start_date=self.completed_start_date,
                        data_dir=self.data_dir,
                        ai_analysis=False,
                    )

                    # Verify that analysis was created
                    if completed_week_file.exists():
                        print()
                        print(f"  ✅ Analyse {self.week_completed} générée avec succès")
                        print(f"  📁 {completed_week_file}")

                        # Load newly created reports
                        self._load_existing_reports()
                        return True
                    else:
                        print()
                        print("  ❌ Erreur : fichier bilan_final non créé")
                        return False

                except Exception as e:
                    print()
                    print(f"  ❌ Erreur lors de weekly-analysis : {e}")
                    if "--verbose" in sys.argv:
                        import traceback

                        traceback.print_exc()
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

    def _step1b_pid_evaluation(self) -> bool:
        """Step 1b: PID evaluation and intelligence learning."""
        print("\n" + "=" * 80)
        print("🧠 STEP 1b/6: Évaluation PID & Training Intelligence")
        print("=" * 80)
        print()

        if self.dry_run:
            print("🔍 DRY-RUN: Simulation évaluation PID")
            return True

        try:
            print("  ℹ️  Collecte des métriques d'entraînement...")
            print(f"  📅 Période: {self.completed_start_date} → {self.completed_end_date}")
            print()

            # Import and run PID evaluation
            from cyclisme_training_logs.scripts.pid_daily_evaluation import (
                PIDDailyEvaluator,
            )

            evaluator = PIDDailyEvaluator(dry_run=False)

            # Run evaluation for the completed week
            result = evaluator.run_daily_evaluation(days_back=7)

            print()
            print("  ✅ Évaluation PID terminée")
            print("  📊 Données sauvegardées dans ~/data/monitoring/pid_evaluation.jsonl")
            print("  🧠 Intelligence mise à jour dans ~/data/intelligence.json")

            # Display test recommendation if present
            test_rec = result.get("test_recommendation")
            if test_rec:
                print()
                print("  " + "=" * 76)
                print(f"  🎯 RECOMMANDATION DÉTECTÉE: {test_rec['status']}")
                print("  " + "=" * 76)
                print(f"  💡 {test_rec['message']}")
                print(f"  📅 {test_rec['timing']}")
                print(f"  ⏰ Dernier test: {test_rec['weeks_since_test']:.1f} semaines")
                print(f"  💪 TSB actuel: {test_rec['tsb']:.1f}")
                print("  " + "=" * 76)

            return True

        except Exception as e:
            print(f"  ⚠️  Erreur évaluation PID (non bloquant) : {e}")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            # Non-blocking: continue workflow even if PID evaluation fails
            return True

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

            if self.auto:
                # Auto mode: call upload programmatically
                print("  🤖 Mode automatique - Upload programmatique")
                print(f"  📁 Fichier : {self.workouts_file}")
                print()

                from cyclisme_training_logs.upload_workouts import WorkoutUploader

                uploader = WorkoutUploader(self.week_next, self.next_start_date)
                workouts = uploader.parse_workouts_file(self.workouts_file)

                if not workouts:
                    print("  ❌ Erreur parsing workouts")
                    return False

                print(f"  📊 {len(workouts)} workouts à uploader")
                print()

                # Upload all workouts
                result = uploader.upload_all(workouts, dry_run=False)

                print()
                print(f"  ✅ Upload réussi : {result['success']}/{result['total']}")
                if result["errors"]:
                    print(f"  ⚠️  Erreurs : {len(result['errors'])}")
                    for error in result["errors"]:
                        print(f"     • {error}")

                return result["success"] == result["total"]
            else:
                # Manual mode: prompt user to upload manually
                print("  ⚠️  Upload RÉEL vers Intervals.icu")
                print(f"  📁 Fichier : {self.workouts_file}")
                print()
                response = input("  Confirmer upload ? (o/n) : ")
                if response.lower() != "o":
                    print("  ⚠️  Upload annulé")
                    return False

                print()
                print("  💡 Exécutez manuellement:")
                print(
                    f"     poetry run upload-workouts --week-id {self.week_next} "
                    f"--start-date {self.next_start_date.strftime('%Y-%m-%d')} "
                    f"--file {self.workouts_file}"
                )
                print()

                response = input("  Upload effectué avec succès ? (o/n) : ")
                return response.lower() == "o"

        except Exception as e:
            print(f"  ❌ Erreur upload : {e}")
            return False

    def _step5b_save_planning_json(self):
        """Step 5b: Save planning JSON with real uploaded workout data."""
        print("\n" + "=" * 80)
        print("💾 STEP 5b/6: Sauvegarde Planning JSON")
        print("=" * 80)
        print()

        try:
            if not self.workouts_file:
                print("  ⚠️  Pas de fichier workouts - JSON template déjà créé")
                return

            # Import dependencies
            import json
            import re

            from cyclisme_training_logs.api.intervals_client import IntervalsClient
            from cyclisme_training_logs.config import get_intervals_config

            # Parse workouts file to extract metadata
            print("  📄 Parsing fichier workouts...")
            workouts_text = self.workouts_file.read_text(encoding="utf-8")

            workout_metadata = {}
            for match in re.finditer(
                r"=== WORKOUT (S\d+-\d+-\w+-\w+-V\d+) ===\s*\n\s*(.+?)\((\d+)min, (\d+) TSS\)",
                workouts_text,
            ):
                workout_id = match.group(1)
                name_desc = match.group(2).strip()
                duration = int(match.group(3))
                tss = int(match.group(4))
                workout_metadata[workout_id] = {
                    "name_full": name_desc,
                    "duration_min": duration,
                    "tss_planned": tss,
                }

            print(f"     ✓ {len(workout_metadata)} workouts parsés")

            # Get uploaded events from Intervals.icu
            print("  🌐 Récupération events Intervals.icu...")
            config = get_intervals_config()
            client = IntervalsClient(athlete_id=config.athlete_id, api_key=config.api_key)

            events = client.get_events(
                oldest=self.next_start_date.isoformat(),
                newest=self.next_end_date.isoformat(),
            )

            workouts = [
                e
                for e in events
                if e.get("category") == "WORKOUT" and e.get("name", "").startswith(self.week_next)
            ]
            workouts_sorted = sorted(workouts, key=lambda x: x.get("start_date_local", ""))

            print(f"     ✓ {len(workouts_sorted)} workouts uploadés")

            # Build planning data structure
            planning_data = {
                "week_id": self.week_next,
                "start_date": self.next_start_date.isoformat(),
                "end_date": self.next_end_date.isoformat(),
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": 1,
                "athlete_id": config.athlete_id,
                "tss_target": 0,
                "planned_sessions": [],
            }

            tss_total = 0

            for workout in workouts_sorted:
                workout_name = workout.get("name", "")
                # Parse: S079-01-END-RepriseDouceLundi-V001
                match = re.match(r"(S\d+-\d+)-(\w+)-(.+?)-(V\d+)", workout_name)
                if not match:
                    print(f"     ⚠️  Format invalide: {workout_name}")
                    continue

                session_id = match.group(1)  # S079-01
                workout_type = match.group(2)  # END
                workout_name_part = match.group(3)  # RepriseDouceLundi
                version = match.group(4)  # V001

                # Get metadata from parsing
                meta = workout_metadata.get(workout_name, {})
                tss = meta.get("tss_planned", 0)
                duration = meta.get("duration_min", 0)
                description = meta.get("name_full", workout_name_part)

                tss_total += tss

                workout_date = workout.get("start_date_local", "").split("T")[0]

                session = {
                    "session_id": session_id,
                    "date": workout_date,
                    "name": workout_name_part,
                    "type": workout_type,
                    "version": version,
                    "tss_planned": tss,
                    "duration_min": duration,
                    "description": description,
                    "status": "pending",
                    "intervals_id": workout.get("id"),
                    "description_hash": None,
                }
                planning_data["planned_sessions"].append(session)

            planning_data["tss_target"] = tss_total

            # Save JSON file
            json_file = self.planning_dir / f"week_planning_{self.week_next}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(planning_data, f, indent=2, ensure_ascii=False)

            print()
            print(f"  ✅ Planning JSON créé: {json_file}")
            print(f"     • {len(planning_data['planned_sessions'])} sessions")
            print(f"     • TSS total: {tss_total}")

        except Exception as e:
            print(f"  ⚠️  Erreur sauvegarde JSON (non bloquant): {e}")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            # Non-blocking: continue workflow even if JSON save fails

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
        required=False,
        help="Semaine terminée (format SXXX, ex: S075). Optionnel si --auto-calculate",
    )

    parser.add_argument(
        "--week-next",
        type=str,
        required=False,
        help="Semaine à planifier (format SXXX, ex: S076). Optionnel si --auto-calculate",
    )

    parser.add_argument(
        "--auto-calculate",
        action="store_true",
        help="Auto-calculer les week-ids à partir de la date du jour (pas de hard-coding)",
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

    # Auto-calculate week-ids if requested
    if args.auto_calculate:
        if args.week_completed or args.week_next:
            print("⚠️  --auto-calculate ignore les --week-completed et --week-next fournis")

        week_completed, week_next, completed_start, next_start = calculate_weekly_transition()
        print("ℹ️  Transition auto-calculée:")
        print(f"   • Semaine complétée: {week_completed} (début: {completed_start})")
        print(f"   • Semaine suivante:  {week_next} (début: {next_start})")
        print()
    else:
        # Manual mode - validate required args
        if not args.week_completed or not args.week_next:
            print("❌ Erreur: --week-completed et --week-next sont requis")
            print("   Ou utilisez --auto-calculate pour calcul automatique")
            return 1

        week_completed = args.week_completed
        week_next = args.week_next

        # Validate week formats
        if not week_completed.startswith("S") or len(week_completed) != 4:
            print(f"❌ Format semaine invalide : {week_completed}")
            print("   Utiliser le format SXXX (ex: S075)")
            return 1

        if not week_next.startswith("S") or len(week_next) != 4:
            print(f"❌ Format semaine invalide : {week_next}")
            print("   Utiliser le format SXXX (ex: S076)")
            return 1

        # Check week sequence
        completed_num = int(week_completed[1:])
        next_num = int(week_next[1:])

        if next_num != completed_num + 1:
            print(f"⚠️  Attention : {week_next} ne suit pas {week_completed}")
            if not args.auto:
                response = input("Continuer quand même ? (o/n) : ")
                if response.lower() != "o":
                    return 1

    # Execute workflow
    workflow = EndOfWeekWorkflow(
        week_completed=week_completed,
        week_next=week_next,
        provider=args.provider,
        dry_run=args.dry_run,
        auto=args.auto,
        archive=args.archive,
    )

    success = workflow.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
