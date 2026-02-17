#!/usr/bin/env python3
"""
PID Daily Evaluation - Complete Training Intelligence Pipeline.

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
    Version: 1.0.0
    Sprint: R9++
    Replaces: aggregate_adherence_to_intelligence.py (integrated)
    Related: check_workout_adherence.py (22:00 data source)
"""

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cyclisme_training_logs.api.intervals_client import IntervalsClient  # noqa: E402
from cyclisme_training_logs.config import get_intervals_config  # noqa: E402
from cyclisme_training_logs.intelligence.discrete_pid_controller import (  # noqa: E402
    DiscretePIDController,
    compute_discrete_pid_gains_from_intelligence,
)
from cyclisme_training_logs.intelligence.training_intelligence import (  # noqa: E402
    AnalysisLevel,
    ConfidenceLevel,
    TrainingIntelligence,
)


class PIDDailyEvaluator:
    """
    Complete PID evaluation pipeline.

    Integrates all data sources to provide intelligent training load recommendations
    via discrete PID controller with multi-criteria validation.

    Attributes:
        client: IntervalsClient for API access
        intelligence: TrainingIntelligence instance
        adherence_file: Path to workout_adherence.jsonl
        workouts_history: Path to workouts-history.md
        evaluation_log: Path to pid_evaluation.jsonl
        intelligence_file: Path to intelligence.json
        dry_run: If True, don't save files
    """

    def __init__(
        self,
        adherence_file: Path | None = None,
        workouts_history: Path | None = None,
        evaluation_log: Path | None = None,
        intelligence_file: Path | None = None,
        dry_run: bool = False,
    ):
        """
        Initialize PID evaluator.

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
        # Point to logs/weekly_reports/ directory for scanning weekly workout history files
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

    def load_adherence_data(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        """
        Load adherence data for date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of adherence records
        """
        if not self.adherence_file.exists():
            print(f"⚠️  No adherence data at {self.adherence_file}")
            return []

        print(f"\n📥 Loading adherence data ({start_date} → {end_date})")

        records = []
        with open(self.adherence_file, encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    record_date = datetime.strptime(record["date"], "%Y-%m-%d").date()

                    if start_date <= record_date <= end_date:
                        records.append(record)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        print(f"   ✅ {len(records)} records loaded")
        return records

    def extract_cardiovascular_coupling(self, start_date: date, end_date: date) -> list[float]:
        """
        Extract cardiovascular coupling (découplage) from weekly workout history files.

        Scans logs/weekly_reports/S0XX/workout_history_S0XX.md files for découplage values.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of découplage percentages (as decimals, e.g., 0.062 for 6.2%)
        """
        if not self.workouts_history.exists():
            print(f"⚠️  Weekly reports directory not found at {self.workouts_history}")
            return []

        print(f"\n📥 Extracting cardiovascular coupling ({start_date} → {end_date})")

        coupling_values = []

        # Regex patterns for découplage extraction
        # Matches: "découplage cardiovasculaire excellent (1.6%)" or "découplage 4.1%"
        patterns = [
            r"découplage\s+cardiovasculaire\s+\w+\s*\((\d+\.?\d*)\s*%\)",  # (1.6%)
            r"découplage\s+(\d+\.?\d*)\s*%",  # 4.1%
        ]

        # Scan all weekly workout history files
        workout_files = sorted(self.workouts_history.glob("*/workout_history_*.md"))
        print(f"   📁 Found {len(workout_files)} weekly files")

        for workout_file in workout_files:
            with open(workout_file, encoding="utf-8") as f:
                content = f.read()

            # Extract all découplage values from the file
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    coupling_pct = float(match.group(1))
                    # Convert to decimal (6.2% → 0.062)
                    coupling_values.append(abs(coupling_pct) / 100.0)

        print(f"   ✅ {len(coupling_values)} cardiovascular coupling values extracted")
        return coupling_values

    def calculate_tss_completion(self, start_date: date, end_date: date) -> float:
        """
        Calculate TSS completion rate from Intervals.icu.

        Compares planned TSS (events) vs realized TSS (activities).

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            TSS completion rate (0.0 - 1.0)
        """
        print(f"\n📥 Calculating TSS completion ({start_date} → {end_date})")

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        try:
            # Get planned workouts
            events = self.client.get_events(oldest=start_str, newest=end_str)
            planned_workouts = [
                e
                for e in events
                if e.get("category") == "WORKOUT" and not e.get("name", "").startswith("[")
            ]

            # Get completed activities
            activities = self.client.get_activities(oldest=start_str, newest=end_str)

            # Calculate TSS
            planned_tss = sum(e.get("icu_training_load", 0) for e in planned_workouts)
            realized_tss = sum(a.get("icu_training_load", 0) for a in activities)

            completion_rate = realized_tss / planned_tss if planned_tss > 0 else 1.0

            print(f"   Planned TSS: {planned_tss:.0f}")
            print(f"   Realized TSS: {realized_tss:.0f}")
            print(f"   Completion: {completion_rate * 100:.1f}%")

            return completion_rate

        except Exception as e:
            print(f"   ⚠️  Error calculating TSS: {e}")
            return 1.0  # Assume 100% if can't calculate

    def calculate_cycle_metrics(self, start_date: date, end_date: date) -> dict[str, Any]:
        """
        Calculate all metrics needed for PID evaluation.

        Args:
            start_date: Cycle start
            end_date: Cycle end

        Returns:
            Dict with keys:
            - adherence_rate: float (0.0 - 1.0)
            - avg_cardiovascular_coupling: float (e.g., 0.062 for 6.2%)
            - tss_completion_rate: float (0.0 - 1.0)
            - days_with_data: int
            - total_workouts: int
        """
        print(f"\n{'=' * 60}")
        print("📊 Calculating Cycle Metrics")
        print(f"{'=' * 60}")
        print(f"Period: {start_date} → {end_date}")

        # 1. Adherence (discipline)
        adherence_records = self.load_adherence_data(start_date, end_date)
        total_planned = sum(r["planned_workouts"] for r in adherence_records)
        total_completed = sum(r["completed_activities"] for r in adherence_records)
        adherence_rate = total_completed / total_planned if total_planned > 0 else 1.0

        # 2. Cardiovascular coupling (quality)
        coupling_values = self.extract_cardiovascular_coupling(start_date, end_date)
        avg_coupling = sum(coupling_values) / len(coupling_values) if coupling_values else 0.05

        # 3. TSS completion (capacity)
        tss_completion = self.calculate_tss_completion(start_date, end_date)

        metrics = {
            "adherence_rate": adherence_rate,
            "avg_cardiovascular_coupling": avg_coupling,
            "tss_completion_rate": tss_completion,
            "days_with_data": len(adherence_records),
            "total_workouts": total_completed,
        }

        print("\n📊 Metrics Summary:")
        print(f"   Adherence Rate: {adherence_rate * 100:.1f}% (discipline)")
        print(f"   Avg Cardiovascular Coupling: {avg_coupling * 100:.1f}% (quality)")
        print(f"   TSS Completion: {tss_completion * 100:.1f}% (capacity)")
        print(f"   Workouts: {total_completed} completed")
        print(f"   Days: {len(adherence_records)} with data")

        return metrics

    def create_intelligence_learnings(
        self,
        metrics: dict[str, Any],
        start_date: date,
        end_date: date,
    ) -> None:
        """
        Create learnings in TrainingIntelligence from metrics.

        Args:
            metrics: Cycle metrics dict
            start_date: Period start
            end_date: Period end
        """
        print(f"\n{'=' * 60}")
        print("🧠 Creating Intelligence Learnings")
        print(f"{'=' * 60}")

        days = metrics["days_with_data"]
        adherence = metrics["adherence_rate"]
        coupling = metrics["avg_cardiovascular_coupling"]
        tss_completion = metrics["tss_completion_rate"]

        # Learning 1: Adherence (discipline)
        adherence_evidence = [
            f"Période: {start_date} → {end_date} ({days} jours)",
            f"Taux adhérence: {adherence * 100:.1f}%",
            f"Workouts complétés: {metrics['total_workouts']}",
        ]

        if adherence >= 0.90:
            adherence_desc = f"Discipline excellente: {adherence * 100:.1f}% adhérence"
            impact = "LOW"
        elif adherence >= 0.80:
            adherence_desc = f"Discipline correcte: {adherence * 100:.1f}% adhérence"
            impact = "MEDIUM"
        else:
            adherence_desc = f"Discipline faible: {adherence * 100:.1f}% - Action requise"
            impact = "HIGH"

        learning_adh = self.intelligence.add_learning(
            category="adherence",
            description=adherence_desc,
            evidence=adherence_evidence,
            level=AnalysisLevel.WEEKLY,
        )
        learning_adh.impact = impact

        # Set confidence based on data quantity
        if days >= 35:
            learning_adh.confidence = ConfidenceLevel.VALIDATED
        elif days >= 21:
            learning_adh.confidence = ConfidenceLevel.HIGH
        elif days >= 14:
            learning_adh.confidence = ConfidenceLevel.MEDIUM
        else:
            learning_adh.confidence = ConfidenceLevel.LOW

        print(f"   ✅ Adherence learning: {learning_adh.confidence.value}")

        # Learning 2: Cardiovascular quality
        coupling_evidence = [
            f"Période: {start_date} → {end_date}",
            f"Découplage moyen: {coupling * 100:.1f}%",
            "Seuil optimal: <7.5%",
        ]

        if coupling <= 0.075:
            coupling_desc = f"Qualité cardiovasculaire excellente: {coupling * 100:.1f}% découplage"
            impact = "LOW"
        elif coupling <= 0.085:
            coupling_desc = f"Qualité cardiovasculaire dégradée: {coupling * 100:.1f}%"
            impact = "MEDIUM"
        else:
            coupling_desc = (
                f"Surcharge détectée: {coupling * 100:.1f}% découplage - Repos nécessaire"
            )
            impact = "HIGH"

        learning_cv = self.intelligence.add_learning(
            category="cardiovascular_quality",
            description=coupling_desc,
            evidence=coupling_evidence,
            level=AnalysisLevel.WEEKLY,
        )
        learning_cv.impact = impact
        learning_cv.confidence = learning_adh.confidence  # Same confidence

        print(f"   ✅ Cardiovascular learning: {learning_cv.confidence.value}")

        # Learning 3: TSS capacity
        tss_evidence = [
            f"Période: {start_date} → {end_date}",
            f"Taux complétion TSS: {tss_completion * 100:.1f}%",
        ]

        if tss_completion >= 0.90:
            tss_desc = f"Capacité TSS excellente: {tss_completion * 100:.1f}%"
            impact = "LOW"
        elif tss_completion >= 0.85:
            tss_desc = f"Capacité TSS limite: {tss_completion * 100:.1f}%"
            impact = "MEDIUM"
        else:
            tss_desc = f"Capacité TSS insuffisante: {tss_completion * 100:.1f}%"
            impact = "HIGH"

        learning_tss = self.intelligence.add_learning(
            category="tss_capacity",
            description=tss_desc,
            evidence=tss_evidence,
            level=AnalysisLevel.WEEKLY,
        )
        learning_tss.impact = impact
        learning_tss.confidence = learning_adh.confidence

        print(f"   ✅ TSS capacity learning: {learning_tss.confidence.value}")

    def evaluate_pid_correction(
        self,
        measured_ftp: float,
        cycle_duration_weeks: int,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluate PID correction with enhanced validation.

        Args:
            measured_ftp: FTP mesurée (W)
            cycle_duration_weeks: Durée cycle (semaines)
            metrics: Cycle metrics dict

        Returns:
            PID correction result dict
        """
        print(f"\n{'=' * 60}")
        print("🎛️  PID Correction Evaluation")
        print(f"{'=' * 60}")

        # Calculate adaptive gains from intelligence
        gains = compute_discrete_pid_gains_from_intelligence(self.intelligence)
        print("\nAdaptive PID Gains:")
        print(f"   Kp: {gains['kp']:.4f}")
        print(f"   Ki: {gains['ki']:.4f}")
        print(f"   Kd: {gains['kd']:.4f}")

        # TODO: Get FTP setpoint from athlete profile or config
        # For now, use a reasonable default
        setpoint = 260  # Example FTP target

        # Create PID controller
        controller = DiscretePIDController(
            kp=gains["kp"],
            ki=gains["ki"],
            kd=gains["kd"],
            setpoint=setpoint,
        )

        # Compute enhanced correction
        result = controller.compute_cycle_correction_enhanced(
            measured_ftp=measured_ftp,
            cycle_duration_weeks=cycle_duration_weeks,
            adherence_rate=metrics["adherence_rate"],
            avg_cardiovascular_coupling=metrics["avg_cardiovascular_coupling"],
            tss_completion_rate=metrics["tss_completion_rate"],
        )

        print("\n📊 PID Results:")
        print(f"   FTP Error: {result['error']:.1f}W")
        print(f"   TSS Adjustment: {result['tss_per_week_adjusted']} TSS/week")
        print(f"   Validated: {'✅' if result['validation']['validated'] else '⚠️ '}")
        print(f"   Confidence: {result['validation']['confidence']}")

        if result["validation"]["red_flags"]:
            print("\n🚨 Red Flags:")
            for flag in result["validation"]["red_flags"]:
                print(f"   • {flag}")

        print("\n💡 Recommendation:")
        print(f"   {result['recommendation']}")

        return result

    def log_evaluation(
        self,
        start_date: date,
        end_date: date,
        metrics: dict[str, Any],
        pid_result: dict[str, Any] | None = None,
    ) -> None:
        """
        Log evaluation to pid_evaluation.jsonl.

        Args:
            start_date: Cycle start
            end_date: Cycle end
            metrics: Cycle metrics
            pid_result: PID correction result (None if not cycle completion)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "metrics": metrics,
            "pid_correction": pid_result,
            "learnings_count": len(self.intelligence.learnings),
            "patterns_count": len(self.intelligence.patterns),
        }

        if not self.dry_run:
            self.evaluation_log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.evaluation_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
            print(f"\n📝 Evaluation logged to {self.evaluation_log}")
        else:
            print("\n🔍 DRY-RUN: Skipping log save")

    def save_intelligence(self) -> None:
        """Save intelligence to file."""
        if not self.dry_run:
            self.intelligence_file.parent.mkdir(parents=True, exist_ok=True)
            self.intelligence.save_to_file(self.intelligence_file)
            print(f"💾 Intelligence saved to {self.intelligence_file}")
        else:
            print("🔍 DRY-RUN: Skipping intelligence save")

    def check_test_opportunity(self) -> dict[str, Any] | None:
        """
        Check if FTP test is recommended based on PID discrete cycle timing.

        Analyzes:
        - Time since last FTP test
        - Current TSB (form)
        - Recent training load
        - Overall condition

        Returns:
            Dict with recommendation details if test is due, None otherwise
        """
        # Get current wellness for TSB
        try:
            wellness_data = self.client.get_wellness(
                date.today().isoformat(), date.today().isoformat()
            )
            if not wellness_data:
                return None

            wellness = wellness_data[0]
            tsb = wellness.get("tsb", 0)
            ctl = wellness.get("ctl", 0)

        except Exception as e:
            print(f"  ⚠️  Could not fetch wellness data: {e}")
            return None

        # Check time since last test (look for high IF activities in past 16 weeks)
        weeks_back = 16
        start_check = date.today() - timedelta(weeks=weeks_back)

        # Get activities to check for test patterns
        try:
            activities = self.client.get_activities(
                start_check.isoformat(), date.today().isoformat()
            )

            # Look for test-like activities (IF > 0.90, duration 40 - 60min)
            test_activities = [
                a
                for a in activities
                if a.get("icu_intensity", 0) > 0.90 and 35 <= a.get("moving_time", 0) / 60 <= 65
            ]

            if test_activities:
                # Find most recent test
                last_test = max(test_activities, key=lambda x: x.get("start_date_local", ""))
                last_test_date_str = last_test.get("start_date_local", "")[:10]
                last_test_date = datetime.strptime(last_test_date_str, "%Y-%m-%d").date()
                weeks_since_test = (date.today() - last_test_date).days / 7
            else:
                weeks_since_test = 16  # No test found, definitely overdue

        except Exception:
            weeks_since_test = 8  # Assume standard cycle if error

        # Decision logic
        test_overdue = weeks_since_test >= 6  # PID discrete: 6 - 8 weeks
        form_ready = tsb >= 5  # Not optimal (+10 - 15 ideal) but acceptable
        form_neutral = -5 <= tsb <= 5
        fitness_adequate = ctl >= 40

        recommendation = None

        if test_overdue and form_ready and fitness_adequate:
            recommendation = {
                "status": "READY",
                "weeks_since_test": weeks_since_test,
                "tsb": tsb,
                "ctl": ctl,
                "message": f"Test FTP recommandé (dernier test: {weeks_since_test:.1f} sem)",
                "timing": "Cette semaine (TSB acceptable)",
            }
        elif test_overdue and form_neutral and fitness_adequate:
            recommendation = {
                "status": "NEEDS_TAPER",
                "weeks_since_test": weeks_since_test,
                "tsb": tsb,
                "ctl": ctl,
                "message": f"Test FTP recommandé avec affûtage (dernier: {weeks_since_test:.1f} sem)",
                "timing": "Semaine prochaine après réduction volume (-40% TSS)",
            }
        elif test_overdue:
            recommendation = {
                "status": "OVERDUE_LOW_FITNESS",
                "weeks_since_test": weeks_since_test,
                "tsb": tsb,
                "ctl": ctl,
                "message": f"Test overdue ({weeks_since_test:.1f} sem) mais condition limitée",
                "timing": "Prévoir après 2 semaines de préparation",
            }

        return recommendation

    def monitor_ctl_progression_vs_peaks(self) -> dict[str, Any] | None:
        """
        Monitor CTL progression vs Peaks Coaching targets (Sprint R10).

        Checks:
        - Current CTL vs minimum/optimal for FTP
        - Weekly CTL progression rate
        - Weeks to reach target CTL
        - Phase recommendation (Peaks algorithm)

        Returns:
            Dict with CTL monitoring results or None if failed
        """
        print(f"\n{'=' * 60}")
        print("📈 CTL Progression Monitoring (Peaks Coaching)")
        print(f"{'=' * 60}")

        try:
            # Get current wellness for CTL
            wellness_data = self.client.get_wellness(
                date.today().isoformat(), date.today().isoformat()
            )
            if not wellness_data:
                print("  ⚠️  No wellness data available")
                return None

            wellness = wellness_data[0]
            ctl_current = wellness.get("ctl", 0)
            atl_current = wellness.get("atl", 0)
            tsb_current = wellness.get("tsb", 0)

            # Load athlete profile from env for FTP and age
            from cyclisme_training_logs.config.athlete_profile import AthleteProfile

            athlete_profile = AthleteProfile.from_env()
            ftp_current = athlete_profile.ftp
            ftp_target = athlete_profile.ftp_target
            athlete_age = athlete_profile.age

            # Calculate Peaks Coaching thresholds
            # FTP 223W → CTL minimum ~55, optimal ~70
            # FTP 230W → CTL minimum ~57, optimal ~73
            ctl_minimum = (ftp_current / 220) * 55
            ctl_optimal = (ftp_current / 220) * 70

            # Calculate CTL progression rate (last 7 days)
            week_ago = date.today() - timedelta(days=7)
            wellness_week_ago = self.client.get_wellness(week_ago.isoformat(), week_ago.isoformat())

            if wellness_week_ago:
                ctl_week_ago = wellness_week_ago[0].get("ctl", ctl_current)
                ctl_weekly_change = ctl_current - ctl_week_ago
            else:
                ctl_weekly_change = 0

            # Estimate weeks to reach targets
            if ctl_weekly_change > 0:
                weeks_to_minimum = max(0, (ctl_minimum - ctl_current) / ctl_weekly_change)
                weeks_to_optimal = max(0, (ctl_optimal - ctl_current) / ctl_weekly_change)
            else:
                weeks_to_minimum = float("inf")
                weeks_to_optimal = float("inf")

            # Determine status
            if ctl_current < 50:
                status = "CRITICAL"
                status_emoji = "🚨"
                message = "CTL critique < 50 - Reconstruction base urgente"
            elif ctl_current < ctl_minimum:
                status = "LOW"
                status_emoji = "⚠️"
                message = f"CTL sous minimum Peaks ({ctl_minimum:.0f})"
            elif ctl_current < (ctl_optimal * 0.85):
                status = "SUBOPTIMAL"
                status_emoji = "📊"
                message = f"CTL sous-optimal (< 85% de {ctl_optimal:.0f})"
            else:
                status = "OPTIMAL"
                status_emoji = "✅"
                message = "CTL dans la zone optimale Peaks"

            print(f"\n{status_emoji} Status: {status}")
            print(f"   {message}")
            print("\n📊 Métriques Actuelles:")
            print(f"   CTL: {ctl_current:.1f}")
            print(f"   ATL: {atl_current:.1f}")
            print(f"   TSB: {tsb_current:+.1f}")
            print(f"   FTP: {ftp_current}W")
            print(f"\n🎯 Seuils Peaks (FTP {ftp_current}W):")
            print(f"   CTL minimum: {ctl_minimum:.0f}")
            print(f"   CTL optimal: {ctl_optimal:.0f}")
            print("\n📈 Progression:")
            print(f"   Changement 7 jours: {ctl_weekly_change:+.1f} points")

            if weeks_to_minimum < float("inf"):
                print(f"   Semaines → minimum: {weeks_to_minimum:.1f} semaines")
            if weeks_to_optimal < float("inf"):
                print(f"   Semaines → optimal: {weeks_to_optimal:.1f} semaines")

            # Determine Peaks phase (using loaded athlete profile)
            from cyclisme_training_logs.planning.peaks_phases import determine_training_phase

            phase_rec = determine_training_phase(
                ctl_current=ctl_current,
                ftp_current=ftp_current,
                ftp_target=ftp_target,
                athlete_age=athlete_age,
            )

            print(f"\n🎯 Phase Peaks Coaching: {phase_rec.phase.value.upper()}")
            print(f"   TSS recommandé: {phase_rec.weekly_tss_load} TSS/semaine (charge)")
            print(f"   TSS recovery: {phase_rec.weekly_tss_recovery} TSS/semaine")

            # Recommendations
            recommendations = []
            if status == "CRITICAL":
                recommendations.append("🚨 PEAKS OVERRIDE actif (CTL < 50)")
                recommendations.append("Focus Tempo (35%) + Sweet-Spot (20%)")
                recommendations.append(f"Target: {phase_rec.weekly_tss_load} TSS/semaine")
            elif status == "LOW":
                recommendations.append("Reconstruction base progressive")
                recommendations.append(f"Maintenir {phase_rec.weekly_tss_load} TSS/semaine")
                recommendations.append(f"CTL target: {ctl_minimum:.0f} minimum")
            elif status == "SUBOPTIMAL":
                recommendations.append("PID peut devenir actif si CTL ≥ 50")
                recommendations.append("Continuer progression régulière")
            else:
                recommendations.append("Maintenir CTL à 90% du maximum (Masters 50+)")
                recommendations.append("PID autonome recommandé")

            if recommendations:
                print("\n💡 Recommandations:")
                for rec in recommendations:
                    print(f"   • {rec}")

            return {
                "ctl_current": ctl_current,
                "atl_current": atl_current,
                "tsb_current": tsb_current,
                "ftp_current": ftp_current,
                "ctl_minimum": ctl_minimum,
                "ctl_optimal": ctl_optimal,
                "ctl_weekly_change": ctl_weekly_change,
                "weeks_to_minimum": weeks_to_minimum if weeks_to_minimum < float("inf") else None,
                "weeks_to_optimal": weeks_to_optimal if weeks_to_optimal < float("inf") else None,
                "status": status,
                "message": message,
                "phase": phase_rec.phase.value,
                "weekly_tss_recommended": phase_rec.weekly_tss_load,
                "recommendations": recommendations,
            }

        except Exception as e:
            print(f"  ❌ Erreur monitoring CTL: {e}")
            import traceback

            traceback.print_exc()
            return None

    def run_daily_evaluation(self, days_back: int = 7) -> dict[str, Any]:
        """
        Run daily evaluation (collect + learn, no PID).

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

        # NEW Sprint R10: Monitor CTL progression vs Peaks targets
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
                    justification=f"Cycle PID dépassé ({weeks:.1f} > 6 - 8 sem), condition prête",
                    evidence=evidence,
                )
            elif status == "NEEDS_TAPER":
                adaptation = self.intelligence.propose_adaptation(
                    protocol_name="ftp_test_cycle",
                    adaptation_type="ADD",
                    current_rule=f"Dernier test: {weeks:.1f} semaines",
                    proposed_rule="Semaine affûtage puis tests FTP (TSS -40%)",
                    justification=f"Cycle PID dépassé ({weeks:.1f} > 6 - 8 sem), TSB insuffisant",
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

        print(f"\n{'=' * 70}")
        print("✨ Daily Evaluation Complete")
        print(f"{'=' * 70}")
        print(f"   Learnings: {len(self.intelligence.learnings)}")
        print(f"   Patterns: {len(self.intelligence.patterns)}")
        print(f"   Adaptations: {len(self.intelligence.adaptations)}")

        # Sprint R10: Display CTL status summary
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
            "ctl_monitoring": ctl_monitoring,  # NEW Sprint R10
        }

    def run_cycle_evaluation(
        self,
        measured_ftp: float,
        cycle_duration_weeks: int = 6,
    ) -> dict[str, Any]:
        """
        Run cycle completion evaluation (full PID).

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
        sys.exit(1)

    # Create evaluator
    evaluator = PIDDailyEvaluator(dry_run=args.dry_run)

    # Run evaluation
    try:
        if args.cycle_complete:
            result = evaluator.run_cycle_evaluation(
                measured_ftp=args.measured_ftp,
                cycle_duration_weeks=args.cycle_weeks,
            )
        else:
            result = evaluator.run_daily_evaluation(days_back=args.days_back)

        if result["status"] == "SUCCESS":
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
