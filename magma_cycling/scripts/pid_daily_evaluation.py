#!/usr/bin/env python3
"""PID Daily Evaluation - Complete Training Intelligence Pipeline.

This script is the central nervous system for training load adaptation:
1. Collects adherence data (discipline)
2. Extracts cardiovascular metrics (quality)
3. Calculates TSS completion (capacity)
4. Feeds TrainingIntelligence with learnings
5. Evaluates PID corrections at cycle completion
6. Logs all evaluations for monitoring

Usage:
    # Daily evaluation (collect + learn)
    poetry run pid-daily-evaluation

    # Evaluate cycle completion
    poetry run pid-daily-evaluation --cycle-complete --measured-ftp 210

    # Dry-run (no saves)
    poetry run pid-daily-evaluation --dry-run

Metadata:
    Created: 2026 - 01 - 25
    Author: Claude Code + Stéphane Jouve
    Category: INTELLIGENCE + PID
    Status: Production
    Priority: P0 (Critical Path)
    Version: 2.0.0
    Sprint: R9++ / Sprint 3 (facade rewire)
    Replaces: aggregate_adherence_to_intelligence.py (integrated)
    Related: check_workout_adherence.py (22:00 data source)
"""

import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from magma_cycling.api.intervals_client import IntervalsClient
from magma_cycling.config import get_intervals_config
from magma_cycling.intelligence.training_intelligence import TrainingIntelligence
from magma_cycling.utils.cli import cli_main
from magma_cycling.workflows.pid_eval.adherence import AdherenceMixin
from magma_cycling.workflows.pid_eval.cardiovascular import CardiovascularQualityMixin
from magma_cycling.workflows.pid_eval.cycle_metrics import CycleMetricsAggregationMixin
from magma_cycling.workflows.pid_eval.evaluation_logging import LoggingMixin
from magma_cycling.workflows.pid_eval.intelligence_learnings import (
    TrainingIntelligenceLearningsMixin,
)
from magma_cycling.workflows.pid_eval.pid_correction import PIDCorrectionMixin
from magma_cycling.workflows.pid_eval.test_opportunity import TestOpportunityMixin
from magma_cycling.workflows.pid_eval.tss_capacity import TSSCapacityMixin


class PIDDailyEvaluator(
    AdherenceMixin,
    CardiovascularQualityMixin,
    TSSCapacityMixin,
    CycleMetricsAggregationMixin,
    TrainingIntelligenceLearningsMixin,
    PIDCorrectionMixin,
    TestOpportunityMixin,
    LoggingMixin,
):
    """Complete PID evaluation pipeline."""

    def __init__(
        self,
        adherence_file: Path | None = None,
        workouts_history: Path | None = None,
        evaluation_log: Path | None = None,
        intelligence_file: Path | None = None,
        dry_run: bool = False,
    ):
        """Initialize PID evaluator.

        Args:
            adherence_file: Path to workout_adherence.jsonl (default: ~/data/monitoring/)
            workouts_history: Path to workouts-history.md (default: ~/training-logs/)
            evaluation_log: Path to pid_evaluation.jsonl (default: ~/data/monitoring/)
            intelligence_file: Path to intelligence.json (default: ~/data/)
            dry_run: If True, don't save files
        """
        # API client
        config = get_intervals_config()
        self.client = IntervalsClient(athlete_id=config.athlete_id, api_key=config.api_key)

        # File paths
        self.adherence_file = (
            adherence_file or Path.home() / "data" / "monitoring" / "workout_adherence.jsonl"
        )
        self.workouts_history = (
            workouts_history
            if workouts_history
            else Path(__file__).parent.parent.parent / "logs" / "weekly_reports"
        )
        self.evaluation_log = (
            evaluation_log or Path.home() / "data" / "monitoring" / "pid_evaluation.jsonl"
        )
        self.intelligence_file = intelligence_file or Path.home() / "data" / "intelligence.json"

        self.dry_run = dry_run

        # Load or create intelligence
        if self.intelligence_file.exists():
            print(f"📖 Loading intelligence from {self.intelligence_file}")
            self.intelligence = TrainingIntelligence.load_from_file(self.intelligence_file)
            print(f"   Learnings: {len(self.intelligence.learnings)}")
            print(f"   Patterns: {len(self.intelligence.patterns)}")
        else:
            print("📝 Creating new TrainingIntelligence instance")
            self.intelligence = TrainingIntelligence()

    def run_daily_evaluation(self, days_back: int = 7) -> dict[str, Any]:
        """Run daily evaluation (collect + learn, no PID).

        Args:
            days_back: Number of days to analyze (default: 7)

        Returns:
            Evaluation result dict
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        print(f"\n{'=' * 70}")
        print("📅 PID Daily Evaluation - Collection Mode")
        print(f"{'=' * 70}")

        # Calculate metrics
        metrics = self.calculate_cycle_metrics(start_date, end_date)

        # Create learnings
        self.create_intelligence_learnings(metrics, start_date, end_date)

        # Monitor CTL progression vs Peaks targets
        ctl_monitoring = self.monitor_ctl_progression_vs_peaks()

        # Check test opportunity
        print(f"\n{'=' * 60}")
        print("🎯 Test FTP Opportunity Check")
        print(f"{'=' * 60}")

        test_recommendation = self.check_test_opportunity()

        if test_recommendation:
            status = test_recommendation["status"]
            message = test_recommendation["message"]
            timing = test_recommendation["timing"]
            weeks = test_recommendation["weeks_since_test"]
            tsb = test_recommendation["tsb"]

            print(f"   📊 Status: {status}")
            print(f"   ⏰ Dernier test: {weeks:.1f} semaines")
            print(f"   💪 TSB actuel: {tsb:.1f}")
            print(f"   💡 {message}")
            print(f"   📅 Timing: {timing}")

            # Create adaptation in TrainingIntelligence
            evidence = [
                f"Dernier test FTP: {weeks:.1f} semaines",
                "Cycle PID recommandé: 6 - 8 semaines",
                f"TSB actuel: {tsb:.1f}",
                f"Adhérence: {metrics['adherence_rate'] * 100:.0f}%",
                f"Qualité CV: {metrics['avg_cardiovascular_coupling'] * 100:.1f}%",
                f"Capacité TSS: {metrics['tss_completion_rate'] * 100:.0f}%",
            ]

            if status == "READY":
                adaptation = self.intelligence.propose_adaptation(
                    protocol_name="ftp_test_cycle",
                    adaptation_type="ADD",
                    current_rule=f"Dernier test: {weeks:.1f} semaines",
                    proposed_rule="Planifier tests FTP cette semaine",
                    justification=(f"Cycle PID dépassé ({weeks:.1f} > 6 - 8 sem), condition prête"),
                    evidence=evidence,
                )
            elif status == "NEEDS_TAPER":
                adaptation = self.intelligence.propose_adaptation(
                    protocol_name="ftp_test_cycle",
                    adaptation_type="ADD",
                    current_rule=f"Dernier test: {weeks:.1f} semaines",
                    proposed_rule="Semaine affûtage puis tests FTP (TSS -40%)",
                    justification=(f"Cycle PID dépassé ({weeks:.1f} > 6 - 8 sem), TSB insuffisant"),
                    evidence=evidence,
                )
            else:
                adaptation = self.intelligence.propose_adaptation(
                    protocol_name="ftp_test_cycle",
                    adaptation_type="ADD",
                    current_rule=f"Dernier test: {weeks:.1f} semaines",
                    proposed_rule="Préparation 2 semaines puis tests FTP",
                    justification="Test overdue mais fitness/form limitée",
                    evidence=evidence,
                )

            print(f"   ✅ Adaptation créée: {adaptation.id}")
        else:
            print("   ✓ Pas de test recommandé pour le moment")

        # Log
        self.log_evaluation(start_date, end_date, metrics, pid_result=None)

        # Save
        self.save_intelligence()

        # Expire stale adaptations
        expired = self.intelligence.expire_stale_adaptations()
        if expired > 0:
            print(f"   🗑️  {expired} adaptation(s) expirée(s)")
            self.save_intelligence()

        print(f"\n{'=' * 70}")
        print("✨ Daily Evaluation Complete")
        print(f"{'=' * 70}")
        print(f"   Learnings: {len(self.intelligence.learnings)}")
        print(f"   Patterns: {len(self.intelligence.patterns)}")
        print(f"   Adaptations: {len(self.intelligence.adaptations)}")

        if ctl_monitoring:
            print(f"   CTL Status: {ctl_monitoring['status']}")
            print(f"   CTL Current: {ctl_monitoring['ctl_current']:.1f}")
            if ctl_monitoring.get("weeks_to_optimal"):
                print(f"   Weeks → Optimal: {ctl_monitoring['weeks_to_optimal']:.1f} semaines")

        print(f"{'=' * 70}\n")

        return {
            "status": "SUCCESS",
            "metrics": metrics,
            "test_recommendation": test_recommendation,
            "ctl_monitoring": ctl_monitoring,
        }

    def run_cycle_evaluation(
        self,
        measured_ftp: float,
        cycle_duration_weeks: int = 6,
    ) -> dict[str, Any]:
        """Run cycle completion evaluation (full PID).

        Args:
            measured_ftp: Measured FTP from test (W)
            cycle_duration_weeks: Cycle duration (default: 6 weeks)

        Returns:
            Evaluation result dict with PID correction
        """
        end_date = date.today()
        start_date = end_date - timedelta(weeks=cycle_duration_weeks)

        print(f"\n{'=' * 70}")
        print("📅 PID Cycle Evaluation - Full PID Mode")
        print(f"{'=' * 70}")
        print(f"   Measured FTP: {measured_ftp}W")
        print(f"   Cycle Duration: {cycle_duration_weeks} weeks")

        # Calculate metrics
        metrics = self.calculate_cycle_metrics(start_date, end_date)

        # Create learnings
        self.create_intelligence_learnings(metrics, start_date, end_date)

        # Evaluate PID
        pid_result = self.evaluate_pid_correction(
            measured_ftp=measured_ftp,
            cycle_duration_weeks=cycle_duration_weeks,
            metrics=metrics,
        )

        # Log
        self.log_evaluation(start_date, end_date, metrics, pid_result=pid_result)

        # Save
        self.save_intelligence()

        print(f"\n{'=' * 70}")
        print("✨ Cycle Evaluation Complete")
        print(f"{'=' * 70}")
        print(f"   Learnings: {len(self.intelligence.learnings)}")
        print(f"   Patterns: {len(self.intelligence.patterns)}")
        print(f"   PID Adjustment: {pid_result['tss_per_week_adjusted']} TSS/week")
        print(f"{'=' * 70}\n")

        return {
            "status": "SUCCESS",
            "metrics": metrics,
            "pid_correction": pid_result,
        }


@cli_main
def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PID Daily Evaluation - Complete Training Intelligence Pipeline"
    )

    parser.add_argument(
        "--cycle-complete",
        action="store_true",
        help="Run cycle completion evaluation (requires --measured-ftp)",
    )

    parser.add_argument(
        "--measured-ftp",
        type=float,
        help="Measured FTP from test (W) - required for --cycle-complete",
    )

    parser.add_argument(
        "--cycle-weeks",
        type=int,
        default=6,
        help="Cycle duration in weeks (default: 6)",
    )

    parser.add_argument(
        "--days-back",
        type=int,
        default=7,
        help="Days to analyze in daily mode (default: 7)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run mode (no saves)",
    )

    args = parser.parse_args()

    # Validate args
    if args.cycle_complete and not args.measured_ftp:
        print("❌ Error: --measured-ftp required when --cycle-complete is used")
        return 1

    # Create evaluator
    evaluator = PIDDailyEvaluator(dry_run=args.dry_run)

    # Run evaluation
    if args.cycle_complete:
        result = evaluator.run_cycle_evaluation(
            measured_ftp=args.measured_ftp,
            cycle_duration_weeks=args.cycle_weeks,
        )
    else:
        result = evaluator.run_daily_evaluation(days_back=args.days_back)

    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    main()  # pragma: no cover
