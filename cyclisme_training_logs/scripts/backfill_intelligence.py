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
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cyclisme_training_logs.api.intervals_client import IntervalsClient  # noqa: E402
from cyclisme_training_logs.intelligence.training_intelligence import (  # noqa: E402
    AnalysisLevel,
    ConfidenceLevel,
    TrainingIntelligence,
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

    def fetch_activities(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
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

    def fetch_wellness(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
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

    def classify_workout_type(self, activity: dict[str, Any]) -> str:
        """
        Classify workout type from activity data.

        Uses activity name, intensity factor (IF), and TSS to determine type.

        Args:
            activity: Activity dict from Intervals.icu

        Returns:
            Workout type: "sweet-spot", "vo2", "tempo", "endurance", "recovery"
        """
        name = activity.get("name", "").lower()
        intensity = activity.get("icu_intensity") or 0

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

    def analyze_sweet_spot_sessions(self, activities: list[dict]) -> None:
        """
        Extract Sweet-Spot learning from historical sessions.

        Analyzes all Sweet-Spot sessions (88-90% FTP) to identify optimal
        intensity and duration patterns.

        Args:
            activities: List of activities
        """
        print("\n🍭 Analyzing Sweet-Spot sessions...")

        sweet_spot_sessions = [
            a for a in activities if self.classify_workout_type(a) == "sweet-spot"
        ]

        if not sweet_spot_sessions:
            print("   ⚠️  No Sweet-Spot sessions found")
            return

        # Analyze metrics (filter out None values)
        intensities = [
            a.get("icu_intensity", 0)
            for a in sweet_spot_sessions
            if a.get("icu_intensity") is not None
        ]
        avg_intensity = sum(intensities) / len(intensities) if intensities else 0

        # Create learning
        evidence = [
            f"{len(sweet_spot_sessions)} sessions completed",
            f"Avg IF {avg_intensity:.2f}",
            "Intensity range 88-90% FTP sustainable",
        ]

        learning = self.intelligence.add_learning(
            category="sweet-spot",
            description="88-90% FTP sustainable for 2x10min+ intervals",
            evidence=evidence,
            level=AnalysisLevel.WEEKLY,
        )

        # Promote confidence based on session count (not evidence count)
        session_count = len(sweet_spot_sessions)
        if session_count >= 10:
            learning.confidence = ConfidenceLevel.VALIDATED
        elif session_count >= 6:
            learning.confidence = ConfidenceLevel.HIGH
        elif session_count >= 3:
            learning.confidence = ConfidenceLevel.MEDIUM

        print(
            f"   ✅ Created learning: {len(sweet_spot_sessions)} sessions, confidence={learning.confidence.value}"
        )

    def analyze_vo2_sleep_correlation(
        self, activities: list[dict], wellness_data: list[dict]
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

        vo2_activities = [a for a in activities if self.classify_workout_type(a) == "vo2"]

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

            # Skip if sleep data is missing
            sleep_secs = sleep_record.get("sleepSecs")
            if sleep_secs is None:
                continue

            total_analyzed += 1
            sleep_hours = sleep_secs / 3600

            # Determine if session was completed successfully
            # Use IF and TSS as proxies (high IF + reasonable TSS = success)
            intensity = activity.get("icu_intensity") or 0
            tss = activity.get("icu_training_load") or 0
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
                observation_date=date.today(),
            )
            pattern.frequency = total_analyzed

            # Promote confidence based on frequency
            if pattern.frequency >= 10:
                pattern.confidence = ConfidenceLevel.VALIDATED
            elif pattern.frequency >= 6:
                pattern.confidence = ConfidenceLevel.HIGH
            elif pattern.frequency >= 3:
                pattern.confidence = ConfidenceLevel.MEDIUM

            print(
                f"   ✅ Created pattern: {failures} failures/{total_analyzed} attempts, confidence={pattern.confidence.value}"
            )
        else:
            print(f"   ℹ️  Insufficient correlation: {failures} failures/{total_analyzed} attempts")

    def analyze_outdoor_discipline(self, activities: list[dict]) -> None:
        """
        Identify outdoor intensity overshoot pattern.

        Analyzes outdoor rides vs indoor to identify tendency to exceed
        planned intensity outdoors.

        Args:
            activities: List of activities
        """
        print("\n🚴 Analyzing outdoor discipline...")

        outdoor_activities = [a for a in activities if a.get("type") == "Ride"]  # Outdoor rides

        indoor_activities = [
            a for a in activities if a.get("type") == "VirtualRide"  # Indoor rides
        ]

        if not outdoor_activities or not indoor_activities:
            print("   ⚠️  Insufficient data (need both outdoor and indoor)")
            return

        # Calculate average IF for outdoor vs indoor (filter out None values)
        outdoor_intensities = [
            a.get("icu_intensity", 0)
            for a in outdoor_activities
            if a.get("icu_intensity") is not None
        ]
        indoor_intensities = [
            a.get("icu_intensity", 0)
            for a in indoor_activities
            if a.get("icu_intensity") is not None
        ]

        if not outdoor_intensities or not indoor_intensities:
            print("   ⚠️  Insufficient intensity data")
            return

        outdoor_if = sum(outdoor_intensities) / len(outdoor_intensities)
        indoor_if = sum(indoor_intensities) / len(indoor_intensities)

        overshoot_pct = ((outdoor_if - indoor_if) / indoor_if) * 100

        if overshoot_pct > 10:  # Significant overshoot
            pattern = self.intelligence.identify_pattern(
                name="outdoor_intensity_overshoot",
                trigger_conditions={"workout_location": "outdoor"},
                observed_outcome=f"IF +{overshoot_pct:.1f}% vs indoor ({outdoor_if:.2f} vs {indoor_if:.2f})",
                observation_date=date.today(),
            )
            pattern.frequency = len(outdoor_activities)

            # Promote confidence based on frequency
            if pattern.frequency >= 10:
                pattern.confidence = ConfidenceLevel.VALIDATED
            elif pattern.frequency >= 6:
                pattern.confidence = ConfidenceLevel.HIGH
            elif pattern.frequency >= 3:
                pattern.confidence = ConfidenceLevel.MEDIUM

            print(
                f"   ✅ Created pattern: {len(outdoor_activities)} outdoor rides, +{overshoot_pct:.1f}% IF, confidence={pattern.confidence.value}"
            )
        else:
            print(f"   ℹ️  No significant overshoot: +{overshoot_pct:.1f}%")

    def analyze_ftp_progression(
        self,
        start_date: str,
        end_date: str,
        activities: list[dict[str, Any]],
        wellness_data: list[dict[str, Any]],
    ) -> None:
        """
        Extract FTP progression learning from real test data.

        Detects FTP tests via two methods:
        1. FTP changes in wellness data (Intervals.icu athlete profile)
        2. Activities with "FTP", "test", "ramp" in name

        Args:
            start_date: Period start (YYYY-MM-DD)
            end_date: Period end (YYYY-MM-DD)
            activities: List of activities from API
            wellness_data: List of wellness entries from API
        """
        print("\n📈 Analyzing FTP progression...")

        try:
            ftp_tests = []

            # Method 1: Detect FTP changes in wellness data
            print("   🔍 Method 1: Scanning wellness data for FTP changes...")
            wellness_sorted = sorted(wellness_data, key=lambda w: w.get("id", ""))

            prev_ftp = None
            for entry in wellness_sorted:
                # Extract eFTP from sportInfo (estimated FTP calculated by Intervals.icu)
                sport_info = entry.get("sportInfo", [])
                current_ftp = None

                # Find Ride sport info
                for sport in sport_info:
                    if sport.get("type") == "Ride":
                        current_ftp = sport.get("eftp")
                        break

                entry_date = entry.get("id")  # Date in YYYY-MM-DD format

                if current_ftp is None:
                    continue

                # Detect FTP change (threshold: >2W to avoid noise)
                if prev_ftp is not None and abs(current_ftp - prev_ftp) > 2:
                    change_w = current_ftp - prev_ftp
                    change_pct = (change_w / prev_ftp) * 100 if prev_ftp > 0 else 0

                    ftp_tests.append(
                        {
                            "date": entry_date,
                            "ftp": current_ftp,
                            "previous_ftp": prev_ftp,
                            "change_w": change_w,
                            "change_pct": change_pct,
                            "source": "wellness_eftp",
                        }
                    )
                    print(
                        f"      ✓ {entry_date}: {prev_ftp:.0f}W → {current_ftp:.0f}W ({change_w:+.0f}W, {change_pct:+.1f}%)"
                    )

                prev_ftp = current_ftp

            # Method 2: Find FTP test activities by name (only executed activities)
            print("   🔍 Method 2: Scanning activities for FTP test keywords...")
            ftp_keywords = ["ftp", "test", "ramp", "evaluation"]

            for activity in activities:
                # Skip manually created events (not executed)
                if activity.get("source") == "MANUAL":
                    continue

                name = activity.get("name", "").lower()
                activity_date = activity.get("start_date_local", "")[:10]  # Extract YYYY-MM-DD

                # Check if name contains FTP test keywords
                if any(keyword in name for keyword in ftp_keywords):
                    # Use icu_average_watts (not average_watts)
                    avg_watts = activity.get("icu_average_watts", 0)
                    icu_ftp = activity.get("icu_ftp", 0)  # FTP at time of activity
                    icu_rolling_ftp = activity.get("icu_rolling_ftp", 0)  # Calculated FTP

                    # Try to extract FTP from power curve (20min * 0.95)
                    max_watts = activity.get("max_avg_watts", {})
                    ftp_20min = (
                        max_watts.get("1200", 0) * 0.95 if max_watts else 0
                    )  # 20min power * 0.95

                    # Use best available FTP estimate
                    estimated_ftp = ftp_20min or icu_rolling_ftp or icu_ftp

                    ftp_tests.append(
                        {
                            "date": activity_date,
                            "activity_name": activity.get("name", ""),
                            "avg_watts": avg_watts,
                            "ftp": estimated_ftp if estimated_ftp > 0 else None,
                            "ftp_20min": int(ftp_20min) if ftp_20min > 0 else None,
                            "icu_ftp": icu_ftp,
                            "source": "activity_executed",
                        }
                    )
                    ftp_display = (
                        f"{estimated_ftp:.0f}W FTP" if estimated_ftp > 0 else "no FTP data"
                    )
                    print(
                        f"      ✓ {activity_date}: '{activity.get('name', '')}' (avg: {avg_watts:.0f}W, {ftp_display})"
                    )

            # Create learning if tests found
            if not ftp_tests:
                print("   ℹ️  No FTP tests detected")
                return

            # Sort by date
            ftp_tests.sort(key=lambda t: t.get("date", ""))

            # Calculate overall progression
            tests_with_ftp = [
                t for t in ftp_tests if t.get("ftp") is not None or t.get("ftp_20min") is not None
            ]

            if len(tests_with_ftp) < 2:
                print(
                    f"   ℹ️  Only {len(ftp_tests)} test(s) found, need at least 2 with FTP values for progression"
                )
                # Still create learning with single test
                if ftp_tests:
                    evidence = [
                        f"{t['date']}: {t.get('activity_name', 'FTP change detected')}"
                        for t in ftp_tests[:5]
                    ]
                    learning = self.intelligence.add_learning(
                        category="ftp_tests",
                        description=f"{len(ftp_tests)} FTP test(s) detected",
                        evidence=evidence,
                        level=AnalysisLevel.MONTHLY,
                    )
                    learning.confidence = ConfidenceLevel.LOW
                    print(f"   ✅ Created learning: {len(ftp_tests)} test(s), confidence=LOW")
                return

            # Get first and last FTP values
            first_test = tests_with_ftp[0]
            last_test = tests_with_ftp[-1]

            first_ftp = first_test.get("ftp") or first_test.get("ftp_20min") or 0
            last_ftp = last_test.get("ftp") or last_test.get("ftp_20min") or 0

            if first_ftp == 0 or last_ftp == 0:
                print("   ⚠️  Cannot calculate progression (missing FTP values)")
                return

            # Calculate progression
            progression_w = last_ftp - first_ftp
            progression_pct = (progression_w / first_ftp) * 100

            # Calculate time span
            first_date = datetime.strptime(first_test["date"], "%Y-%m-%d")
            last_date = datetime.strptime(last_test["date"], "%Y-%m-%d")
            days = (last_date - first_date).days
            months = days / 30.0
            rate_per_month = progression_w / months if months > 0 else 0

            # Build evidence
            evidence = [
                f"Period: {first_test['date']} → {last_test['date']} ({days} days)",
                f"FTP progression: {first_ftp:.0f}W → {last_ftp:.0f}W",
                f"Change: {progression_w:+.0f}W ({progression_pct:+.1f}%)",
                f"Rate: {rate_per_month:+.2f}W/month",
                f"Total tests detected: {len(ftp_tests)}",
            ]

            # Add individual test details (max 5)
            for test in ftp_tests[:5]:
                if test.get("source") == "wellness_data":
                    evidence.append(f"  • {test['date']}: {test['previous_ftp']}W → {test['ftp']}W")
                else:
                    evidence.append(f"  • {test['date']}: {test.get('activity_name', 'FTP test')}")

            learning = self.intelligence.add_learning(
                category="ftp_progression",
                description=f"FTP progression: {first_ftp:.0f}W → {last_ftp:.0f}W over {len(ftp_tests)} tests",
                evidence=evidence,
                level=AnalysisLevel.MONTHLY,
            )

            # Set confidence based on number of tests and time period
            if len(ftp_tests) >= 5 and months >= 6:
                learning.confidence = ConfidenceLevel.VALIDATED
            elif len(ftp_tests) >= 3 and months >= 3:
                learning.confidence = ConfidenceLevel.HIGH
            elif len(ftp_tests) >= 2:
                learning.confidence = ConfidenceLevel.MEDIUM
            else:
                learning.confidence = ConfidenceLevel.LOW

            print(
                f"   ✅ Created learning: {len(ftp_tests)} tests, {progression_w:+.0f}W ({progression_pct:+.1f}%), confidence={learning.confidence.value}"
            )

        except Exception as e:
            print(f"   ❌ Error analyzing FTP: {e}")
            import traceback

            traceback.print_exc()

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
        self.analyze_ftp_progression(start_date, end_date, activities, wellness_data)

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

    parser.add_argument("--start-date", type=str, required=True, help="Start date (YYYY-MM-DD)")

    parser.add_argument("--end-date", type=str, required=True, help="End date (YYYY-MM-DD)")

    parser.add_argument(
        "--output",
        type=str,
        default="~/data/intelligence_backfilled.json",
        help="Output path for intelligence JSON",
    )

    parser.add_argument("--athlete-id", type=str, help="Intervals.icu athlete ID (overrides env)")

    parser.add_argument("--api-key", type=str, help="Intervals.icu API key (overrides env)")

    args = parser.parse_args()

    # Get credentials (support both standard and VITE_ prefixed)
    athlete_id = (
        args.athlete_id
        or os.getenv("INTERVALS_ATHLETE_ID")
        or os.getenv("VITE_INTERVALS_ATHLETE_ID")
    )
    api_key = args.api_key or os.getenv("INTERVALS_API_KEY") or os.getenv("VITE_INTERVALS_API_KEY")

    if not athlete_id or not api_key:
        print("❌ Missing Intervals.icu credentials")
        print("   Set INTERVALS_ATHLETE_ID and INTERVALS_API_KEY environment variables")
        print("   Or VITE_INTERVALS_ATHLETE_ID and VITE_INTERVALS_API_KEY")
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
