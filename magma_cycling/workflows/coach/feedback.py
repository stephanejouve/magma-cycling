"""Feedback collection methods for WorkflowCoach."""

import subprocess
import sys


class FeedbackMixin:
    """Athlete feedback collection workflow."""

    def _validate_feedback_collection(self) -> tuple[bool, str | None]:
        """Validate if feedback collection should proceed.

        Returns:
            Tuple of (should_collect, skip_reason)
        """
        # Check skip flag

        if self.skip_feedback:
            return False, "skipped_by_flag"

        # Check if gaps detected
        if not self.unanalyzed_activities or len(self.unanalyzed_activities) == 0:
            return False, "no_gaps"

        return True, None

    def _prepare_feedback_context(self) -> tuple[dict | None, str, str]:
        """Prepare context for feedback collection (credentials + activity).

        Returns:
            Tuple of (activity, athlete_id, api_key)
        """
        try:
            # Load credentials
            athlete_id, api_key = self.load_credentials()

            if not athlete_id or not api_key:
                return None, "", ""

            # Get first unanalyzed activity for context
            activity = None
            if self.unanalyzed_activities and len(self.unanalyzed_activities) > 0:
                activity = self.unanalyzed_activities[0]

            return activity, athlete_id, api_key

        except Exception as e:
            print(f"⚠️  Erreur lors de la récupération du contexte : {e}")
            return None, "", ""

    def _execute_feedback_collection(self, activity: dict | None, mode: str) -> int:
        """Execute feedback collection subprocess.

        Args:
            activity: Activity dict with context (or None for no context)
            mode: Collection mode ("quick" or "full")

        Returns:
            Return code from subprocess (0 = success)
        """
        cmd = [sys.executable, "-m", "magma_cycling.collect_athlete_feedback"]

        # Add activity context if available
        if activity:
            print()
            print(
                f"✓ Contexte : {activity.get('name', 'Séance')} du {activity.get('start_date_local', '')[:10]}"
            )

            cmd.extend(
                [
                    "--activity-name",
                    activity.get("name", "Séance"),
                    "--activity-date",
                    activity.get("start_date_local", ""),
                    "--activity-duration",
                    str(activity.get("moving_time", 0) // 60),
                    "--activity-tss",
                    str(int(activity.get("icu_training_load", 0))),
                ]
            )

            # Add IF if available
            if activity.get("icu_intensity"):
                if_value = activity.get("icu_intensity", 0) / 100.0
                cmd.extend(["--activity-if", f"{if_value:.2f}"])

        # Add mode flag
        if mode == "quick":
            cmd.append("--quick")

        # Execute subprocess
        result = subprocess.run(cmd)
        return result.returncode

    def step_2_collect_feedback(self):
        """Étape 2 : Collecter le feedback athlète."""
        # 1. Validate if feedback collection should proceed

        should_collect, skip_reason = self._validate_feedback_collection()

        if not should_collect:
            if skip_reason == "skipped_by_flag":
                self.clear_screen()
                self.print_header(
                    "⏭️  Feedback Athlète (Skip)", "Étape 2/7 : Collecte feedback (optionnel)"
                )
                print("Le feedback athlète a été skippé (--skip-feedback).")
                print("L'analyse sera basée uniquement sur les métriques objectives.")
                self.wait_user()
            # For "no_gaps", skip silently
            return

        # 2. Display header and prompt user
        self.clear_screen()
        self.print_header(
            "💭 Collecte Feedback Athlète", "Étape 2/7 : Ressenti subjectif (optionnel)"
        )

        gap_count = len(self.unanalyzed_activities)
        print(f"📊 {gap_count} séance(s) non analysée(s) détectée(s)")
        print()
        print("Veux-tu enrichir l'analyse avec ton ressenti sur la séance ?")
        print()
        print("✅ Avantages :")
        print("   • Claude croise métriques objectives + ressenti subjectif")
        print("   • Analyse plus personnalisée et pertinente")
        print("   • Détection des écarts perception/réalité")
        print()
        print("⏱️  Temps estimé : 30 secondes (quick) ou 2-3 min (full)")
        print()

        collect = input("Collecter le feedback ? (o/n) : ").strip().lower()

        if collect != "o":
            print()
            print("⏭️  Feedback skippé. L'analyse sera basée sur les métriques.")
            self.wait_user()
            return

        # 3. Get collection mode
        print()
        print("Mode feedback :")
        print("  1 - Quick (30s) : RPE + ressenti général")
        print("  2 - Full (2-3min) : RPE + ressenti + difficultés + contexte + sensations")
        mode_choice = input("Choix (1/2) : ").strip()

        mode = "quick" if mode_choice == "1" else "full"
        print()
        print(f"Lancement de collect_athlete_feedback.py (mode {mode})...")
        self.print_separator()

        # 4. Prepare context
        activity, athlete_id, api_key = self._prepare_feedback_context()

        if not activity:
            print()
            print("⚠️  Contexte activité non disponible → Feedback sans contexte")

        # 5. Execute feedback collection
        returncode = self._execute_feedback_collection(activity, mode)

        # 6. Display result
        if returncode != 0:
            print()
            print("⚠️  Erreur lors de la collecte du feedback.")
            print("    L'analyse continuera sans feedback.")
            self.wait_user()
        else:
            print()
            print("✅ Feedback collecté et sauvegardé !")
            self.wait_user()

    def _ask_fallback_consent(
        self, failed_provider: str, next_provider: str, error_msg: str
    ) -> str:
        """Ask user consent before falling back to another provider.

        Args:
            failed_provider: The provider that failed
            next_provider: The next provider in fallback chain
            error_msg: Error message from the failed provider

        Returns:
            User choice: 'F' (Fallback), 'C' (Clipboard), 'Q' (Quit).
        """
        print()

        print("=" * 70)
        print(f"⚠️  ÉCHEC DU PROVIDER : {failed_provider}")
        print("=" * 70)
        print()
        print(f"Erreur : {error_msg}")
        print()
        print("🔀 OPTIONS DISPONIBLES :")
        print()
        print(f"  [F] Fallback  - Essayer {next_provider} (provider suivant)")
        print("  [C] Clipboard - Basculer vers le mode manuel (presse-papier)")
        print("  [Q] Quit      - Quitter le workflow")
        print()

        while True:
            choice = input("Votre choix [F/C/Q] : ").strip().upper()
            if choice in ["F", "C", "Q"]:
                return choice
            print("⚠️  Choix invalide. Veuillez entrer F, C ou Q.")
            print()
