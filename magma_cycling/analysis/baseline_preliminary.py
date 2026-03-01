#!/usr/bin/env python3
"""
Baseline Preliminary Analysis - Monitoring Data Validation.

Analyzes monitoring data (adherence, TSS, TSB) for baseline period
to validate infrastructure and identify patterns before PID calibration.

Usage:
    poetry run analyze-baseline --start 2026 - 01 - 04 --end 2026 - 01 - 25
    poetry run analyze-baseline --start 2026 - 01 - 04 --end 2026 - 01 - 25 --output ~/data/pid

Author: Claude Code + Stéphane Jouve
Created: 2026 - 01 - 25
Sprint: R9.E - Baseline Preliminary Analysis

Metadata:
    Status: Production
    Priority: P1
    Version: 1.0.0
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from magma_cycling.analysis.baseline.anomaly_detection import AnomalyDetectionMixin
from magma_cycling.analysis.baseline.data_loading import DataLoadingMixin
from magma_cycling.analysis.baseline.metrics import MetricsMixin
from magma_cycling.analysis.baseline.pattern_analysis import PatternAnalysisMixin
from magma_cycling.analysis.baseline.reporting import ReportingMixin
from magma_cycling.config import create_intervals_client


class BaselineAnalyzer(
    DataLoadingMixin,
    AnomalyDetectionMixin,
    PatternAnalysisMixin,
    MetricsMixin,
    ReportingMixin,
):
    """Analyze monitoring data for baseline period validation.

    Validates infrastructure monitoring and extracts patterns from:
    - Adherence data (workout_adherence.jsonl)
    - Intervals.icu wellness (TSB, CTL, ATL)
    - Intervals.icu activities (TSS, IF, NP)
    - Cardiovascular coupling (workout_history)

    Args:
        start_date: Analysis start date (YYYY-MM-DD)
        end_date: Analysis end date (YYYY-MM-DD)
        adherence_file: Path to workout_adherence.jsonl
        workout_history_dir: Path to logs/weekly_reports/
        output_dir: Path to output directory
    """

    def __init__(
        self,
        start_date: str,
        end_date: str,
        adherence_file: Path | None = None,
        workout_history_dir: Path | None = None,
        output_dir: Path | None = None,
    ):
        """Initialize baseline analyzer."""
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        self.duration_days = (self.end_date - self.start_date).days + 1

        # Paths
        self.adherence_file = (
            adherence_file or Path.home() / "data" / "monitoring" / "workout_adherence.jsonl"
        )
        self.workout_history_dir = (
            workout_history_dir or Path(__file__).parent.parent.parent / "logs" / "weekly_reports"
        )
        self.output_dir = output_dir or Path.home() / "data" / "pid"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Data storage
        self.adherence_data = []
        self.wellness_data = []
        self.activities_data = []
        self.events_data = []
        self.cv_coupling_values = []
        self.skipped_sessions = []  # NOTE events with [SAUTÉE] tag
        self.replaced_sessions = []  # NOTE events with [REMPLACÉE] tag
        self.cancelled_sessions = []  # NOTE events with [ANNULÉE] tag
        self.unsolicited_activities = []  # Activities without paired workout event

        # Intervals.icu client
        self.client = create_intervals_client()

        print("📊 Baseline Analyzer Initialized")
        print(f"   Period: {self.start_date} → {self.end_date} ({self.duration_days} days)")
        print()

    def run_analysis(self) -> dict[str, Any]:
        """Run complete baseline analysis.

        Returns:
            Complete analysis results dict
        """
        print("=" * 70)
        print("🔬 BASELINE PRELIMINARY ANALYSIS")
        print("=" * 70)
        print()

        # Load all data
        self.load_adherence_data()
        self.load_intervals_data()
        self.parse_skipped_replaced_sessions()  # Parse NOTE events for skipped/replaced
        self.unsolicited_activities = self.detect_unsolicited_activities()
        self.load_cardiovascular_coupling()

        # Validate quality
        quality = self.validate_data_quality()

        # Calculate metrics
        adherence = self.calculate_adherence_metrics()
        tss = self.calculate_tss_metrics()
        cv_coupling = self.calculate_cv_coupling_metrics()
        tsb = self.analyze_tsb_trajectory()

        # Calculate unsolicited metrics
        total_unsolicited_tss = sum(a["tss"] for a in self.unsolicited_activities)
        actual_tss = tss.get("actual_total", 0)
        unsolicited_percentage = (total_unsolicited_tss / actual_tss * 100) if actual_tss > 0 else 0

        # Assemble results
        results = {
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "period_start": self.start_date.isoformat(),
                "period_end": self.end_date.isoformat(),
                "duration_days": self.duration_days,
                "version": "2.0.0",  # Updated for Sprint R9.F
            },
            "quality": quality,
            "adherence": adherence,
            "tss": tss,
            "tsb": tsb,
            "cardiovascular_coupling": cv_coupling,
            "unsolicited_activities": {
                "total_count": len(self.unsolicited_activities),
                "total_tss": total_unsolicited_tss,
                "percentage_of_total": unsolicited_percentage,
                "details": self.unsolicited_activities,
            },
        }

        print()
        print("=" * 70)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 70)

        return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Baseline Preliminary Analysis")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default=None, help="Output directory (default: ~/data/pid)")

    args = parser.parse_args()

    # Create analyzer
    analyzer = BaselineAnalyzer(
        start_date=args.start,
        end_date=args.end,
        output_dir=Path(args.output) if args.output else None,
    )

    # Run analysis
    results = analyzer.run_analysis()

    # Generate outputs
    analyzer.generate_json_output(results)
    analyzer.generate_markdown_report(results)

    print("\n✅ Baseline analysis complete!")
    print(f"   JSON: {analyzer.output_dir / 'baseline_preliminary.json'}")
    print(f"   Report: {analyzer.output_dir / 'baseline_report_s076_s077.md'}")


if __name__ == "__main__":
    main()
