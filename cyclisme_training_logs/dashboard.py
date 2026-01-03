#!/usr/bin/env python3
"""Dashboard CLI - Vue d'ensemble rapide entraînement.

Affiche en 1 commande :
- Current Week stats (TSS, CTL/ATL, sessions)
- FTP Progression (current, target, PID recommendation)
- Recent Learnings (top 3)
- Next Week Plan preview

Usage:
    poetry run dashboard
    poetry run dashboard --week 2026-W01
    poetry run dashboard --intelligence ~/data/intelligence.json

Examples:
    # Dashboard semaine courante
    poetry run dashboard

    # Dashboard semaine spécifique
    poetry run dashboard --week 2026-W02

    # Avec intelligence chargée
    poetry run dashboard --intelligence ~/cyclisme-training-logs-data/intelligence/backfilled_2024-2025.json.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from cyclisme_training_logs.config import get_logger

logger = get_logger(__name__)


def get_current_week() -> str:
    """Get current ISO week (YYYY-WXX format)."""
    now = datetime.now()
    iso_calendar = now.isocalendar()
    return f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"


def print_dashboard_header(week: str) -> None:
    """Print dashboard header."""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print(f"║    Cyclisme Training Dashboard - {week:^18} ║")
    print("╠══════════════════════════════════════════════════════════╣")


def print_current_week_stats(week: str) -> None:
    """Print current week statistics.

    TODO: Integrate with real data from:
    - cyclisme_training_logs.analyzers.weekly_aggregator
    - Intervals.icu API (activities, wellness).
    """
    print("║ 📊 Current Week                                          ║")

    # Mock data (replace with real data)
    tss_completed = 285
    tss_target = 350
    tss_pct = int((tss_completed / tss_target) * 100)
    ctl = 60.2
    atl = 58.1
    sessions_completed = 4
    sessions_total = 5

    print(
        f"║   TSS: {tss_completed} / {tss_target} ({tss_pct}%)    CTL: {ctl}    ATL: {atl}       ║"
    )
    print(
        f"║   Sessions: {sessions_completed}/{sessions_total} completed                                ║"
    )
    print("║                                                          ║")


def print_ftp_progression(intelligence_path: Path | None) -> None:
    """Print FTP progression and PID recommendation.

    TODO: Integrate with:
    - cyclisme_training_logs.intelligence.training_intelligence
    - cyclisme_training_logs.intelligence.pid_controller.
    """
    print("║ 🎯 FTP Progression                                       ║")

    if intelligence_path and intelligence_path.exists():
        # Try to load intelligence
        try:
            from cyclisme_training_logs.intelligence import TrainingIntelligence

            intelligence = TrainingIntelligence.load_from_file(intelligence_path)

            # Get PID correction
            result = intelligence.get_pid_correction(
                current_ftp=220,  # TODO: Get from athlete profile or latest test
                target_ftp=260,  # TODO: Get from goals
                dt=1.0,
            )

            current_ftp = 220
            target_ftp = 260
            gap = result["correction"]["error"]
            tss_adj = result["correction"]["tss_adjustment"]
            recommendation = result["recommendation"]

            print(
                f"║   Current: {current_ftp}W    Target: {target_ftp}W    Gap: {gap}W             ║"
            )
            print(f"║   PID Recommendation: {tss_adj:+.0f} TSS/week                      ║")
            print(f"║   {recommendation[:54]:<54} ║")
        except Exception as e:
            logger.debug(f"Could not load intelligence: {e}")
            print_ftp_mock_data()
    else:
        print_ftp_mock_data()

    print("║                                                          ║")


def print_ftp_mock_data() -> None:
    """Print mock FTP data when intelligence not available."""
    current_ftp = 220
    target_ftp = 260
    gap = 40

    print(f"║   Current: {current_ftp}W    Target: {target_ftp}W    Gap: {gap}W             ║")
    print("║   (Load intelligence file for PID recommendations)       ║")


def print_recent_learnings(intelligence_path: Path | None) -> None:
    """Print recent learnings.

    TODO: Integrate with cyclisme_training_logs.intelligence.training_intelligence.
    """
    print("║ 🧠 Recent Learnings                                      ║")

    if intelligence_path and intelligence_path.exists():
        try:
            from cyclisme_training_logs.intelligence import ConfidenceLevel, TrainingIntelligence

            intelligence = TrainingIntelligence.load_from_file(intelligence_path)

            # Get top 3 learnings (validated first)
            learnings = sorted(
                intelligence.learnings.values(),
                key=lambda lrn: (
                    lrn.confidence == ConfidenceLevel.VALIDATED,
                    lrn.confidence.value,
                    len(lrn.evidence),
                ),
                reverse=True,
            )[:3]

            for learning in learnings:
                confidence_icon = "✓" if learning.confidence == ConfidenceLevel.VALIDATED else "·"
                desc = learning.description[:50]
                conf = learning.confidence.value.lower()
                print(f"║   {confidence_icon} {desc:<48} ║")
                print(f"║     ({conf})                                         ║")

            if not learnings:
                print("║   (No learnings yet - run backfill-intelligence)     ║")
        except Exception as e:
            logger.debug(f"Could not load learnings: {e}")
            print_learnings_mock_data()
    else:
        print_learnings_mock_data()

    print("║                                                          ║")


def print_learnings_mock_data() -> None:
    """Print mock learnings when intelligence not available."""
    print("║   (Load intelligence file to see learnings)              ║")


def print_next_week_plan() -> None:
    """Print next week plan preview.

    TODO: Integrate with cyclisme_training_logs.planning.planning_manager.
    """
    print("║ 📅 Next Week Plan                                        ║")

    # Mock data (replace with real planning)
    print("║   Mon: Recovery (50 TSS)                                 ║")
    print("║   Tue: Sweet-Spot 2x10min (70 TSS)                       ║")
    print("║   Wed: Endurance 2h (80 TSS)                             ║")
    print("║   Thu: Rest                                              ║")
    print("║   Fri: VO2 5x5min (90 TSS)                               ║")
    print("║   Sat: Tempo 90min (100 TSS)                             ║")
    print("║   Sun: Endurance 3h (120 TSS)                            ║")


def print_dashboard_footer() -> None:
    """Print dashboard footer."""
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("💡 Tips:")
    print("   - Load intelligence: --intelligence ~/data/intelligence.json")
    print("   - Specific week: --week 2026-W02")
    print("   - Run backfill: poetry run backfill-intelligence")
    print()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Dashboard - Vue d'ensemble rapide entraînement")

    parser.add_argument(
        "--week", type=str, default=None, help="ISO week (YYYY-WXX). Default: current week"
    )

    parser.add_argument(
        "--intelligence",
        type=Path,
        default=None,
        help="Path to intelligence JSON file (for learnings, PID)",
    )

    args = parser.parse_args()

    # Get week
    week = args.week or get_current_week()

    # Print dashboard
    try:
        print_dashboard_header(week)
        print_current_week_stats(week)
        print_ftp_progression(args.intelligence)
        print_recent_learnings(args.intelligence)
        print_next_week_plan()
        print_dashboard_footer()
        return 0
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
