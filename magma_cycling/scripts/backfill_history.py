#!/usr/bin/env python3
"""
Backfill automatisé de l'historique d'entraînement.

Analyse en masse des activités historiques depuis Intervals.icu avec génération
automatisée d'analyses IA. Utilise TimelineInjector via insert-analysis pour
injection chronologique dans workouts-history.md.

Examples:
    CLI usage::

        # Backfill par défaut (2024-01-01 → aujourd'hui)
        poetry run backfill-history --yes

        # Backfill période spécifique
        poetry run backfill-history --start-date 2024-08-01 --end-date 2024-08-31 --yes

        # Test dry-run avec limite
        poetry run backfill-history --dry-run --limit 5

        # Provider spécifique et batch size
        poetry run backfill-history --provider claude_api --batch-size 5 --yes

        # Skip activités avec workouts planifiés
        poetry run backfill-history --skip-planned --yes

    Programmatic usage::

        from backfill_history import HistoryBackfiller

        # Initialisation backfiller
        backfiller = HistoryBackfiller(
            provider="mistral_api",
            batch_size=10,
            yes_confirm=True
        )

        # Exécution backfill (utilise TimelineInjector via insert-analysis)
        backfiller.run(
            start_date="2024-08-01",
            end_date="2024-08-31"
        )

Author: Claude Code
Created: 2025-12-26
Updated: 2025-12-26 (Integrated TimelineInjector via insert-analysis)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P2
    Version: v2
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime

from requests.exceptions import HTTPError

from magma_cycling.config import create_intervals_client, get_data_config
from magma_cycling.utils.cli import cli_main
from magma_cycling.workflow_state import WorkflowState


class HistoryBackfiller:
    """Backfill training history with AI analysis."""

    def __init__(
        self,
        provider: str = "mistral_api",
        batch_size: int = 10,
        dry_run: bool = False,
        yes_confirm: bool = False,
        force_reanalyze: bool = False,
    ):
        """Initialize history backfiller.

        Args:
            provider: AI provider name (default: mistral_api)
            batch_size: Number of activities per batch (default: 10)
            dry_run: If True, simulate without writing (default: False)
            yes_confirm: If True, skip confirmation prompts (default: False)
            force_reanalyze: If True, reanalyze existing entries (default: False).
        """
        self.provider = provider

        self.batch_size = batch_size
        self.dry_run = dry_run
        self.yes_confirm = yes_confirm
        self.force_reanalyze = force_reanalyze

        self.api = create_intervals_client()
        self.state = WorkflowState()

        # Get data repo configuration
        self.data_config = get_data_config()

        # Statistics tracking
        self.total_activities = 0
        self.already_analyzed = 0
        self.to_analyze = 0
        self.analyzed_success = 0
        self.analyzed_failed = 0
        self.start_time: float | None = None

    def get_analyzed_activities(self) -> set[str]:
        """Get set of already analyzed activity IDs."""
        history = self.state.state.get("history", [])

        return {h["activity_id"] for h in history}

    def fetch_activities(self, start_date: str, end_date: str) -> list[dict]:
        """
        Fetch all activities from Intervals.icu in date range.

        IMPORTANT: Enrichit chaque activité avec détails complets (TSS, IF, NP)
        car get_activities() ne retourne que les champs basiques.

        Gère rate limiting avec retry + backoff exponentiel.

        Returns list sorted chronologically (oldest first).
        """
        print(f"\n📥 Récupération activités {start_date} → {end_date}...")

        # Fetch liste activités (données basiques)
        activities_basic = self.api.get_activities(oldest=start_date, newest=end_date)

        print(f"✅ {len(activities_basic)} activités trouvées")
        print("📊 Enrichissement avec détails (TSS, IF, NP)...")

        # Enrichir chaque activité avec retry logic
        activities_detailed = []
        failed_permanent = []

        for i, activity in enumerate(activities_basic, 1):
            activity_id = activity.get("id")
            if not activity_id:
                activities_detailed.append(activity)
                continue

            # Retry avec backoff exponentiel
            max_retries = 3
            base_delay = 5  # secondes (5s, 10s, 20s)
            enriched = False

            for attempt in range(max_retries):
                try:
                    # Fetch détails complets (inclut TSS, IF, NP)
                    detailed = self.api.get_activity(activity_id)
                    activities_detailed.append(detailed)
                    enriched = True

                    # Progress indicator every 50 activities
                    if i % 50 == 0:
                        print(f"   ... {i}/{len(activities_basic)} enrichies")

                    break  # Succès, sortir boucle retry

                except HTTPError as e:
                    if e.response.status_code == 429:  # Rate limit
                        if attempt < max_retries - 1:
                            # Backoff exponentiel: 2s, 4s, 8s
                            wait_time = base_delay * (2**attempt)
                            print(
                                f"   ⏸️  Rate limit {activity_id}, retry dans {wait_time}s (tentative {attempt + 2}/{max_retries})"
                            )
                            time.sleep(wait_time)
                        else:
                            # Échec après 3 tentatives
                            print(
                                f"   ❌ Skip {activity_id}: rate limit persistant après {max_retries} tentatives"
                            )
                            failed_permanent.append(activity_id)
                    else:
                        # Autre erreur HTTP (400, 404, 500, etc.)
                        print(f"   ⚠️  HTTP {e.response.status_code} pour {activity_id}")
                        failed_permanent.append(activity_id)
                        break  # Pas de retry pour erreurs non-429

                except Exception as e:
                    # Erreur réseau, timeout, etc.
                    print(f"   ⚠️  Exception {activity_id}: {type(e).__name__}")
                    failed_permanent.append(activity_id)
                    break  # Pas de retry pour exceptions inattendues

            # Si échec définitif après retries, utiliser données basiques
            if not enriched:
                activities_detailed.append(activity)

        # Sort by date (oldest first for chronological backfill)
        activities_detailed.sort(key=lambda a: a.get("start_date_local", ""))

        print(f"✅ {len(activities_detailed)} activités enrichies")

        if failed_permanent:
            print(f"⚠️  {len(failed_permanent)} activités non enrichies (erreur définitive)")
            print("   → Ces activités seront probablement rejetées par is_valid_activity()")
            print("   → Conseil: Relancer backfill avec période plus courte")

        return activities_detailed

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
                sys.executable,  # Python actuel (même que backfill)
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
                cwd=str(self.data_config.data_repo_path),  # ✅ CWD data repo OK now
                capture_output=True,
                text=True,
                timeout=300,  # 5 min timeout per activity
            )

            if result.returncode == 0:
                print(f"✅ Analyse réussie: {activity_id}")
                self.analyzed_success += 1
                return True
            else:
                print(f"❌ Échec analyse: {activity_id}")
                print(f"   Return code: {result.returncode}")

                # Afficher stdout ET stderr (beaucoup d'erreurs Python vont sur stdout!)
                if result.stdout:
                    print(f"   Output:\n{result.stdout[:1000]}")
                if result.stderr:
                    print(f"   Error:\n{result.stderr[:1000]}")

                # Si les deux vides, debug info
                if not result.stdout and not result.stderr:
                    print("   ⚠️  Aucune sortie capturée!")
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
                f"Backfill: Batch {batch_num} " f"({len(activities)} séances, {date_range})"
            )
            cmd = ["git", "commit", "-m", commit_msg]
            subprocess.run(cmd, cwd=str(data_repo_path), check=True)

            print(f"✅ Batch {batch_num} committé: {commit_msg}")
            print(f"   Repo: {data_repo_path}")

        except subprocess.CalledProcessError as e:
            print(f"⚠️  Échec commit batch {batch_num}: {e}")
            print("   Continuant quand même...")

    def estimate_resources(self, count: int) -> dict[str, float]:
        """
        Estimate time and cost for analyzing N activities.

        Returns:
            Dict with 'time_minutes' and 'cost_usd' estimates.
        """
        # Time estimates per provider (minutes per activity)

        time_per_activity = {
            "mistral_api": 1.0,
            "claude_api": 0.7,
            "openai": 0.8,
            "ollama": 4.0,
            "clipboard": 4.0,  # Manual
        }

        # Cost estimates per provider (USD per activity)
        cost_per_activity = {
            "mistral_api": 0.02,
            "claude_api": 0.08,
            "openai": 0.05,
            "ollama": 0.0,
            "clipboard": 0.0,
        }

        time_minutes = count * time_per_activity.get(self.provider, 1.0)
        cost_usd = count * cost_per_activity.get(self.provider, 0.0)

        return {"time_minutes": time_minutes, "time_hours": time_minutes / 60, "cost_usd": cost_usd}

    def run(
        self, start_date: str, end_date: str, skip_planned: bool = False, limit: int | None = None
    ):
        """
        Run complete backfill process.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            skip_planned: Skip activities with planned workouts
            limit: Max activities to analyze (for testing).
        """
        self.start_time = time.time()

        # Print header
        print("\n" + "=" * 70)
        print("  🚀 BACKFILL HISTORIQUE COMPLET")
        print("=" * 70)
        print(f"\n📅 Période: {start_date} → {end_date}")
        print(f"🤖 Provider: {self.provider}")
        print(f"📦 Batch size: {self.batch_size}")
        print(f"🔍 Dry run: {self.dry_run}")
        if limit:
            print(f"⚠️  Limit: {limit} activités max")
        print()

        # Fetch all activities
        activities = self.fetch_activities(start_date, end_date)
        self.total_activities = len(activities)

        # Filter unanalyzed
        to_analyze = self.filter_unanalyzed(activities, skip_planned)
        self.to_analyze = len(to_analyze)

        # Print summary
        print("\n📊 RÉSUMÉ:")
        print(f"   Total activités: {self.total_activities}")
        print(f"   Déjà analysées: {self.already_analyzed}")
        print(f"   À analyser: {self.to_analyze}")

        # Apply limit if specified
        if limit and self.to_analyze > limit:
            print(f"\n⚠️  Limite activée: {limit} activités max")
            to_analyze = to_analyze[:limit]
            self.to_analyze = limit

        # Nothing to do?
        if self.to_analyze == 0:
            print("\n✅ Rien à faire!")
            print("   Toutes les activités sont déjà analysées.")
            return

        # Estimate resources
        estimates = self.estimate_resources(self.to_analyze)

        print("\n⏱️  ESTIMATIONS:")
        print(
            f"   Temps: ~{estimates['time_hours']:.1f}h " f"({estimates['time_minutes']:.0f} min)"
        )
        print(f"   Coût: ${estimates['cost_usd']:.2f} " f"({self.provider})")

        # Confirm if not dry run
        if not self.dry_run:
            if self.yes_confirm:
                print("\n✅ CONFIRMATION AUTOMATIQUE (--yes)")
                print(f"   Analyse de {self.to_analyze} activités avec '{self.provider}'")
            else:
                print("\n⚠️  CONFIRMATION REQUISE")
                print(f"   Cela va analyser {self.to_analyze} activités")
                print(f"   avec le provider '{self.provider}'")
                print()

                response = input("   Continuer? (yes/no): ").strip().lower()
                if response not in ["yes", "y"]:
                    print("\n❌ Annulé par l'utilisateur")
                    return

        # Process activities in batches
        batch = []
        batch_num = 1

        for i, activity in enumerate(to_analyze, 1):
            # Progress header
            progress_pct = int(i * 100 / self.to_analyze)
            print(f"\n{'=' * 70}")
            print(f"📈 Progression: {i}/{self.to_analyze} ({progress_pct}%)")

            # Estimate remaining time
            if self.start_time and i > 1:
                elapsed = time.time() - self.start_time
                avg_time_per_activity = elapsed / (i - 1)
                remaining_activities = self.to_analyze - i + 1
                eta_seconds = avg_time_per_activity * remaining_activities
                eta_minutes = eta_seconds / 60
                print(f"⏱️  ETA: ~{eta_minutes:.1f} min")

            print(f"{'=' * 70}")

            # Analyze activity
            success = self.analyze_activity(activity)

            # Add to batch if successful
            if success:
                batch.append(activity)

            # Commit batch if full
            if len(batch) >= self.batch_size:
                self.commit_batch(batch_num, batch)
                batch = []
                batch_num += 1

                # Rate limiting (avoid API throttling)
                if not self.dry_run and i < self.to_analyze:
                    print("\n⏸️  Pause 5s (rate limiting)...")
                    time.sleep(5)

        # Commit remaining activities
        if batch:
            self.commit_batch(batch_num, batch)

        # Final report
        self.print_final_report()

    def print_final_report(self):
        """Print final statistics and summary."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        print("\n" + "=" * 70)
        print("  ✅ BACKFILL TERMINÉ!")
        print("=" * 70)

        print("\n📊 STATISTIQUES FINALES:")
        print(f"   Total activités: {self.total_activities}")
        print(f"   Déjà analysées: {self.already_analyzed}")
        print(f"   À analyser: {self.to_analyze}")
        print(f"   ✅ Succès: {self.analyzed_success}")
        print(f"   ❌ Échecs: {self.analyzed_failed}")

        if self.analyzed_success > 0:
            success_rate = (self.analyzed_success / self.to_analyze) * 100
            print(f"   📈 Taux réussite: {success_rate:.1f}%")

        print("\n⏱️  TEMPS:")
        print(f"   Total: {elapsed / 60:.1f} min ({elapsed / 3600:.2f}h)")
        if self.analyzed_success > 0:
            avg_time = elapsed / self.analyzed_success
            print(f"   Moyenne: {avg_time:.1f}s par activité")

        if self.analyzed_success > 0:
            num_commits = (self.analyzed_success // self.batch_size) + (
                1 if self.analyzed_success % self.batch_size else 0
            )
            print("\n💾 GIT:")
            print(f"   Commits créés: {num_commits}")
            print(f"   Activités par commit: ~{self.batch_size}")

        print("\n" + "=" * 70)


@cli_main
def main():
    """Run entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill complete training history from Intervals.icu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Dry run to see what would be analyzed
  poetry run backfill-history --dry-run --limit 10

  # Test with 10 activities
  poetry run backfill-history --limit 10 --provider mistral_api

  # Backfill complete 2024
  poetry run backfill-history --start-date 2024-01-01 --end-date 2024-12-31

  # Backfill all with Claude API
  poetry run backfill-history --start-date 2024-01-01 --provider claude_api

  # Backfill with Ollama (free but slow)
  poetry run backfill-history --start-date 2024-01-01 --provider ollama.
        """,
    )

    parser.add_argument(
        "--start-date",
        default="2024-01-01",
        help="Start date in YYYY-MM-DD format (default: 2024-01-01)",
    )

    parser.add_argument(
        "--end-date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date in YYYY-MM-DD format (default: today)",
    )

    parser.add_argument(
        "--provider",
        default="mistral_api",
        choices=["mistral_api", "claude_api", "openai", "ollama", "clipboard"],
        help="AI provider to use (default: mistral_api)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of activities per git commit (default: 10)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be analyzed without actually doing it",
    )

    parser.add_argument(
        "--skip-planned", action="store_true", help="Skip activities that have planned workouts"
    )

    parser.add_argument(
        "--limit", type=int, help="Maximum number of activities to analyze (for testing)"
    )

    parser.add_argument(
        "--yes", action="store_true", help="Auto-confirm analysis (no interactive prompt)"
    )

    parser.add_argument(
        "--force-reanalyze",
        action="store_true",
        help="Force re-analyze activities even if already in workflow state (useful after fixing bugs)",
    )

    args = parser.parse_args()

    # Validate dates
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
        datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        print("   Use YYYY-MM-DD format")
        sys.exit(1)

    # Create and run backfiller
    backfiller = HistoryBackfiller(
        provider=args.provider,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        yes_confirm=args.yes,
        force_reanalyze=args.force_reanalyze,
    )

    try:
        backfiller.run(
            start_date=args.start_date,
            end_date=args.end_date,
            skip_planned=args.skip_planned,
            limit=args.limit,
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par l'utilisateur (Ctrl+C)")
        print("\n📊 Progression avant interruption:")
        print(f"   Analysées: {backfiller.analyzed_success}")
        print(f"   Échecs: {backfiller.analyzed_failed}")
        sys.exit(130)


if __name__ == "__main__":
    main()
