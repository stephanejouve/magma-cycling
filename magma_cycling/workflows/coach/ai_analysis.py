"""AI analysis preparation and execution methods for WorkflowCoach."""

import json
import logging
import subprocess
import sys
from pathlib import Path

from magma_cycling.ai_providers import AIProviderFactory
from magma_cycling.config import get_data_config
from magma_cycling.prompts.prompt_builder import build_prompt, load_current_metrics

logger = logging.getLogger(__name__)


class AIAnalysisMixin:
    """AI analysis preparation, execution, metrics extraction, and posting."""

    def step_3_prepare_analysis(self):
        """Étape 3 : Préparer le prompt d'analyse."""
        self.clear_screen()

        self.print_header("📝 Préparation Prompt d'Analyse", "Étape 3/7 : Génération du prompt")

        print("Récupération de la séance depuis Intervals.icu...")
        print("Génération du prompt optimisé pour l'IA...")
        print()
        print("⏱️  Temps estimé : 10 secondes")
        self.print_separator()

        # Construire la commande - Module import au lieu de path absolu
        cmd = [sys.executable, "-m", "magma_cycling.prepare_analysis"]
        if self.activity_id:
            cmd.extend(["--activity-id", self.activity_id])

        result = subprocess.run(cmd)

        if result.returncode != 0:
            print()
            print("❌ Erreur lors de la préparation du prompt.")
            print("   Vérifier la configuration Intervals.icu et réessayer.")
            sys.exit(1)

        print()
        print("✅ Prompt généré !")

        # Read prompt from clipboard (prepare_analysis.py copied it there)
        try:
            clipboard = subprocess.run(["pbpaste"], capture_output=True, text=True)
            prompt = clipboard.stdout

            # Extract activity name from prompt
            for line in prompt.split("\n"):
                if line.strip().startswith("- **Nom** :"):
                    self.activity_name = line.split(":", 1)[1].strip()
                    break
        except Exception as e:
            logger.error(f"Failed to read prompt from clipboard: {e}")
            print(f"❌ Erreur lecture prompt: {e}")
            sys.exit(1)

        # Display activity name if found
        if self.activity_name:
            print()
            print("=" * 70)
            print("🚴 SÉANCE EN COURS D'ANALYSE")
            print("=" * 70)
            print(f"\n{self.activity_name}\n")
            print("=" * 70)

        print()
        print(f"🤖 Provider IA : {self.current_provider}")
        print()

        # Execute analysis based on provider type
        if self.current_provider == "clipboard":
            # Clipboard workflow: user pastes in IA manually
            print("✅ Prompt copié dans le presse-papier")
            print()
            print("📋 Instructions :")
            print("   1. Ouvrez votre IA (Claude.ai, ChatGPT, etc.)")
            print("   2. Collez le prompt (Cmd+V)")
            print("   3. Attendez la réponse complète")
            print("   4. Copiez TOUTE la réponse (Cmd+A puis Cmd+C)")
            print("   5. Revenez ici et appuyez sur ENTRÉE")
            print()
            self.wait_user()
        else:
            # API workflow: automatic execution
            print("⏳ Envoi du prompt à l'IA...")
            print("   Cela peut prendre 30-60 secondes...")
            print()

            try:
                current_metrics = load_current_metrics()
                system_prompt, _ = build_prompt(
                    mission="daily_feedback",
                    current_metrics=current_metrics,
                    workflow_data="",
                )
                self.analysis_result = self.ai_analyzer.analyze_session(
                    prompt, dataset=None, system_prompt=system_prompt
                )
                print("✅ Analyse terminée !")
                print(f"   Longueur réponse : {len(self.analysis_result)} caractères")
                print()
                self.wait_user()
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")

                # Check if fallback is possible
                fallback_chain = self.ai_config.get_fallback_chain()
                next_provider = None

                try:
                    current_idx = fallback_chain.index(self.current_provider)
                    if current_idx + 1 < len(fallback_chain):
                        next_provider = fallback_chain[current_idx + 1]
                except (ValueError, IndexError):
                    pass

                # If fallback available, ask user consent
                if next_provider and self.ai_config.enable_fallback:
                    choice = self._ask_fallback_consent(
                        failed_provider=self.current_provider,
                        next_provider=next_provider,
                        error_msg=str(e),
                    )

                    if choice == "F":
                        # Fallback to next provider
                        print()
                        print(f"🔄 Basculement vers provider de secours : {next_provider}")
                        print()

                        self.current_provider = next_provider
                        provider_config = self.ai_config.get_provider_config(next_provider)
                        self.ai_analyzer = AIProviderFactory.create(next_provider, provider_config)

                        # Retry
                        self.step_3_prepare_analysis()
                        return

                    elif choice == "C":
                        # Switch to clipboard
                        print()
                        print("📋 Basculement vers mode manuel (clipboard)")
                        print()

                        self.current_provider = "clipboard"
                        self.ai_analyzer = AIProviderFactory.create("clipboard", {})

                        # Retry
                        self.step_3_prepare_analysis()
                        return

                    else:  # choice == 'Q'
                        print()
                        print("👋 Workflow interrompu par l'utilisateur")
                        sys.exit(0)
                else:
                    # No fallback available
                    print(f"❌ Erreur lors de l'analyse IA : {e}")
                    print()
                    print("💡 Conseil : Utilisez --provider clipboard pour le mode manuel")
                    sys.exit(1)

    def _detect_week_id(self) -> str:
        """Détecte ou demande le week_id.

        Returns:
            Week ID (ex: "S070")
        """
        # Si week_id fourni en argument CLI

        if self.week_id:
            return self.week_id

        # Sinon, demander à l'utilisateur
        print("\n💡 Pour le mode réconciliation, un identifiant de semaine est requis")
        week_id = input("Identifiant semaine (ex: S070) : ").strip().upper()

        if not week_id.startswith("S"):
            week_id = "S" + week_id

        return week_id

    def _check_planning_available(self) -> bool:
        """Vérifie si un planning hebdomadaire est disponible.

        Returns:
            True si planning trouvé, False sinon.
        """
        if not self.week_id:
            week_id = self._detect_week_id()
        else:
            week_id = self.week_id

        config = get_data_config()
        planning_dir = config.week_planning_dir
        planning_file = planning_dir / f"week_planning_{week_id}.json"

        return planning_file.exists()

    def _extract_metrics_from_analysis(self) -> dict:
        """Extract key metrics from markdown analysis.

        Returns:
            Dict with tsb, sleep_hours, rpe, decoupling, avg_hr extracted from analysis_result.
        """
        import re

        metrics = {
            "tsb": None,
            "sleep_hours": None,
            "rpe": None,
            "decoupling": None,
            "avg_hr": None,
        }

        if not hasattr(self, "analysis_result") or not self.analysis_result:
            return metrics

        analysis = self.analysis_result

        # Extract TSB (format: "TSB : +6" or "TSB : -3")
        tsb_match = re.search(r"TSB\s*:\s*([+-]?\d+)", analysis)
        if tsb_match:
            metrics["tsb"] = int(tsb_match.group(1))

        # Extract sleep (format: "Sommeil : 7.5h" or "Sommeil : 0.0h")
        sleep_match = re.search(r"Sommeil\s*:\s*(\d+\.?\d*)h", analysis)
        if sleep_match:
            metrics["sleep_hours"] = float(sleep_match.group(1))

        # Extract decoupling (format: "Découplage : 11.2%" or "Découplage cardiovasculaire : 5.8%")
        decoupling_match = re.search(r"Découplage[^:]*:\s*(\d+\.?\d*)%", analysis)
        if decoupling_match:
            metrics["decoupling"] = float(decoupling_match.group(1))

        # Extract avg HR (format: "FC moyenne : 93bpm")
        hr_match = re.search(r"FC moyenne\s*:\s*(\d+)bpm", analysis)
        if hr_match:
            metrics["avg_hr"] = int(hr_match.group(1))

        # Try to get RPE from feedback file if not in analysis
        try:
            feedback_file = Path(".athlete_feedback") / "last_feedback.json"
            if feedback_file.exists():
                with open(feedback_file, encoding="utf-8") as f:
                    feedback = json.load(f)
                    metrics["rpe"] = feedback.get("rpe")
        except Exception:
            pass

        return metrics

    def _prompt_sleep_if_missing(self, sleep_hours: float | None) -> float:
        """Prompt athlete for sleep duration if missing from Intervals.icu.

        Args:
            sleep_hours: Sleep hours from Intervals.icu (or None)

        Returns:
            float: Sleep hours (from user input or original value)
        """
        # If sleep data is available and > 0, return as-is
        if sleep_hours and sleep_hours > 0:
            return sleep_hours

        print()
        print("⚠️  Données de sommeil non disponibles dans Intervals.icu")
        print("   Pour une recommandation plus précise, tu peux saisir la durée de sommeil.")
        print()

        while True:
            sleep_input = input("   Sommeil (format 7h30, ou Entrée pour ignorer) : ").strip()

            if not sleep_input:
                # User skipped, return 0.0
                return 0.0

            # Parse format "7h30", "7h", "7.5", "7,5"
            try:
                # Try formats: "7h30", "7h", "7.5"
                if "h" in sleep_input:
                    parts = sleep_input.lower().replace("h", ":").split(":")
                    hours = float(parts[0])
                    minutes = float(parts[1]) if len(parts) > 1 else 0.0
                    total_hours = hours + (minutes / 60.0)
                    return round(total_hours, 1)
                else:
                    # Try direct decimal: "7.5" or "7,5"
                    return round(float(sleep_input.replace(",", ".")), 1)
            except ValueError:
                print("   ⚠️  Format invalide. Exemples: 7h30, 7h, 7.5")

    def _post_analysis_to_intervals(self):
        """Poste l'analyse comme note dans Intervals.icu.

        Returns:
            bool: True si succès, False sinon
        """
        from datetime import datetime

        if not self.activity_id:
            logger.warning("No activity_id available, skipping Intervals.icu note posting")
            return False

        # Get analysis text
        analysis_text = None
        if hasattr(self, "analysis_result") and self.analysis_result:
            analysis_text = self.analysis_result
        else:
            try:
                result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
                analysis_text = result.stdout
            except Exception as e:
                logger.error(f"Failed to read analysis from clipboard: {e}")
                return False

        if not analysis_text or len(analysis_text.strip()) < 50:
            logger.warning("Analysis text too short or empty, skipping Intervals.icu posting")
            return False

        # Prepare note content
        note_content = f"""## 📊 Analyse Coach IA

{analysis_text}

---
*Analyse générée automatiquement par Cyclisme Training Logs*
*Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

        # POST note via API client
        try:
            api = self._get_api()
            return api.create_activity_note(self.activity_id, note_content)
        except Exception as e:
            logger.error(f"Exception posting note to Intervals.icu: {e}")
            return False
