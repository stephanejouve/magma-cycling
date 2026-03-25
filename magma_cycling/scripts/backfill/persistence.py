"""Persistence mixin for HistoryBackfiller."""

import logging
import subprocess
import time

logger = logging.getLogger(__name__)


class PersistenceMixin:
    """Git commit and final report."""

    def commit_batch(self, batch_num: int, activities: list[dict]):
        """
        Commit analyzed activities to git.

        Args:
            batch_num: Batch number for commit message
            activities: Activities in this batch.
        """
        if self.dry_run:
            print(f"\n🔍 DRY RUN - Would commit batch {batch_num}")
            return

        print(f"\n💾 Commit batch {batch_num}...")

        try:
            # Get date range for commit message
            dates = [a.get("start_date_local", "")[:10] for a in activities]
            date_min = min(dates) if dates else "unknown"
            date_max = max(dates) if dates else "unknown"
            date_range = f"{date_min} → {date_max}" if date_min != date_max else date_min

            # Get data repo path and workouts-history path
            data_repo_path = self.data_config.data_repo_path
            workouts_history_file = self.data_config.workouts_history_path

            # Git add (use absolute path of file)
            cmd = ["git", "add", str(workouts_history_file)]
            subprocess.run(cmd, cwd=str(data_repo_path), check=True)

            # Git commit
            commit_msg = (
                f"Backfill: Batch {batch_num} " f"({len(activities)} seances, {date_range})"
            )
            cmd = ["git", "commit", "-m", commit_msg]
            subprocess.run(cmd, cwd=str(data_repo_path), check=True)

            print(f"✅ Batch {batch_num} committe: {commit_msg}")
            print(f"   Repo: {data_repo_path}")

        except subprocess.CalledProcessError as e:
            print(f"⚠️  Echec commit batch {batch_num}: {e}")
            print("   Continuant quand meme...")

    def print_final_report(self):
        """Print final statistics and summary."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        print("\n" + "=" * 70)
        print("  ✅ BACKFILL TERMINE!")
        print("=" * 70)

        print("\n📊 STATISTIQUES FINALES:")
        print(f"   Total activites: {self.total_activities}")
        print(f"   Deja analysees: {self.already_analyzed}")
        print(f"   A analyser: {self.to_analyze}")
        print(f"   ✅ Succes: {self.analyzed_success}")
        print(f"   ❌ Echecs: {self.analyzed_failed}")

        if self.analyzed_success > 0:
            success_rate = (self.analyzed_success / self.to_analyze) * 100
            print(f"   📈 Taux reussite: {success_rate:.1f}%")

        print("\n⏱️  TEMPS:")
        print(f"   Total: {elapsed / 60:.1f} min ({elapsed / 3600:.2f}h)")
        if self.analyzed_success > 0:
            avg_time = elapsed / self.analyzed_success
            print(f"   Moyenne: {avg_time:.1f}s par activite")

        if self.analyzed_success > 0:
            num_commits = (self.analyzed_success // self.batch_size) + (
                1 if self.analyzed_success % self.batch_size else 0
            )
            print("\n💾 GIT:")
            print(f"   Commits crees: {num_commits}")
            print(f"   Activites par commit: ~{self.batch_size}")

        print("\n" + "=" * 70)
