"""Reporting methods for BaselineAnalyzer."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ReportingMixin:
    """Génération rapports JSON + Markdown."""

    def generate_json_output(self, results: dict[str, Any]) -> Path:
        """Generate JSON dataset output.

        Args:
            results: Analysis results dict

        Returns:
            Path to generated JSON file
        """
        output_file = self.output_dir / "baseline_preliminary.json"

        with open(output_file, "w", encoding="utf-8") as f:
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

        with open(output_file, "w", encoding="utf-8") as f:
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
- **Séances remplacées**: {adherence.get('replaced', 0)}
- **Séances annulées**: {adherence.get('cancelled', 0)}

### Détail Séances Non Complétées
"""

        # Skipped sessions
        if adherence.get("skipped_details"):
            report += "\n#### ⏭️ Séances Sautées\n"
            for detail in adherence["skipped_details"]:
                report += f"- **{detail['date']}**: {detail['name']}\n"
                report += f"  - Raison: {detail['reason']}\n"

        # Replaced sessions
        if adherence.get("replaced_details"):
            report += "\n#### 🔄 Séances Remplacées\n"
            for detail in adherence["replaced_details"]:
                report += f"- **{detail['date']}**: {detail['name']}\n"
                report += f"  - Raison: {detail['reason']}\n"

        # Cancelled sessions
        if adherence.get("cancelled_details"):
            report += "\n#### ❌ Séances Annulées\n"
            for detail in adherence["cancelled_details"]:
                report += f"- **{detail['date']}**: {detail['name']}\n"
                report += f"  - Raison: {detail['reason']}\n"

        # If nothing skipped/replaced/cancelled
        if (
            not adherence.get("skipped_details")
            and not adherence.get("replaced_details")
            and not adherence.get("cancelled_details")
        ):
            report += "✅ Aucune séance manquée, remplacée ou annulée\n"

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

        # NEW: Section 1.1 - Unsolicited Activities Analysis
        unsolicited = results.get("unsolicited_activities", {})
        if unsolicited.get("total_count", 0) > 0:
            report += f"""
### 🏃 Activités Non Sollicitées

- **Total**: {unsolicited.get('total_count', 0)} activités
- **TSS non planifié**: {unsolicited.get('total_tss', 0):.0f}
- **% du TSS total**: {unsolicited.get('percentage_of_total', 0):.1f}%

#### Détail
"""
            for activity in unsolicited.get("details", [])[:5]:  # Limit to first 5
                report += (
                    f"- **{activity['date']}**: {activity['name']} ({activity['tss']:.0f} TSS)\n"
                )
                if activity.get("avg_power"):
                    report += f"  - Puissance: {activity['avg_power']:.0f}W"
                    if activity.get("normalized_power"):
                        report += f" (NP: {activity['normalized_power']:.0f}W)"
                    report += "\n"

            # Explain TSS overload if applicable
            if unsolicited.get("percentage_of_total", 0) > 10:
                report += f"""
**💡 Analyse** : Les activités non sollicitées représentent {unsolicited.get('percentage_of_total', 0):.0f}% du TSS total, ce qui explique en grande partie la sur-charge observée (+{(tss.get('completion_rate', 1) - 1) * 100:.0f}% TSS vs planifié).
"""

        # NEW: Section 1.2 - Skip Reasons Analysis
        skip_reasons = adherence.get("skip_reasons_analysis", {})
        if skip_reasons.get("total", 0) > 0:
            report += f"""
### 🔍 Analyse Raisons Séances Sautées

- **Total séances analysées**: {skip_reasons.get('total', 0)}

#### Distribution par Catégorie
"""
            for category, stats in skip_reasons.get("distribution", {}).items():
                report += f"- **{category.replace('_', ' ').title()}**: {stats['count']} séances ({stats['percentage']:.0f}%)\n"

            # Dominant category analysis
            if skip_reasons.get("distribution"):
                dominant = max(skip_reasons["distribution"].items(), key=lambda x: x[1]["count"])
                dominant_category = dominant[0].replace("_", " ").title()
                dominant_pct = dominant[1]["percentage"]
                report += f"""
**💡 Pattern dominant** : {dominant_category} ({dominant_pct:.0f}% des séances sautées)
"""

        # NEW: Section 1.3 - Day/Type Patterns Analysis
        day_analysis = adherence.get("day_patterns_analysis", {})
        type_analysis = adherence.get("workout_type_patterns_analysis", {})

        if day_analysis.get("high_risk_days") or type_analysis.get("high_risk_types"):
            report += """
### 📊 Patterns à Risque

"""
            # High-risk days
            if day_analysis.get("high_risk_days"):
                report += "#### 📅 Jours à Risque\n"
                for day_risk in day_analysis["high_risk_days"]:
                    risk_emoji = "🔴" if day_risk["risk_score"] >= 60 else "🟠"
                    report += f"- {risk_emoji} **{day_risk['day']}**: {day_risk['adherence_rate'] * 100:.0f}% adherence (Risque: {day_risk['risk_score']:.0f}/100)\n"

            # High-risk types
            if type_analysis.get("high_risk_types"):
                report += "\n#### 🏋️ Types d'Entraînement à Risque\n"
                for type_risk in type_analysis["high_risk_types"]:
                    risk_emoji = "🔴" if type_risk["risk_score"] >= 60 else "🟠"
                    report += f"- {risk_emoji} **{type_risk['type']}**: {type_risk['adherence_rate'] * 100:.0f}% adherence (Risque: {type_risk['risk_score']:.0f}/100)\n"

            # Recommendations
            all_recommendations = []
            if day_analysis.get("recommendations"):
                all_recommendations.extend(day_analysis["recommendations"])
            if type_analysis.get("recommendations"):
                all_recommendations.extend(type_analysis["recommendations"])

            if all_recommendations:
                report += "\n#### 💡 Recommandations Patterns\n"
                for rec in all_recommendations:
                    report += f"{rec}\n"

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

*Sprint R9.F - Advanced Pattern Analysis*
"""

        return report
