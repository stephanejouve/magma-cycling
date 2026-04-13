"""AI workout generation methods for EndOfWeekWorkflow."""

import sys

from magma_cycling.paths import get_project_root
from magma_cycling.prompts.prompt_builder import build_prompt, load_current_metrics


class AIWorkoutsMixin:
    """Génération de workouts via AI providers (clipboard, Claude, Mistral)."""

    def _step2_generate_planning_prompt(self) -> bool:
        """Step 2: Generate planning prompt for next week."""
        print("\n" + "=" * 80)
        print(f"✍️  STEP 2/7: Génération Prompt Planning {self.week_next}")
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
        print(f"🤖 STEP 3/7: Génération Workouts via {self.provider.upper()}")
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
            from magma_cycling.ai_providers.factory import AIProviderFactory
            from magma_cycling.config import get_ai_config
            from magma_cycling.weekly_planner import WeeklyPlanner

            # Get provider config from centralized AI configuration
            config = get_ai_config().get_provider_config(provider_name)

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
                week_number=self.week_next,
                start_date=self.next_start_date,
                project_root=get_project_root(),
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

            current_metrics = load_current_metrics()
            system_prompt, _ = build_prompt(
                mission="weekly_planning",
                current_metrics=current_metrics,
                workflow_data="",
            )
            workouts_response = analyzer.analyze_session(prompt, system_prompt=system_prompt)

            print(f"  ✅ Workouts générés ({len(workouts_response)} caractères)")
            print()

            # Step 3: Save to file (with backup)
            from magma_cycling.planning.backup import safe_write

            workouts_file = self.planning_dir / f"{self.week_next}_workouts.txt"
            safe_write(workouts_file, workouts_response)

            self.workouts_content = workouts_response
            self.workouts_file = workouts_file

            print(f"  💾 Workouts sauvegardés : {workouts_file}")
            print()

            return True

        except Exception as e:
            print(f"  ❌ Erreur {provider_name.upper()} : {e}")
            if "--verbose" in sys.argv:
                import traceback

                traceback.print_exc()
            return False

    def _get_workouts_claude_api(self) -> bool:
        """Get workouts from Claude API automatically."""
        return self._get_workouts_api("claude_api")

    def _get_workouts_mistral_api(self) -> bool:
        """Get workouts from Mistral API automatically."""
        return self._get_workouts_api("mistral_api")
