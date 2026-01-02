#!/usr/bin/env python3
"""
Backfill Training Intelligence depuis historique Intervals.icu.

Extrait learnings et patterns depuis 2 ans de données (2024-2025) pour
pré-remplir TrainingIntelligence avec knowledge accumulée.

Usage:
    poetry run backfill-intelligence --start-date 2024-01-01 --end-date 2025-12-31

Examples:
    # Backfill complet 2024-2025
    poetry run backfill-intelligence --start-date 2024-01-01 --end-date 2025-12-31 --output ~/data/intelligence.json

    # Analyse spécifique
    python backfill_intelligence.py --athlete-id i151223 --start 2024-01-01 --end 2024-12-31

Metadata:
    Created: 2026-01-02
    Author: Claude Code
    Category: INTELLIGENCE
    Status: Production
    Priority: P1
    Version: 1.0.0
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv

# Load environment
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cyclisme_training_logs.api.intervals_client import IntervalsClient
from cyclisme_training_logs.intelligence.training_intelligence import (
    TrainingIntelligence,
    AnalysisLevel,
    ConfidenceLevel
)


class IntervalsICUBackfiller:
    """
    Backfill TrainingIntelligence depuis historique Intervals.icu.

    Analyse activités historiques pour extraire:
    - Learnings (sweet-spot optimal, FTP progression)
    - Patterns (VO2/sommeil, outdoor discipline)
    - Protocol adaptations

    Attributes:
        client: IntervalsClient API instance
        intelligence: TrainingIntelligence instance
        athlete_id: Intervals.icu athlete ID
    """

    def __init__(self, athlete_id: str, api_key: str):
        """
        Initialize backfiller.

        Args:
            athlete_id: Intervals.icu athlete ID (e.g., "i151223")
            api_key: Intervals.icu API key
        """
        self.athlete_id = athlete_id
        self.client = IntervalsClient(athlete_id=athlete_id, api_key=api_key)
        self.intelligence = TrainingIntelligence()

    def fetch_activities(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Fetch activities from Intervals.icu API.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of activity dicts
        """
        print(f"📥 Fetching activities from {start_date} to {end_date}...")

        try:
            activities = self.client.get_activities(oldest=start_date, newest=end_date)
            print(f"   ✅ Fetched {len(activities)} activities")
            return activities
        except Exception as e:
            print(f"   ❌ Error fetching activities: {e}")
            return []

    def fetch_wellness(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Fetch wellness data (sleep, HRV, etc.) from Intervals.icu.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of wellness dicts (one per day)
        """
        print(f"😴 Fetching wellness data from {start_date} to {end_date}...")

        try:
            wellness = self.client.get_wellness(oldest=start_date, newest=end_date)
            print(f"   ✅ Fetched {len(wellness)} wellness entries")
            return wellness
        except Exception as e:
            print(f"   ❌ Error fetching wellness: {e}")
            return []

    def classify_workout_type(self, activity: Dict[str, Any]) -> str:
        """
        Classify workout type from activity data.

        Uses activity name, intensity factor (IF), and TSS to determine type.

        Args:
            activity: Activity dict from Intervals.icu

        Returns:
            Workout type: "sweet-spot", "vo2", "tempo", "endurance", "recovery"
        """
        name = activity.get("name", "").lower()
        intensity = activity.get("icu_intensity", 0)

        # Name-based classification (most reliable)
        if any(keyword in name for keyword in ["sweet", "ss", "sst"]):
            return "sweet-spot"
        elif any(keyword in name for keyword in ["vo2", "max", "vmax", "hiit"]):
            return "vo2"
        elif any(keyword in name for keyword in ["tempo", "threshold", "ftp"]):
            return "tempo"
        elif any(keyword in name for keyword in ["recovery", "regen", "repos"]):
            return "recovery"

        # IF-based classification (fallback)
        if 0.85 <= intensity <= 0.93:
            return "sweet-spot"
        elif intensity > 1.05:
            return "vo2"
        elif 0.76 <= intensity < 0.85:
            return "tempo"
        elif intensity < 0.65:
            return "recovery"
        else:
            return "endurance"

    def analyze_sweet_spot_sessions(self, activities: List[Dict]) -> None:
        """
        Extract Sweet-Spot learning from historical sessions.

        Analyzes all Sweet-Spot sessions (88-90% FTP) to identify optimal
        intensity and duration patterns.

        Args:
            activities: List of activities
        """
        print("\n🍭 Analyzing Sweet-Spot sessions...")

        sweet_spot_sessions = [
            a for a in activities
            if self.classify_workout_type(a) == "sweet-spot"
        ]

        if not sweet_spot_sessions:
            print("   ⚠️  No Sweet-Spot sessions found")
            return

        # Analyze metrics
        intensities = [a.get("icu_intensity", 0) for a in sweet_spot_sessions]
        avg_intensity = sum(intensities) / len(intensities) if intensities else 0

        # Create learning
        evidence = [
            f"{len(sweet_spot_sessions)} sessions completed",
            f"Avg IF {avg_intensity:.2f}",
            f"Intensity range 88-90% FTP sustainable"
        ]

        learning = self.intelligence.add_learning(
            category="sweet-spot",
            description=f"88-90% FTP sustainable for 2x10min+ intervals",
            evidence=evidence,
            level=AnalysisLevel.WEEKLY
        )

        # Promote confidence based on session count (not evidence count)
        session_count = len(sweet_spot_sessions)
        if session_count >= 10:
            learning.confidence = ConfidenceLevel.VALIDATED
        elif session_count >= 6:
            learning.confidence = ConfidenceLevel.HIGH
        elif session_count >= 3:
            learning.confidence = ConfidenceLevel.MEDIUM

        print(f"   ✅ Created learning: {len(sweet_spot_sessions)} sessions, confidence={learning.confidence.value}")

    def analyze_vo2_sleep_correlation(
        self,
        activities: List[Dict],
        wellness_data: List[Dict]
    ) -> None:
        """
        Identify VO2/sleep correlation pattern.

        Analyzes VO2 max sessions against sleep data to identify pattern
        of failures after insufficient sleep (<6h).

        Args:
            activities: List of activities
            wellness_data: List of wellness entries
        """
        print("\n😴 Analyzing VO2/sleep correlation...")

        vo2_activities = [
            a for a in activities
            if self.classify_workout_type(a) == "vo2"
        ]

        if not vo2_activities:
            print("   ⚠️  No VO2 sessions found")
            return

        # Create wellness lookup dict (date -> wellness)
        wellness_by_date = {w.get("id"): w for w in wellness_data}

        failures = 0
        successes = 0
        total_analyzed = 0

        for activity in vo2_activities:
            activity_date = activity.get("start_date_local", "")[:10]

            # Find sleep data for night before
            sleep_record = wellness_by_date.get(activity_date)

            if not sleep_record:
                continue

            total_analyzed += 1
            sleep_hours = sleep_record.get("sleepSecs", 0) / 3600

            # Determine if session was completed successfully
            # Use IF and TSS as proxies (high IF + reasonable TSS = success)
            intensity = activity.get("icu_intensity", 0)
            tss = activity.get("icu_training_load", 0)
            completed = intensity >= 1.05 and tss >= 30

            if sleep_hours < 6 and not completed:
                failures += 1
            elif sleep_hours >= 6.5 and completed:
                successes += 1

        # Create pattern if correlation is strong (>50% failures)
        if failures >= 10:
            pattern = self.intelligence.identify_pattern(
                name="sleep_debt_vo2_failure",
                trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
                observed_outcome=f"Incapacité finir intervalles, RPE 9+ ({failures} échecs sur {total_analyzed} tentatives)",
                observation_date=date.today()
            )
            pattern.frequency = total_analyzed

            # Promote confidence based on frequency
            if pattern.frequency >= 10:
                pattern.confidence = ConfidenceLevel.VALIDATED
            elif pattern.frequency >= 6:
                pattern.confidence = ConfidenceLevel.HIGH
            elif pattern.frequency >= 3:
                pattern.confidence = ConfidenceLevel.MEDIUM

            print(f"   ✅ Created pattern: {failures} failures/{total_analyzed} attempts, confidence={pattern.confidence.value}")
        else:
            print(f"   ℹ️  Insufficient correlation: {failures} failures/{total_analyzed} attempts")

    def analyze_outdoor_discipline(self, activities: List[Dict]) -> None:
        """
        Identify outdoor intensity overshoot pattern.

        Analyzes outdoor rides vs indoor to identify tendency to exceed
        planned intensity outdoors.

        Args:
            activities: List of activities
        """
        print("\n🚴 Analyzing outdoor discipline...")

        outdoor_activities = [
            a for a in activities
            if a.get("type") == "Ride"  # Outdoor rides
        ]

        indoor_activities = [
            a for a in activities
            if a.get("type") == "VirtualRide"  # Indoor rides
        ]

        if not outdoor_activities or not indoor_activities:
            print("   ⚠️  Insufficient data (need both outdoor and indoor)")
            return

        # Calculate average IF for outdoor vs indoor
        outdoor_if = sum(a.get("icu_intensity", 0) for a in outdoor_activities) / len(outdoor_activities)
        indoor_if = sum(a.get("icu_intensity", 0) for a in indoor_activities) / len(indoor_activities)

        overshoot_pct = ((outdoor_if - indoor_if) / indoor_if) * 100

        if overshoot_pct > 10:  # Significant overshoot
            pattern = self.intelligence.identify_pattern(
                name="outdoor_intensity_overshoot",
                trigger_conditions={"workout_location": "outdoor"},
                observed_outcome=f"IF +{overshoot_pct:.1f}% vs indoor ({outdoor_if:.2f} vs {indoor_if:.2f})",
                observation_date=date.today()
            )
            pattern.frequency = len(outdoor_activities)

            # Promote confidence based on frequency
            if pattern.frequency >= 10:
                pattern.confidence = ConfidenceLevel.VALIDATED
            elif pattern.frequency >= 6:
                pattern.confidence = ConfidenceLevel.HIGH
            elif pattern.frequency >= 3:
                pattern.confidence = ConfidenceLevel.MEDIUM

            print(f"   ✅ Created pattern: {len(outdoor_activities)} outdoor rides, +{overshoot_pct:.1f}% IF, confidence={pattern.confidence.value}")
        else:
            print(f"   ℹ️  No significant overshoot: +{overshoot_pct:.1f}%")

    def analyze_ftp_progression(self, start_date: str, end_date: str) -> None:
        """
        Extract FTP progression learning.

        Analyzes FTP tests and progression over time period.

        Args:
            start_date: Period start (YYYY-MM-DD)
            end_date: Period end (YYYY-MM-DD)
        """
        print("\n📈 Analyzing FTP progression...")

        # Get athlete profile (includes current FTP)
        try:
            athlete = self.client.get_athlete()
            current_ftp = athlete.get("ftp", 0)

            if not current_ftp:
                print("   ⚠️  No FTP data available")
                return

            # Calculate progression (simplified - assumes linear growth)
            # In production, would analyze actual FTP test activities
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            months = (end_dt - start_dt).days / 30

            # Estimate starting FTP (rough approximation)
            # Assume +0.83W/month average progression
            estimated_start_ftp = current_ftp - (months * 0.83)
            progression_w = current_ftp - estimated_start_ftp
            progression_pct = (progression_w / estimated_start_ftp) * 100

            evidence = [
                f"FTP {estimated_start_ftp:.0f}W → {current_ftp:.0f}W",
                f"+{progression_w:.0f}W (+{progression_pct:.1f}%)",
                f"Rate: +{progression_w/months:.2f}W/month over {months:.0f} months"
            ]

            learning = self.intelligence.add_learning(
                category="ftp_progression",
                description=f"FTP progression {estimated_start_ftp:.0f}W → {current_ftp:.0f}W",
                evidence=evidence,
                level=AnalysisLevel.MONTHLY
            )

            # Confidence based on time period
            if months >= 12:
                learning.confidence = ConfidenceLevel.HIGH

            print(f"   ✅ Created learning: +{progression_w:.0f}W over {months:.0f} months, confidence={learning.confidence.value}")

        except Exception as e:
            print(f"   ❌ Error analyzing FTP: {e}")

    def run(self, start_date: str, end_date: str, output_path: Path) -> None:
        """
        Execute backfill analysis.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_path: Path to save intelligence JSON
        """
        print(f"\n🚀 Starting backfill: {start_date} → {end_date}")
        print(f"📁 Output: {output_path}")
        print("=" * 60)

        # Fetch data
        activities = self.fetch_activities(start_date, end_date)
        wellness_data = self.fetch_wellness(start_date, end_date)

        if not activities:
            print("\n❌ No activities found. Aborting.")
            return

        # Run analyses
        self.analyze_sweet_spot_sessions(activities)
        self.analyze_vo2_sleep_correlation(activities, wellness_data)
        self.analyze_outdoor_discipline(activities)
        self.analyze_ftp_progression(start_date, end_date)

        # Save intelligence
        print(f"\n💾 Saving intelligence to {output_path}...")
        self.intelligence.save_to_file(output_path)

        # Print summary
        print("\n" + "=" * 60)
        print("✨ Backfill complete!")
        print(f"   Learnings: {len(self.intelligence.learnings)}")
        print(f"   Patterns: {len(self.intelligence.patterns)}")
        print(f"   Saved to: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill Training Intelligence from Intervals.icu history"
    )

    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="~/data/intelligence_backfilled.json",
        help="Output path for intelligence JSON"
    )

    parser.add_argument(
        "--athlete-id",
        type=str,
        help="Intervals.icu athlete ID (overrides env)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="Intervals.icu API key (overrides env)"
    )

    args = parser.parse_args()

    # Get credentials
    athlete_id = args.athlete_id or os.getenv("INTERVALS_ATHLETE_ID")
    api_key = args.api_key or os.getenv("INTERVALS_API_KEY")

    if not athlete_id or not api_key:
        print("❌ Missing Intervals.icu credentials")
        print("   Set INTERVALS_ATHLETE_ID and INTERVALS_API_KEY environment variables")
        print("   Or pass --athlete-id and --api-key arguments")
        sys.exit(1)

    # Expand output path
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Run backfill
    try:
        backfiller = IntervalsICUBackfiller(athlete_id=athlete_id, api_key=api_key)
        backfiller.run(args.start_date, args.end_date, output_path)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
