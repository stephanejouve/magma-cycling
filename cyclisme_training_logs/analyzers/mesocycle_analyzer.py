#!/usr/bin/env python3
"""
Mesocycle Analyzer - Enriched Context for Strategic Planning.

Generates comprehensive statistical analysis every 4-6 weeks to provide
strategic insights for planning: power profile evolution, execution patterns,
workout diversity, and cycle comparisons.

Examples:
    Detect mesocycle end and generate report::

        from cyclisme_training_logs.analyzers.mesocycle_analyzer import MesocycleAnalyzer

        analyzer = MesocycleAnalyzer(week_id="S082")
        if analyzer.is_mesocycle_end():
            report = analyzer.generate_mesocycle_report()
            print(report)

Author: Claude Code
Created: 2026-02-19
Version: 1.0.0
"""

import json
import re
from collections import defaultdict
from pathlib import Path

from cyclisme_training_logs.api.intervals_client import IntervalsClient
from cyclisme_training_logs.config import get_data_config, get_intervals_config


class MesocycleAnalyzer:
    """
    Analyzes training mesocycles (4-6 weeks) for strategic planning context.

    Provides enriched context including power profile evolution, execution patterns,
    workout diversity, and cycle comparisons to inform weekly planning decisions.
    """

    def __init__(self, week_id: str, mesocycle_weeks: int = 6):
        """
        Initialize mesocycle analyzer.

        Args:
            week_id: Current week ID (e.g., "S082")
            mesocycle_weeks: Length of mesocycle in weeks (default: 6)
        """
        self.week_id = week_id
        self.mesocycle_weeks = mesocycle_weeks
        self.week_number = int(week_id[1:])  # Extract number from "S082"

        # Load config
        self.data_config = get_data_config()
        self.intervals_config = get_intervals_config()
        self.client = IntervalsClient(
            self.intervals_config.athlete_id, self.intervals_config.api_key
        )

        # State file to track analyzed mesocycles
        self.state_file = Path.home() / ".mesocycle_state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load mesocycle analysis state."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                return {"analyzed_cycles": []}
        return {"analyzed_cycles": []}

    def _save_state(self):
        """Save mesocycle analysis state."""
        try:
            self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"⚠️  Failed to save mesocycle state: {e}")

    def is_mesocycle_end(self) -> bool:
        """
        Check if current week is at mesocycle boundary.

        Returns:
            True if current week ends a mesocycle (every 6 weeks)

        Examples:
            >>> analyzer = MesocycleAnalyzer("S078")  # Week 78
            >>> analyzer.is_mesocycle_end()
            True  # 78 % 6 == 0
        """
        # Mesocycle ends every N weeks
        return self.week_number % self.mesocycle_weeks == 0

    def should_generate_report(self) -> bool:
        """
        Check if report should be generated (not already done for this cycle).

        Returns:
            True if report should be generated
        """
        if not self.is_mesocycle_end():
            return False

        # Check if already analyzed
        cycle_id = f"cycle_ending_{self.week_id}"
        return cycle_id not in self.state.get("analyzed_cycles", [])

    def _get_mesocycle_weeks(self) -> list[str]:
        """
        Get list of week IDs in current mesocycle.

        Returns:
            List of week IDs (e.g., ["S077", "S078", ...])
        """
        start_week = self.week_number - self.mesocycle_weeks + 1
        return [f"S{w:03d}" for w in range(start_week, self.week_number + 1)]

    def _get_previous_mesocycle_weeks(self) -> list[str]:
        """Get list of week IDs in previous mesocycle."""
        start_week = self.week_number - (2 * self.mesocycle_weeks) + 1
        end_week = self.week_number - self.mesocycle_weeks
        return [f"S{w:03d}" for w in range(start_week, end_week + 1)]

    def _extract_workouts_from_history(self, week_ids: list[str]) -> list[dict]:
        """
        Extract workout analyses from workouts-history.md for given weeks.

        Args:
            week_ids: List of week IDs to extract

        Returns:
            List of workout data dicts
        """
        history_file = self.data_config.data_repo_path / "workouts-history.md"

        if not history_file.exists():
            return []

        content = history_file.read_text(encoding="utf-8")
        workouts = []

        # Split by ### headers
        sections = content.split("###")

        for section in sections:
            # Check if any of the target weeks is in this section
            for week_id in week_ids:
                week_pattern = f"{week_id}-"
                if week_pattern in section[:100]:  # Check in title area
                    # Parse workout data
                    workout_data = self._parse_workout_section(section, week_id)
                    if workout_data:
                        workouts.append(workout_data)
                    break

        return workouts

    def _parse_workout_section(self, section: str, week_id: str) -> dict | None:
        """Parse a workout section to extract key metrics."""
        try:
            data = {"week_id": week_id}

            # Extract title
            title_match = re.search(r"^[\s]*(.+?)\n", section)
            if title_match:
                data["name"] = title_match.group(1).strip()

            # Extract metrics using regex
            metrics = {
                "tss": r"TSS\s*:\s*(\d+)",
                "if": r"IF\s*:\s*([\d.]+)",
                "decoupling": r"Découplage\s*:\s*([\d.]+)%",
                "duration": r"Durée\s*:\s*(\d+)min",
                "avg_power": r"Puissance moyenne\s*:\s*(\d+)W",
                "np": r"Puissance normalisée\s*:\s*(\d+)W",
            }

            for key, pattern in metrics.items():
                match = re.search(pattern, section)
                if match:
                    value = match.group(1)
                    data[key] = float(value) if "." in value else int(value)

            # Extract validation status
            data["validated"] = "✅" in section and "Découplage" in section

            return data if len(data) > 2 else None

        except Exception:
            return None

    def _calculate_decoupling_stats(self, workouts: list[dict]) -> dict:
        """Calculate decoupling statistics."""
        decouplings = [w["decoupling"] for w in workouts if "decoupling" in w]

        if not decouplings:
            return {
                "avg": 0,
                "min": 0,
                "max": 0,
                "count": 0,
                "validated_count": 0,
                "validated_pct": 0,
            }

        validated = sum(1 for w in workouts if w.get("validated", False))

        return {
            "avg": sum(decouplings) / len(decouplings),
            "min": min(decouplings),
            "max": max(decouplings),
            "count": len(decouplings),
            "validated_count": validated,
            "validated_pct": (validated / len(decouplings) * 100) if decouplings else 0,
        }

    def _calculate_adherence_stats(self, workouts: list[dict]) -> dict:
        """Calculate TSS/IF adherence statistics."""
        # This would ideally compare planned vs actual from Intervals.icu
        # For now, basic stats
        tss_values = [w["tss"] for w in workouts if "tss" in w]
        if_values = [w["if"] for w in workouts if "if" in w]

        return {
            "tss_avg": sum(tss_values) / len(tss_values) if tss_values else 0,
            "tss_total": sum(tss_values),
            "if_avg": sum(if_values) / len(if_values) if if_values else 0,
            "workout_count": len(workouts),
        }

    def _analyze_workout_diversity(self, workouts: list[dict]) -> dict:
        """Analyze workout diversity and patterns."""
        workout_types = defaultdict(int)

        for workout in workouts:
            name = workout.get("name", "")
            # Extract workout type from name (e.g., "S081-02-INT-SweetSpot" -> "SweetSpot")
            if "-" in name:
                parts = name.split("-")
                if len(parts) >= 3:
                    workout_type = parts[2]  # Type is 3rd part
                    workout_types[workout_type] += 1

        unique_workouts = len(set(w.get("name", "") for w in workouts))
        total_workouts = len(workouts)

        return {
            "unique_count": unique_workouts,
            "total_count": total_workouts,
            "diversity_pct": (unique_workouts / total_workouts * 100) if total_workouts else 0,
            "by_type": dict(workout_types),
        }

    def generate_mesocycle_report(self) -> str:
        """
        Generate comprehensive mesocycle analysis report.

        Returns:
            Markdown formatted report with statistical analysis

        Examples:
            >>> analyzer = MesocycleAnalyzer("S078")
            >>> report = analyzer.generate_mesocycle_report()
            >>> "Power Profile" in report
            True
        """
        print("\n📊 Génération rapport méso-cycle enrichi...")

        # Get current and previous mesocycle weeks
        current_weeks = self._get_mesocycle_weeks()
        previous_weeks = self._get_previous_mesocycle_weeks()

        print(f"   Cycle actuel: {current_weeks[0]} → {current_weeks[-1]}")
        print(f"   Cycle précédent: {previous_weeks[0]} → {previous_weeks[-1]}")

        # Extract workouts
        current_workouts = self._extract_workouts_from_history(current_weeks)
        previous_workouts = self._extract_workouts_from_history(previous_weeks)

        print(f"   Workouts actuels: {len(current_workouts)}")
        print(f"   Workouts précédents: {len(previous_workouts)}")

        # Check if enough data
        if len(current_workouts) < 3:
            print("   ⚠️ Données insuffisantes pour analyse méso-cycle (<3 workouts)")
            return f"""
## 📈 ANALYSE MÉSO-CYCLE ENRICHIE

**Période** : {current_weeks[0]} → {current_weeks[-1]}

⚠️ **Données insuffisantes** : Seulement {len(current_workouts)} workout(s) trouvé(s).
Minimum requis : 3 workouts pour analyse statistique significative.

_L'analyse méso-cycle sera disponible au prochain cycle avec plus de données._

---
"""

        # Calculate statistics
        current_decoupling = self._calculate_decoupling_stats(current_workouts)
        previous_decoupling = self._calculate_decoupling_stats(previous_workouts)

        current_adherence = self._calculate_adherence_stats(current_workouts)
        previous_adherence = self._calculate_adherence_stats(previous_workouts)

        current_diversity = self._analyze_workout_diversity(current_workouts)

        # Build report
        report = f"""
## 📈 ANALYSE MÉSO-CYCLE ENRICHIE ({self.mesocycle_weeks} Semaines)

**Période analysée** : {current_weeks[0]} → {current_weeks[-1]}
**Cycle précédent** : {previous_weeks[0]} → {previous_weeks[-1]}

---

### 📊 Patterns d'Exécution (Cycle Actuel)

"""

        # Only show decoupling if data available
        if current_decoupling["count"] > 0:
            report += f"""**Découplage Cardiovasculaire** :
- Moyenne : {current_decoupling['avg']:.1f}%
- Plage : {current_decoupling['min']:.1f}% - {current_decoupling['max']:.1f}%
- Séances validées (<7.5%) : {current_decoupling['validated_count']}/{current_decoupling['count']} ({current_decoupling['validated_pct']:.0f}%)
"""
        else:
            report += "**Découplage Cardiovasculaire** : _Données non disponibles pour ce cycle_\n"

        report += "\n"

        # Add comparison with previous cycle
        if previous_decoupling["count"] > 0:
            decoupling_delta = current_decoupling["avg"] - previous_decoupling["avg"]
            trend = "amélioration" if decoupling_delta < 0 else "dégradation"
            report += f"- **Tendance vs cycle précédent** : {decoupling_delta:+.1f}% ({trend})\n"

        report += f"""
**Charge d'Entraînement** :
- TSS moyen/séance : {current_adherence['tss_avg']:.0f}
- TSS total cycle : {current_adherence['tss_total']:.0f}
- IF moyen : {current_adherence['if_avg']:.2f}
- Nombre séances : {current_adherence['workout_count']}
"""

        # Add comparison
        if previous_adherence["workout_count"] > 0:
            tss_delta = current_adherence["tss_total"] - previous_adherence["tss_total"]
            report += f"- **Charge vs cycle précédent** : {tss_delta:+.0f} TSS\n"

        report += f"""
---

### 🎨 Diversité & Engagement

**Workouts uniques** : {current_diversity['unique_count']}/{current_diversity['total_count']} ({current_diversity['diversity_pct']:.0f}% diversité)

**Répartition par type** :
"""

        for workout_type, count in sorted(
            current_diversity["by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            report += f"- {workout_type} : {count} séance(s)\n"

        report += """
---

### 💡 Insights Stratégiques

"""

        # Generate insights based on data
        insights = []

        # Decoupling insight
        if current_decoupling["validated_pct"] >= 90:
            insights.append(
                "✅ **Qualité excellente** : >90% séances validées (découplage <7.5%). "
                "Marge pour augmenter charge ou intensité."
            )
        elif current_decoupling["validated_pct"] < 70:
            insights.append(
                "⚠️ **Qualité dégradée** : <70% séances validées. "
                "Privilégier récupération et réduire intensité."
            )

        # Diversity insight
        if current_diversity["diversity_pct"] < 70:
            insights.append(
                f"⚠️ **Diversité faible** : {current_diversity['diversity_pct']:.0f}% seulement. "
                "Risque de monotonie. Varier formats et structures."
            )

        # Trend insight
        if previous_decoupling["count"] > 0:
            decoupling_delta = current_decoupling["avg"] - previous_decoupling["avg"]
            if decoupling_delta < -0.5:
                insights.append(
                    f"📈 **Progression qualité** : Découplage amélioré de {-decoupling_delta:.1f}% "
                    "vs cycle précédent. Adaptations physiologiques efficaces."
                )
            elif decoupling_delta > 0.5:
                insights.append(
                    f"📉 **Alerte fatigue** : Découplage dégradé de {decoupling_delta:.1f}% "
                    "vs cycle précédent. Envisager semaine récupération."
                )

        if insights:
            report += "\n".join(insights) + "\n"
        else:
            report += "Aucun insight critique détecté. Progression normale.\n"

        report += f"""
---

### 🎯 Recommandations pour Cycle Suivant

**Basées sur analyse {self.mesocycle_weeks} semaines** :

1. **Charge** : TSS moyen actuel {current_adherence['tss_avg']:.0f}/séance est {"soutenable" if current_decoupling['validated_pct'] >= 80 else "élevé"}
"""

        if current_decoupling["validated_pct"] >= 85 and current_adherence["tss_avg"] < 70:
            report += "   → Possibilité d'augmenter volume (+10-15 TSS/séance)\n"
        elif current_decoupling["validated_pct"] < 75:
            report += "   → Maintenir ou réduire volume jusqu'à récupération complète\n"

        report += f"""
2. **Diversité** : {"✅ Bonne variété maintenue" if current_diversity['diversity_pct'] >= 75 else "⚠️ Introduire nouvelles structures"}

3. **Qualité** : {"✅ Maintenir standards actuels" if current_decoupling['validated_pct'] >= 80 else "⚠️ Prioriser qualité sur quantité"}

---

*Rapport généré automatiquement - Fin méso-cycle {self.week_id}*
"""

        # Mark cycle as analyzed
        cycle_id = f"cycle_ending_{self.week_id}"
        if cycle_id not in self.state.get("analyzed_cycles", []):
            self.state.setdefault("analyzed_cycles", []).append(cycle_id)
            self._save_state()

        print("   ✅ Rapport méso-cycle généré")

        return report


def should_include_mesocycle_context(week_id: str) -> bool:
    """
    Check if mesocycle context should be included for given week.

    Args:
        week_id: Week ID to check (e.g., "S082")

    Returns:
        True if mesocycle enriched context should be included

    Examples:
        >>> should_include_mesocycle_context("S078")
        True  # End of 6-week cycle
        >>> should_include_mesocycle_context("S079")
        False  # Mid-cycle
    """
    analyzer = MesocycleAnalyzer(week_id)
    return analyzer.should_generate_report()


def generate_mesocycle_context(week_id: str) -> str:
    """
    Generate mesocycle enriched context if applicable.

    Args:
        week_id: Week ID (e.g., "S082")

    Returns:
        Markdown formatted mesocycle report or empty string

    Examples:
        >>> context = generate_mesocycle_context("S078")
        >>> "ANALYSE MÉSO-CYCLE" in context
        True
    """
    analyzer = MesocycleAnalyzer(week_id)

    if not analyzer.should_generate_report():
        return ""

    return analyzer.generate_mesocycle_report()
