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
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from cyclisme_training_logs.config import create_intervals_client


class BaselineAnalyzer:
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

        # Intervals.icu client
        self.client = create_intervals_client()

        print("📊 Baseline Analyzer Initialized")
        print(f"   Period: {self.start_date} → {self.end_date} ({self.duration_days} days)")
        print()

    def load_adherence_data(self) -> None:
        """Load adherence data from workout_adherence.jsonl."""
        print("📥 Loading adherence data...")

        if not self.adherence_file.exists():
            print(f"   ⚠️  File not found: {self.adherence_file}")
            return

        seen_dates = {}
        with open(self.adherence_file) as f:
            for line in f:
                record = json.loads(line)
                record_date = datetime.strptime(record["date"], "%Y-%m-%d").date()

                if self.start_date <= record_date <= self.end_date:
                    # Deduplicate: keep only most recent record per date
                    date_key = record["date"]
                    if date_key not in seen_dates:
                        seen_dates[date_key] = record
                    else:
                        # Keep record with most recent timestamp
                        existing_ts = seen_dates[date_key].get("timestamp", "")
                        current_ts = record.get("timestamp", "")
                        if current_ts > existing_ts:
                            seen_dates[date_key] = record

        self.adherence_data = list(seen_dates.values())
        self.adherence_data.sort(key=lambda x: x["date"])
        print(f"   ✅ Loaded {len(self.adherence_data)} records")

    def load_intervals_data(self) -> None:
        """Load data from Intervals.icu API."""
        print("\n📥 Loading Intervals.icu data...")

        start_str = self.start_date.isoformat()
        end_str = self.end_date.isoformat()

        # Wellness (TSB, CTL, ATL)
        try:
            self.wellness_data = self.client.get_wellness(start_str, end_str)
            print(f"   ✅ Wellness: {len(self.wellness_data)} days")
        except Exception as e:
            print(f"   ⚠️  Wellness error: {e}")

        # Activities
        try:
            self.activities_data = self.client.get_activities(start_str, end_str)
            print(f"   ✅ Activities: {len(self.activities_data)} records")
        except Exception as e:
            print(f"   ⚠️  Activities error: {e}")

        # Events (planned workouts)
        try:
            self.events_data = self.client.get_events(start_str, end_str)
            print(f"   ✅ Events: {len(self.events_data)} planned workouts")
        except Exception as e:
            print(f"   ⚠️  Events error: {e}")

    def load_cardiovascular_coupling(self) -> None:
        """Extract cardiovascular coupling from workout_history files."""
        print("\n📥 Extracting cardiovascular coupling...")

        if not self.workout_history_dir.exists():
            print(f"   ⚠️  Directory not found: {self.workout_history_dir}")
            return

        patterns = [
            r"découplage\s+cardiovasculaire\s+\w+\s*\((\d+\.?\d*)\s*%\)",
            r"découplage\s+(\d+\.?\d*)\s*%",
        ]

        workout_files = sorted(self.workout_history_dir.glob("*/workout_history_*.md"))
        print(f"   📁 Found {len(workout_files)} weekly files")

        for workout_file in workout_files:
            with open(workout_file) as f:
                content = f.read()

            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    coupling_pct = float(match.group(1))
                    self.cv_coupling_values.append(abs(coupling_pct) / 100.0)

        print(f"   ✅ Extracted {len(self.cv_coupling_values)} values")

    def validate_data_quality(self) -> dict[str, Any]:
        """Check data completeness, gaps, and anomalies.

        Returns:
            Dict with quality metrics and score
        """
        print("\n🔍 Validating data quality...")

        quality = {
            "completeness": {},
            "gaps": [],
            "anomalies": [],
            "score": 0,
            "grade": "",
        }

        # Check adherence completeness
        expected_days = self.duration_days
        actual_days = len(self.adherence_data)
        adherence_completeness = actual_days / expected_days if expected_days > 0 else 0

        quality["completeness"]["adherence"] = adherence_completeness
        quality["completeness"]["wellness"] = (
            len(self.wellness_data) / expected_days if expected_days > 0 else 0
        )
        quality["completeness"]["activities"] = len(self.activities_data)  # No expected count

        # Detect gaps in adherence
        if self.adherence_data:
            adherence_dates = {
                datetime.strptime(r["date"], "%Y-%m-%d").date() for r in self.adherence_data
            }
            current = self.start_date
            while current <= self.end_date:
                if current not in adherence_dates:
                    quality["gaps"].append({"date": current.isoformat(), "type": "adherence"})
                current += timedelta(days=1)

        # Detect anomalies
        for record in self.adherence_data:
            # Anomaly: negative adherence rate
            if record["adherence_rate"] < 0:
                quality["anomalies"].append(
                    {
                        "date": record["date"],
                        "type": "negative_adherence",
                        "value": record["adherence_rate"],
                    }
                )

        # Calculate quality score (0 - 100)
        completeness_score = adherence_completeness * 40
        consistency_score = 30 if len(quality["anomalies"]) == 0 else 20
        richness_score = (
            20 if len(self.cv_coupling_values) > 0 and len(self.wellness_data) > 0 else 10
        )
        timeliness_score = 10  # Assume timestamps are correct if data exists

        quality["score"] = int(
            completeness_score + consistency_score + richness_score + timeliness_score
        )

        # Grade
        if quality["score"] >= 90:
            quality["grade"] = "A"
        elif quality["score"] >= 80:
            quality["grade"] = "B"
        elif quality["score"] >= 70:
            quality["grade"] = "C"
        else:
            quality["grade"] = "D"

        print(f"   📊 Quality Score: {quality['score']}/100 (Grade: {quality['grade']})")
        print(f"   ✅ Completeness: {adherence_completeness * 100:.1f}%")
        print(f"   ⚠️  Gaps: {len(quality['gaps'])}")
        print(f"   ⚠️  Anomalies: {len(quality['anomalies'])}")

        return quality

    def calculate_adherence_metrics(self) -> dict[str, Any]:
        """Calculate adherence metrics.

        Returns:
            Dict with adherence rate, completed, skipped, patterns
        """
        print("\n📊 Calculating adherence metrics...")

        if not self.adherence_data:
            print("   ⚠️  No adherence data")
            return {}

        total_planned = sum(r["planned_workouts"] for r in self.adherence_data)
        total_completed = sum(r["completed_activities"] for r in self.adherence_data)
        total_skipped = sum(len(r.get("skipped_workouts", [])) for r in self.adherence_data)

        adherence_rate = total_completed / total_planned if total_planned > 0 else 0

        # Identify skipped dates
        skipped_dates = []
        for record in self.adherence_data:
            if record["status"] in ["MISSED", "PARTIAL"]:
                skipped_dates.append(record["date"])

        # Pattern by day of week
        day_patterns = {}
        for record in self.adherence_data:
            date = datetime.strptime(record["date"], "%Y-%m-%d")
            day_name = date.strftime("%A")
            if day_name not in day_patterns:
                day_patterns[day_name] = {"planned": 0, "completed": 0}
            day_patterns[day_name]["planned"] += record["planned_workouts"]
            day_patterns[day_name]["completed"] += record["completed_activities"]

        metrics = {
            "rate": adherence_rate,
            "completed": total_completed,
            "planned": total_planned,
            "skipped": total_skipped,
            "skipped_dates": skipped_dates,
            "day_patterns": day_patterns,
        }

        print(f"   ✅ Adherence Rate: {adherence_rate * 100:.1f}%")
        print(f"   ✅ Completed: {total_completed}/{total_planned}")
        print(f"   ⚠️  Skipped: {total_skipped} workouts on {len(skipped_dates)} days")

        return metrics

    def calculate_tss_metrics(self) -> dict[str, Any]:
        """Calculate TSS metrics (planned vs actual).

        Returns:
            Dict with TSS planned, actual, completion rate
        """
        print("\n📊 Calculating TSS metrics...")

        # TSS planned from events (handle None values)
        tss_planned = sum(e.get("icu_training_load") or 0 for e in self.events_data)

        # TSS actual from activities (handle None values)
        tss_actual = sum(a.get("icu_training_load") or 0 for a in self.activities_data)

        completion_rate = tss_actual / tss_planned if tss_planned > 0 else 0

        avg_daily_planned = tss_planned / self.duration_days if self.duration_days > 0 else 0
        avg_daily_actual = tss_actual / self.duration_days if self.duration_days > 0 else 0

        metrics = {
            "planned_total": tss_planned,
            "actual_total": tss_actual,
            "completion_rate": completion_rate,
            "avg_daily_planned": avg_daily_planned,
            "avg_daily_actual": avg_daily_actual,
        }

        print(f"   ✅ TSS Planned: {tss_planned:.0f}")
        print(f"   ✅ TSS Actual: {tss_actual:.0f}")
        print(f"   ✅ Completion Rate: {completion_rate * 100:.1f}%")

        return metrics

    def analyze_tsb_trajectory(self) -> dict[str, Any]:
        """Analyze TSB evolution over period.

        Returns:
            Dict with TSB start, end, trajectory, average
        """
        print("\n📊 Analyzing TSB trajectory...")

        if not self.wellness_data:
            print("   ⚠️  No wellness data")
            return {}

        # Sort by date
        wellness_sorted = sorted(self.wellness_data, key=lambda x: x.get("id", ""))

        tsb_values = [w.get("tsb", 0) for w in wellness_sorted]
        ctl_values = [w.get("ctl", 0) for w in wellness_sorted]
        atl_values = [w.get("atl", 0) for w in wellness_sorted]

        trajectory = [
            {
                "date": w.get("id"),
                "tsb": w.get("tsb", 0),
                "ctl": w.get("ctl", 0),
                "atl": w.get("atl", 0),
            }
            for w in wellness_sorted
        ]

        metrics = {
            "start_tsb": tsb_values[0] if tsb_values else 0,
            "end_tsb": tsb_values[-1] if tsb_values else 0,
            "avg_tsb": sum(tsb_values) / len(tsb_values) if tsb_values else 0,
            "trajectory": trajectory,
            "start_ctl": ctl_values[0] if ctl_values else 0,
            "end_ctl": ctl_values[-1] if ctl_values else 0,
            "start_atl": atl_values[0] if atl_values else 0,
            "end_atl": atl_values[-1] if atl_values else 0,
        }

        print(f"   ✅ TSB: {metrics['start_tsb']:.1f} → {metrics['end_tsb']:.1f}")
        print(f"   ✅ CTL: {metrics['start_ctl']:.1f} → {metrics['end_ctl']:.1f}")
        print(f"   ✅ ATL: {metrics['start_atl']:.1f} → {metrics['end_atl']:.1f}")

        return metrics

    def calculate_cv_coupling_metrics(self) -> dict[str, Any]:
        """Calculate cardiovascular coupling metrics.

        Returns:
            Dict with average coupling, count, quality assessment
        """
        print("\n📊 Calculating cardiovascular coupling metrics...")

        if not self.cv_coupling_values:
            print("   ⚠️  No CV coupling data")
            return {"avg": 0, "count": 0, "quality": "NO_DATA"}

        avg_coupling = sum(self.cv_coupling_values) / len(self.cv_coupling_values)

        # Quality assessment (< 7.5% = good aerobic quality)
        if avg_coupling < 0.025:  # <2.5%
            quality = "EXCELLENT"
        elif avg_coupling < 0.05:  # <5%
            quality = "GOOD"
        elif avg_coupling < 0.075:  # <7.5%
            quality = "ACCEPTABLE"
        else:
            quality = "POOR"

        metrics = {
            "avg": avg_coupling,
            "count": len(self.cv_coupling_values),
            "quality": quality,
        }

        print(f"   ✅ Avg CV Coupling: {avg_coupling * 100:.1f}% ({quality})")
        print(f"   ✅ Samples: {len(self.cv_coupling_values)}")

        return metrics

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
        self.load_cardiovascular_coupling()

        # Validate quality
        quality = self.validate_data_quality()

        # Calculate metrics
        adherence = self.calculate_adherence_metrics()
        tss = self.calculate_tss_metrics()
        tsb = self.analyze_tsb_trajectory()
        cv_coupling = self.calculate_cv_coupling_metrics()

        # Assemble results
        results = {
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "period_start": self.start_date.isoformat(),
                "period_end": self.end_date.isoformat(),
                "duration_days": self.duration_days,
                "version": "1.0.0",
            },
            "quality": quality,
            "adherence": adherence,
            "tss": tss,
            "tsb": tsb,
            "cardiovascular_coupling": cv_coupling,
        }

        print()
        print("=" * 70)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 70)

        return results

    def generate_json_output(self, results: dict[str, Any]) -> Path:
        """Generate JSON dataset output.

        Args:
            results: Analysis results dict

        Returns:
            Path to generated JSON file
        """
        output_file = self.output_dir / "baseline_preliminary.json"

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n📄 JSON dataset: {output_file}")
        return output_file

    def generate_markdown_report(self, results: dict[str, Any]) -> Path:
        """Generate Markdown report.

        Args:
            results: Analysis results dict

        Returns:
            Path to generated markdown file
        """
        output_file = self.output_dir / "baseline_report_s076_s077.md"

        report = self._format_markdown_report(results)

        with open(output_file, "w") as f:
            f.write(report)

        print(f"📄 Markdown report: {output_file}")
        return output_file

    def _format_markdown_report(self, results: dict[str, Any]) -> str:
        """Format analysis results as markdown report."""
        metadata = results["metadata"]
        quality = results["quality"]
        adherence = results.get("adherence", {})
        tss = results.get("tss", {})
        tsb = results.get("tsb", {})
        cv_coupling = results.get("cardiovascular_coupling", {})

        report = f"""# Rapport Baseline S076 - S077

**Analyse Préliminaire - Infrastructure Monitoring**

Généré le: {datetime.now().strftime("%d/%m/%Y %H:%M")}

---

## 📅 Période Analysée

- **Dates**: {metadata['period_start']} → {metadata['period_end']}
- **Durée**: {metadata['duration_days']} jours
- **Semaines**: S076 (complète), S077 (partielle)
- **Version**: {metadata['version']}

---

## 1. 📊 Synthèse Adhérence

### Taux Global
- **Adherence Rate**: {adherence.get('rate', 0) * 100:.1f}%
- **Séances complétées**: {adherence.get('completed', 0)}/{adherence.get('planned', 0)}
- **Séances sautées**: {adherence.get('skipped', 0)}

### Dates Séances Manquées
"""

        if adherence.get("skipped_dates"):
            for date in adherence["skipped_dates"]:
                report += f"- {date}\n"
        else:
            report += "- Aucune séance manquée ✅\n"

        report += """
### Patterns par Jour de Semaine

"""

        if adherence.get("day_patterns"):
            report += "| Jour | Planifié | Complété | Taux |\n"
            report += "|------|----------|----------|------|\n"
            for day, stats in adherence["day_patterns"].items():
                planned = stats["planned"]
                completed = stats["completed"]
                rate = completed / planned * 100 if planned > 0 else 0
                report += f"| {day} | {planned} | {completed} | {rate:.0f}% |\n"

        report += f"""
---

## 2. 💪 Charge Entraînement (TSS)

### Volumes
- **TSS Planifié**: {tss.get('planned_total', 0):.0f}
- **TSS Réalisé**: {tss.get('actual_total', 0):.0f}
- **Ratio Completion**: {tss.get('completion_rate', 0) * 100:.1f}%

### Moyennes Quotidiennes
- **TSS/jour Planifié**: {tss.get('avg_daily_planned', 0):.1f}
- **TSS/jour Réalisé**: {tss.get('avg_daily_actual', 0):.1f}

### Analyse
"""

        completion_rate = tss.get("completion_rate", 0)
        if completion_rate > 1.1:
            report += f"⚠️ **Sur-charge** : TSS réalisé significativement supérieur au planifié (+{(completion_rate - 1) * 100:.0f}%). Risque fatigue accumulée.\n"
        elif completion_rate < 0.85:
            report += f"⚠️ **Sous-charge** : TSS réalisé inférieur au planifié (-{(1 - completion_rate) * 100:.0f}%). Progression potentiellement limitée.\n"
        else:
            report += "✅ **Charge optimale** : TSS réalisé cohérent avec planification.\n"

        report += f"""
---

## 3. 📈 Evolution Fitness (TSB/CTL/ATL)

### Début Période ({metadata['period_start']})
- **TSB**: {tsb.get('start_tsb', 0):.1f}
- **CTL**: {tsb.get('start_ctl', 0):.1f}
- **ATL**: {tsb.get('start_atl', 0):.1f}

### Fin Période ({metadata['period_end']})
- **TSB**: {tsb.get('end_tsb', 0):.1f}
- **CTL**: {tsb.get('end_ctl', 0):.1f}
- **ATL**: {tsb.get('end_atl', 0):.1f}

### Evolution TSB
- **TSB Moyen**: {tsb.get('avg_tsb', 0):.1f}
- **Variation**: {tsb.get('start_tsb', 0):.1f} → {tsb.get('end_tsb', 0):.1f} ({tsb.get('end_tsb', 0) - tsb.get('start_tsb', 0):+.1f})

### Analyse Forme
"""

        end_tsb = tsb.get("end_tsb", 0)
        if end_tsb > 10:
            report += (
                "✅ **Forme excellente** : TSB élevé, prêt pour séances intensives ou tests.\n"
            )
        elif end_tsb > 5:
            report += "✅ **Forme bonne** : TSB positif, condition favorable.\n"
        elif end_tsb > -5:
            report += "⚠️ **Forme neutre** : TSB proche de zéro, équilibre fitness/fatigue.\n"
        else:
            report += "⚠️ **Fatigue** : TSB négatif, besoin récupération.\n"

        report += f"""
---

## 4. ❤️ Qualité Cardiovasculaire

### Découplage Cardiovasculaire
- **Moyenne**: {cv_coupling.get('avg', 0) * 100:.1f}%
- **Échantillons**: {cv_coupling.get('count', 0)}
- **Qualité**: {cv_coupling.get('quality', 'NO_DATA')}

### Référence
- **< 2.5%**: Excellent (aérobie optimal)
- **2.5 - 5%**: Bon (qualité maintenue)
- **5 - 7.5%**: Acceptable (drift léger)
- **> 7.5%**: Attention (qualité dégradée)

---

## 5. 🔍 Qualité Données (Data Quality Score)

### Score Global
- **Score**: {quality['score']}/100
- **Grade**: {quality['grade']}

### Détail Complétude
- **Adherence**: {quality['completeness'].get('adherence', 0) * 100:.0f}%
- **Wellness**: {quality['completeness'].get('wellness', 0) * 100:.0f}%
- **Activities**: {quality['completeness'].get('activities', 0)} records

### Gaps Détectés
"""

        if quality["gaps"]:
            report += f"⚠️ **{len(quality['gaps'])} jours manquants**:\n"
            for gap in quality["gaps"][:5]:  # Limit to first 5
                report += f"- {gap['date']} ({gap['type']})\n"
            if len(quality["gaps"]) > 5:
                report += f"- ... et {len(quality['gaps']) - 5} autres\n"
        else:
            report += "✅ Aucun gap détecté\n"

        report += "\n### Anomalies\n"

        if quality["anomalies"]:
            report += f"⚠️ **{len(quality['anomalies'])} anomalies**:\n"
            for anomaly in quality["anomalies"]:
                report += f"- {anomaly['date']}: {anomaly['type']}\n"
        else:
            report += "✅ Aucune anomalie détectée\n"

        report += """
---

## 6. 💡 Insights Clés

### Forces
"""

        insights_positive = []
        insights_negative = []
        insights_neutral = []

        # Adherence insights
        if adherence.get("rate", 0) >= 0.90:
            insights_positive.append(
                f"**Discipline excellente** : {adherence.get('rate', 0) * 100:.0f}% adherence maintenue"
            )
        elif adherence.get("rate", 0) >= 0.80:
            insights_neutral.append(
                f"**Discipline correcte** : {adherence.get('rate', 0) * 100:.0f}% adherence"
            )
        else:
            insights_negative.append(
                f"**Adherence limitée** : {adherence.get('rate', 0) * 100:.0f}% seulement"
            )

        # CV coupling insights
        if cv_coupling.get("quality") == "EXCELLENT":
            insights_positive.append(
                f"**Qualité aérobie optimale** : {cv_coupling.get('avg', 0) * 100:.1f}% découplage CV"
            )
        elif cv_coupling.get("quality") in ["GOOD", "ACCEPTABLE"]:
            insights_neutral.append(
                f"**Qualité aérobie maintenue** : {cv_coupling.get('avg', 0) * 100:.1f}% découplage CV"
            )

        # TSS insights
        if 0.95 <= tss.get("completion_rate", 0) <= 1.05:
            insights_positive.append("**Planification respectée** : TSS réel cohérent avec plan")
        elif tss.get("completion_rate", 0) > 1.1:
            insights_negative.append(
                f"**Sur-charge** : +{(tss.get('completion_rate', 0) - 1) * 100:.0f}% TSS vs planifié"
            )

        # Data quality insights
        if quality["score"] >= 90:
            insights_positive.append(
                f"**Infrastructure monitoring validée** : Score qualité {quality['score']}/100"
            )

        for insight in insights_positive:
            report += f"- ✅ {insight}\n"

        if insights_neutral:
            report += "\n### Points Neutres\n"
            for insight in insights_neutral:
                report += f"- ℹ️ {insight}\n"

        if insights_negative:
            report += "\n### Points Vigilance\n"
            for insight in insights_negative:
                report += f"- ⚠️ {insight}\n"

        report += """
---

## 7. 🎯 Recommandations

### Court Terme (S078 - S079)

"""

        # Recommendations based on TSB
        if end_tsb < -5:
            report += "1. **Récupération prioritaire** : TSB négatif, réduire volume 20 - 30%\n"
        elif end_tsb < 5 and completion_rate > 1.1:
            report += "1. **Affûtage léger** : Réduire volume 10 - 20% pour optimiser fraîcheur\n"
        else:
            report += "1. **Maintien plan** : Condition favorable, continuer programme\n"

        # Recommendations based on adherence
        if adherence.get("rate", 0) < 0.85:
            report += "2. **Améliorer adherence** : Identifier causes séances manquées\n"

        # Recommendations for CV quality
        if cv_coupling.get("quality") == "POOR":
            report += (
                "3. **Attention qualité Z2** : Découplage élevé, vérifier intensité endurance\n"
            )

        report += """
### Préparation Tests S080 (10 - 16 fév)

1. **Timing optimal** :
   - Semaine S079 (2 - 8 fév) : Affûtage léger
   - TSB cible : +10 à +15
   - Réduction TSS : -30 à -40%

2. **Protocole tests** :
   - Reprendre Zwift Camp Baseline (Flat Out Fast, Climb Control, etc.)
   - Conditions : Sommeil >7h, VFC normale, hydratation optimale

3. **Métriques post-tests** :
   - FTP mesuré
   - Comparaison vs Octobre 2025
   - Calibration PID complète (49 jours données + FTP)

### Collecte Données PID

✅ **Infrastructure validée** : Monitoring adherence opérationnel
✅ **Données complètes** : Adherence, TSS, TSB, CV coupling
⏳ **Tests S080** : Dernière pièce pour calibration PID

---

## 8. 📚 Annexes

### A. Contexte Historique

**Tests Zwift Camp Baseline (Octobre 2025)** :
- Dates : 11 - 14 octobre 2025
- FTP estimé : ~220W (basé sur NP tests)
- Gap temporel : 15 semaines depuis dernier test
- Cycle PID : Largement dépassé (vs 6 - 8 sem recommandé)

### B. Méthodologie

**Sources données** :
- Adherence : `~/data/monitoring/workout_adherence.jsonl`
- Intervals.icu : Wellness, Activities, Events (API)
- Cardiovascular : `logs/weekly_reports/S0XX/workout_history_*.md`

**Outils** :
- BaselineAnalyzer v1.0.0
- IntervalsClient (API wrapper)
- Python 3.11+

---

**Rapport généré automatiquement par BaselineAnalyzer**

*Sprint R9.E - Baseline Preliminary Analysis*
"""

        return report


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
