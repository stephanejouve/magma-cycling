#!/usr/bin/env python3
"""
Backfill automatisé de l'historique d'entraînement

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2
DOCSTRING: v2

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
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
import subprocess
import time
from typing import List, Dict, Set

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cyclisme_training_logs.sync_intervals import IntervalsAPI
from cyclisme_training_logs.workflow_state import WorkflowState
from cyclisme_training_logs.config import get_data_config


class HistoryBackfiller:
    """Backfill training history with AI analysis."""

    def __init__(
        self,
        provider: str = "mistral_api",
        batch_size: int = 10,
        dry_run: bool = False,
        yes_confirm: bool = False
    ):
        self.provider = provider
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.yes_confirm = yes_confirm

        # Get Intervals.icu credentials from environment
        athlete_id = os.getenv('VITE_INTERVALS_ATHLETE_ID')
        api_key = os.getenv('VITE_INTERVALS_API_KEY')

        if not athlete_id or not api_key:
            raise ValueError(
                "Missing Intervals.icu credentials. Set environment variables:\n"
                "  VITE_INTERVALS_ATHLETE_ID\n"
                "  VITE_INTERVALS_API_KEY"
            )

        self.api = IntervalsAPI(athlete_id, api_key)
        self.state = WorkflowState()

        # Get data repo configuration
        self.data_config = get_data_config()

        # Statistics tracking
        self.total_activities = 0
        self.already_analyzed = 0
        self.to_analyze = 0
        self.analyzed_success = 0
        self.analyzed_failed = 0
        self.start_time = None

    def get_analyzed_activities(self) -> Set[str]:
        """Get set of already analyzed activity IDs."""
        history = self.state.state.get("history", [])
        return set(h["activity_id"] for h in history)

    def fetch_activities(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        Fetch all activities from Intervals.icu in date range.

        Returns list sorted chronologically (oldest first).
        """
        print(f"\n📥 Récupération activités {start_date} → {end_date}...")

        activities = self.api.get_activities(
            oldest=start_date,
            newest=end_date
        )

        # Sort by date (oldest first for chronological backfill)
        activities.sort(key=lambda a: a.get('start_date_local', ''))

        print(f"✅ {len(activities)} activités trouvées")
        return activities

    def filter_unanalyzed(
        self,
        activities: List[Dict],
        skip_planned: bool = False
    ) -> List[Dict]:
        """
        Filter activities that need analysis.

        Args:
            activities: All activities from API
            skip_planned: If True, skip activities with planned workouts

        Returns:
            List of activities needing analysis
        """
        analyzed = self.get_analyzed_activities()

        to_analyze = []
        for activity in activities:
            activity_id = str(activity.get('id', ''))

            # Skip if already analyzed
            if activity_id in analyzed:
                self.already_analyzed += 1
                continue

            # Skip if invalid (use same validation as workflow)
            if not self.state.is_valid_activity(activity):
                continue

            # Skip if has planned workout (optional)
            if skip_planned and activity.get('workout_id'):
                print(f"⏭️  Skip {activity_id}: has planned workout")
                continue

            to_analyze.append(activity)

        return to_analyze

    def analyze_activity(self, activity: Dict) -> bool:
        """
        Analyze single activity using workflow-coach --auto.

        Returns:
            True if analysis succeeded, False otherwise
        """
        activity_id = str(activity.get('id', ''))
        activity_name = activity.get('name', 'Unknown')
        activity_date = activity.get('start_date_local', '')[:10]

        print(f"\n{'='*70}")
        print(f"📊 Analyse: {activity_name}")
        print(f"   ID: {activity_id}")
        print(f"   Date: {activity_date}")
        print(f"{'='*70}")

        if self.dry_run:
            print("🔍 DRY RUN - Skipping actual analysis")
            return True

        try:
            # Build command
            cmd = [
                'poetry', 'run', 'workflow-coach',
                '--activity-id', activity_id,
                '--provider', self.provider,
                '--auto',              # Fully automated
                '--skip-feedback',     # No manual feedback
                '--skip-git'           # Batch commits later
            ]

            # Run workflow with timeout
            print(f"🚀 Lancement analyse automatique...")
            result = subprocess.run(
                cmd,
                cwd=str(self.data_config.data_repo_path),  # ✅ Use data repo, not code repo
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout per activity
            )

            if result.returncode == 0:
                print(f"✅ Analyse réussie: {activity_id}")
                self.analyzed_success += 1
                return True
            else:
                print(f"❌ Échec analyse: {activity_id}")
                print(f"   Return code: {result.returncode}")
                if result.stderr:
                    print(f"   Error: {result.stderr[:200]}")
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

    def commit_batch(self, batch_num: int, activities: List[Dict]):
        """
        Commit analyzed activities to git.

        Args:
            batch_num: Batch number for commit message
            activities: Activities in this batch
        """
        if self.dry_run:
            print(f"\n🔍 DRY RUN - Would commit batch {batch_num}")
            return

        print(f"\n💾 Commit batch {batch_num}...")

        try:
            # Get date range for commit message
            dates = [a.get('start_date_local', '')[:10] for a in activities]
            date_min = min(dates) if dates else 'unknown'
            date_max = max(dates) if dates else 'unknown'
            date_range = f"{date_min} → {date_max}" if date_min != date_max else date_min

            # Get data repo path and workouts-history path
            data_repo_path = self.data_config.data_repo_path
            workouts_history_file = self.data_config.workouts_history_path

            # Git add (use absolute path of file)
            cmd = ['git', 'add', str(workouts_history_file)]
            subprocess.run(cmd, cwd=str(data_repo_path), check=True)

            # Git commit
            commit_msg = (
                f"Backfill: Batch {batch_num} "
                f"({len(activities)} séances, {date_range})"
            )
            cmd = ['git', 'commit', '-m', commit_msg]
            subprocess.run(cmd, cwd=str(data_repo_path), check=True)

            print(f"✅ Batch {batch_num} committé: {commit_msg}")
            print(f"   Repo: {data_repo_path}")

        except subprocess.CalledProcessError as e:
            print(f"⚠️  Échec commit batch {batch_num}: {e}")
            print("   Continuant quand même...")

    def estimate_resources(self, count: int) -> Dict[str, float]:
        """
        Estimate time and cost for analyzing N activities.

        Returns:
            Dict with 'time_minutes' and 'cost_usd' estimates
        """
        # Time estimates per provider (minutes per activity)
        time_per_activity = {
            'mistral_api': 1.0,
            'claude_api': 0.7,
            'openai': 0.8,
            'ollama': 4.0,
            'clipboard': 4.0  # Manual
        }

        # Cost estimates per provider (USD per activity)
        cost_per_activity = {
            'mistral_api': 0.02,
            'claude_api': 0.08,
            'openai': 0.05,
            'ollama': 0.0,
            'clipboard': 0.0
        }

        time_minutes = count * time_per_activity.get(self.provider, 1.0)
        cost_usd = count * cost_per_activity.get(self.provider, 0.0)

        return {
            'time_minutes': time_minutes,
            'time_hours': time_minutes / 60,
            'cost_usd': cost_usd
        }

    def run(
        self,
        start_date: str,
        end_date: str,
        skip_planned: bool = False,
        limit: int = None
    ):
        """
        Run complete backfill process.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            skip_planned: Skip activities with planned workouts
            limit: Max activities to analyze (for testing)
        """
        self.start_time = time.time()

        # Print header
        print("\n" + "="*70)
        print("  🚀 BACKFILL HISTORIQUE COMPLET")
        print("="*70)
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
        print(f"\n📊 RÉSUMÉ:")
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

        print(f"\n⏱️  ESTIMATIONS:")
        print(f"   Temps: ~{estimates['time_hours']:.1f}h "
              f"({estimates['time_minutes']:.0f} min)")
        print(f"   Coût: ${estimates['cost_usd']:.2f} "
              f"({self.provider})")

        # Confirm if not dry run
        if not self.dry_run:
            if self.yes_confirm:
                print(f"\n✅ CONFIRMATION AUTOMATIQUE (--yes)")
                print(f"   Analyse de {self.to_analyze} activités avec '{self.provider}'")
            else:
                print(f"\n⚠️  CONFIRMATION REQUISE")
                print(f"   Cela va analyser {self.to_analyze} activités")
                print(f"   avec le provider '{self.provider}'")
                print()

                response = input("   Continuer? (yes/no): ").strip().lower()
                if response not in ['yes', 'y']:
                    print("\n❌ Annulé par l'utilisateur")
                    return

        # Process activities in batches
        batch = []
        batch_num = 1

        for i, activity in enumerate(to_analyze, 1):
            # Progress header
            progress_pct = int(i * 100 / self.to_analyze)
            print(f"\n{'='*70}")
            print(f"📈 Progression: {i}/{self.to_analyze} ({progress_pct}%)")

            # Estimate remaining time
            if self.start_time and i > 1:
                elapsed = time.time() - self.start_time
                avg_time_per_activity = elapsed / (i - 1)
                remaining_activities = self.to_analyze - i + 1
                eta_seconds = avg_time_per_activity * remaining_activities
                eta_minutes = eta_seconds / 60
                print(f"⏱️  ETA: ~{eta_minutes:.1f} min")

            print(f"{'='*70}")

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

        print("\n" + "="*70)
        print("  ✅ BACKFILL TERMINÉ!")
        print("="*70)

        print(f"\n📊 STATISTIQUES FINALES:")
        print(f"   Total activités: {self.total_activities}")
        print(f"   Déjà analysées: {self.already_analyzed}")
        print(f"   À analyser: {self.to_analyze}")
        print(f"   ✅ Succès: {self.analyzed_success}")
        print(f"   ❌ Échecs: {self.analyzed_failed}")

        if self.analyzed_success > 0:
            success_rate = (self.analyzed_success / self.to_analyze) * 100
            print(f"   📈 Taux réussite: {success_rate:.1f}%")

        print(f"\n⏱️  TEMPS:")
        print(f"   Total: {elapsed/60:.1f} min ({elapsed/3600:.2f}h)")
        if self.analyzed_success > 0:
            avg_time = elapsed / self.analyzed_success
            print(f"   Moyenne: {avg_time:.1f}s par activité")

        if self.analyzed_success > 0:
            num_commits = (self.analyzed_success // self.batch_size) + (1 if self.analyzed_success % self.batch_size else 0)
            print(f"\n💾 GIT:")
            print(f"   Commits créés: {num_commits}")
            print(f"   Activités par commit: ~{self.batch_size}")

        print("\n" + "="*70)


def main():
    """Main entry point."""
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
  poetry run backfill-history --start-date 2024-01-01 --provider ollama
        """
    )

    parser.add_argument(
        '--start-date',
        default='2024-01-01',
        help='Start date in YYYY-MM-DD format (default: 2024-01-01)'
    )

    parser.add_argument(
        '--end-date',
        default=datetime.now().strftime('%Y-%m-%d'),
        help='End date in YYYY-MM-DD format (default: today)'
    )

    parser.add_argument(
        '--provider',
        default='mistral_api',
        choices=['mistral_api', 'claude_api', 'openai', 'ollama', 'clipboard'],
        help='AI provider to use (default: mistral_api)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of activities per git commit (default: 10)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be analyzed without actually doing it'
    )

    parser.add_argument(
        '--skip-planned',
        action='store_true',
        help='Skip activities that have planned workouts'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of activities to analyze (for testing)'
    )

    parser.add_argument(
        '--yes',
        action='store_true',
        help='Auto-confirm analysis (no interactive prompt)'
    )

    args = parser.parse_args()

    # Validate dates
    try:
        datetime.strptime(args.start_date, '%Y-%m-%d')
        datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        print("   Use YYYY-MM-DD format")
        sys.exit(1)

    # Create and run backfiller
    backfiller = HistoryBackfiller(
        provider=args.provider,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        yes_confirm=args.yes
    )

    try:
        backfiller.run(
            start_date=args.start_date,
            end_date=args.end_date,
            skip_planned=args.skip_planned,
            limit=args.limit
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par l'utilisateur (Ctrl+C)")
        print(f"\n📊 Progression avant interruption:")
        print(f"   Analysées: {backfiller.analyzed_success}")
        print(f"   Échecs: {backfiller.analyzed_failed}")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
