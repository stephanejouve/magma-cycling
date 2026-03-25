"""Processing mixin for HistoryBackfiller."""

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


class ProcessingMixin:
    """Filter and analyze activities."""

    def filter_unanalyzed(self, activities: list[dict], skip_planned: bool = False) -> list[dict]:
        """
        Filter activities that need analysis.

        Args:
            activities: All activities from API
            skip_planned: If True, skip activities with planned workouts

        Returns:
            List of activities needing analysis.
        """
        # If force_reanalyze, ignore workflow state (empty set = analyze all)

        if self.force_reanalyze:
            print("⚡ Force re-analyze: ignoring workflow state")
            analyzed = set()
        else:
            analyzed = self.get_analyzed_activities()

        to_analyze = []
        for activity in activities:
            activity_id = str(activity.get("id", ""))

            # Skip if already analyzed
            if activity_id in analyzed:
                self.already_analyzed += 1
                continue

            # Skip if invalid (use same validation as workflow)
            if not self.state.is_valid_activity(activity):
                continue

            # Skip if has planned workout (optional)
            if skip_planned and activity.get("workout_id"):
                print(f"⏭️  Skip {activity_id}: has planned workout")
                continue

            to_analyze.append(activity)

        return to_analyze

    def analyze_activity(self, activity: dict) -> bool:
        """
        Analyze single activity using workflow-coach --auto.

        Uses direct Python execution instead of 'poetry run' to avoid
        pyproject.toml lookup in wrong directory (data repo vs code repo).

        Returns:
            True if analysis succeeded, False otherwise.
        """
        activity_id = str(activity.get("id", ""))

        activity_name = activity.get("name", "Unknown")
        activity_date = activity.get("start_date_local", "")[:10]

        print(f"\n{'=' * 70}")
        print(f"📊 Analyse: {activity_name}")
        print(f"   ID: {activity_id}")
        print(f"   Date: {activity_date}")
        print(f"{'=' * 70}")

        if self.dry_run:
            print("🔍 DRY RUN - Skipping actual analysis")
            return True

        try:
            # Build command - Python direct instead of Poetry
            # Au lieu de: poetry run workflow-coach --activity-id ...
            # Utiliser: python -m magma_cycling.workflow_coach --activity-id ...
            cmd = [
                sys.executable,  # Python actuel (meme que backfill)
                "-m",
                "magma_cycling.workflow_coach",
                "--activity-id",
                activity_id,
                "--provider",
                self.provider,
                "--auto",  # Fully automated
                "--skip-feedback",  # No manual feedback
                "--skip-git",  # Batch commits later
            ]

            # Run workflow with timeout
            print("🚀 Lancement analyse automatique...")
            result = subprocess.run(
                cmd,
                cwd=str(self.data_config.data_repo_path),  # CWD data repo OK now
                capture_output=True,
                text=True,
                timeout=300,  # 5 min timeout per activity
            )

            if result.returncode == 0:
                print(f"✅ Analyse reussie: {activity_id}")
                self.analyzed_success += 1
                return True
            else:
                print(f"❌ Echec analyse: {activity_id}")
                print(f"   Return code: {result.returncode}")

                # Afficher stdout ET stderr (beaucoup d'erreurs Python vont sur stdout!)
                if result.stdout:
                    print(f"   Output:\n{result.stdout[:1000]}")
                if result.stderr:
                    print(f"   Error:\n{result.stderr[:1000]}")

                # Si les deux vides, debug info
                if not result.stdout and not result.stderr:
                    print("   ⚠️  Aucune sortie capturee!")
                    print(f"   Command: {' '.join(cmd)}")
                    print(f"   CWD: {self.data_config.data_repo_path}")

                self.analyzed_failed += 1
                return False

        except subprocess.TimeoutExpired:
            print(f"⏱️  TIMEOUT: {activity_id} (>5min)")
            self.analyzed_failed += 1
            return False

        except Exception as e:
            print(f"❌ EXCEPTION: {activity_id}: {e}")
            self.analyzed_failed += 1
            return False
