"""
Weekly analyzer orchestrating 6 automated markdown reports.
Orchestrateur principal pour génération automatisée des 6 reports
hebdomadaires standards : workout_history, metrics_evolution,
training_learnings, protocol_adaptations, transition, bilan_final.

Examples:
    Generate all 6 reports::

        from cyclisme_training_logs.analyzers.weekly_analyzer import WeeklyAnalyzer
        from cyclisme_training_logs.analyzers.weekly_aggregator import WeeklyAggregator
        from datetime import date

        # Pipeline complet
        aggregator = WeeklyAggregator(week="S073", start_date=date(2025, 1, 6))
        aggregation = aggregator.aggregate()

        # Générer reports
        analyzer = WeeklyAnalyzer(
            week="S073",
            weekly_data=aggregation.data['processed']
        )

        reports = analyzer.generate_all_reports()

        # 6 fichiers générés
        print(reports['workout_history'])
        print(reports['metrics_evolution'])
        print(reports['training_learnings'])

    Generate single report::

        # Générer seulement workout_history
        analyzer = WeeklyAnalyzer(week="S073", weekly_data=data)

        history = analyzer.generate_workout_history()
        print(history)

    Save reports to disk::

        from pathlib import Path

        # Sauvegarder tous reports
        reports = analyzer.generate_all_reports()
        output_dir = Path("~/training-logs/weekly-reports/S073")

        analyzer.save_reports(reports, output_dir)

Author: Claude Code
Created: 2025-12-26 (Phase 2 - Weekly Analysis System)

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P1
    Version: v2
"""

from pathlib import Path
from typing import Dict, Any, Optional
import logging

from cyclisme_training_logs.core.prompt_generator import PromptGenerator

logger = logging.getLogger(__name__)


class WeeklyAnalyzer:
    """
    Analyseur hebdomadaire générant 6 reports markdown.

    Reports générés :
    1. workout_history_sXXX.md - Chronologie détaillée séances
    2. metrics_evolution_sXXX.md - Évolution CTL/ATL/TSB
    3. training_learnings_sXXX.md - Enseignements techniques
    4. protocol_adaptations_sXXX.md - Ajustements protocoles
    5. transition_sXXX_sYYY.md - Recommandations semaine suivante
    6. bilan_final_sXXX.md - Synthèse globale
    """

    def __init__(
        self,
        week: str,
        weekly_data: Dict[str, Any],
        prompt_generator: Optional[PromptGenerator] = None
    ):
        """
        Initialiser analyzer.

        Args:
            week: Numéro semaine (S073)
            weekly_data: Données traitées par WeeklyAggregator
            prompt_generator: Generator prompts (créé si None)
        """
        self.week = week
        self.data = weekly_data
        self.prompt_generator = prompt_generator or PromptGenerator()

    def generate_all_reports(self) -> Dict[str, str]:
        """
        Générer les 6 reports complets.

        Returns:
            Dict avec clés : workout_history, metrics_evolution,
            training_learnings, protocol_adaptations, transition, bilan_final
        """
        logger.info(f"Generating all 6 reports for {self.week}")

        reports = {
            'workout_history': self.generate_workout_history(),
            'metrics_evolution': self.generate_metrics_evolution(),
            'training_learnings': self.generate_training_learnings(),
            'protocol_adaptations': self.generate_protocol_adaptations(),
            'transition': self.generate_transition(),
            'bilan_final': self.generate_bilan_final()
        }

        logger.info("All reports generated successfully")
        return reports

    def generate_workout_history(self) -> str:
        """
        Générer workout_history_sXXX.md.

        Format :
        # Historique Entraînements SXXX

        ## SXXX-01 (YYYY-MM-DD)
        **Durée:** XXmin | **TSS:** XX | **IF:** X.XX

        ### Métriques Pré-séance
        ...
        """
        workouts = self.data.get('workouts', [])

        lines = [
            f"# Historique Entraînements {self.week}\n",
            f"**Période :** {self._get_period()}\n",
            f"**Nombre séances :** {len(workouts)}\n"
        ]

        for workout in workouts:
            # Include workout name if available
            workout_name = workout.get('name', '')
            if workout_name:
                lines.append(f"\n## {self.week}-{workout['session_number']:02d}: {workout_name} ({workout['date']})\n")
            else:
                lines.append(f"\n## {self.week}-{workout['session_number']:02d} ({workout['date']})\n")

            # Métriques principales
            duration_min = workout['duration'] // 60
            lines.append(f"**Durée:** {duration_min}min | **TSS:** {workout['tss']} | **IF:** {workout.get('if', 0):.2f}\n")

            # Puissance
            if workout.get('normalized_power', 0) > 0:
                lines.append("\n### Puissance")
                lines.append(f"- Normalisée: {workout['normalized_power']}W")
                lines.append(f"- Moyenne: {workout.get('average_power', 0)}W\n")

            # FC
            if workout.get('average_hr', 0) > 0:
                lines.append("\n### Fréquence Cardiaque")
                lines.append(f"- Moyenne: {workout['average_hr']} bpm")
                lines.append(f"- Max: {workout.get('max_hr', 0)} bpm\n")

            # Feedback
            if 'feedback' in workout:
                feedback = workout['feedback']
                lines.append("\n### Feedback Athlète")

                if 'rpe' in feedback:
                    lines.append(f"- RPE: {feedback['rpe']}/10")

                if 'comments' in feedback:
                    lines.append(f"- Notes: {feedback['comments']}\n")

        return "\n".join(lines)

    def generate_metrics_evolution(self) -> str:
        """
        Générer metrics_evolution_sXXX.md.

        Format :
        # Évolution Métriques SXXX

        ## CTL/ATL/TSB Quotidien
        | Date | CTL | ATL | TSB |
        """
        metrics_evolution = self.data.get('metrics_evolution', {})
        daily = metrics_evolution.get('daily', [])
        trends = metrics_evolution.get('trends', {})

        lines = [
            f"# Évolution Métriques {self.week}\n",
            "## CTL/ATL/TSB Quotidien\n"
        ]

        if daily:
            # Table
            lines.append("| Date | CTL | ATL | TSB |")
            lines.append("|------|-----|-----|-----|")

            for day in daily:
                lines.append(
                    f"| {day['date']} | {day['ctl']:.1f} | "
                    f"{day['atl']:.1f} | {day['tsb']:.1f} |"
                )

            lines.append("")

        # Tendances
        if trends:
            lines.append("\n## Tendances Hebdomadaires\n")
            lines.append(f"- **Variation CTL :** {trends.get('ctl_change', 0):+.1f}")
            lines.append(f"- **Variation ATL :** {trends.get('atl_change', 0):+.1f}")
            lines.append(f"- **Variation TSB :** {trends.get('tsb_change', 0):+.1f}\n")

        # Wellness insights
        if 'wellness_insights' in self.data:
            insights = self.data['wellness_insights']
            lines.append("\n## Wellness\n")

            if insights.get('sleep_hours_avg', 0) > 0:
                lines.append(f"- **Sommeil moyen :** {insights['sleep_hours_avg']:.1f}h")

            if insights.get('weight_trend', 0) != 0:
                lines.append(f"- **Évolution poids :** {insights['weight_trend']:+.1f}kg\n")

        return "\n".join(lines)

    def generate_training_learnings(self) -> str:
        """
        Générer training_learnings_sXXX.md.

        Format :
        # Enseignements d'Entraînement SXXX

        ## Découvertes Majeures
        - Point 1
        - Point 2
        """
        learnings = self.data.get('learnings', [])

        lines = [
            f"# Enseignements d'Entraînement {self.week}\n",
            "## Découvertes Majeures\n"
        ]

        if learnings:
            for learning in learnings:
                lines.append(f"- {learning}")
        else:
            lines.append("*Aucun enseignement spécifique identifié*")

        lines.append("")

        # Patterns techniques (à enrichir avec AI analysis)
        lines.append("\n## Patterns Techniques\n")
        lines.append("*À compléter avec analyse IA détaillée*\n")

        return "\n".join(lines)

    def generate_protocol_adaptations(self) -> str:
        """
        Générer protocol_adaptations_sXXX.md.

        Format :
        # Adaptations Protocoles SXXX

        ## Ajustements Identifiés
        - Type: recovery
          Raison: TSB dropped
          Recommandation: Add recovery day
        """
        adaptations = self.data.get('protocol_adaptations', [])

        lines = [
            f"# Adaptations Protocoles {self.week}\n",
            "## Ajustements Identifiés\n"
        ]

        if adaptations:
            for adaptation in adaptations:
                lines.append(f"\n### {adaptation.get('type', 'Unknown').title()}")
                lines.append(f"- **Raison :** {adaptation.get('reason', 'N/A')}")
                lines.append(f"- **Recommandation :** {adaptation.get('recommendation', 'N/A')}\n")
        else:
            lines.append("*Aucune adaptation protocole nécessaire*\n")

        return "\n".join(lines)

    def generate_transition(self) -> str:
        """
        Générer transition_sXXX_sYYY.md.

        Format :
        # Transition SXXX → SYYY

        ## État Final SXXX
        - TSS total: XXX
        - TSB final: XX

        ## Recommandations SYYY
        - Focus 1
        - Focus 2
        """
        transition = self.data.get('transition', {})
        current_state = transition.get('current_state', {})
        recommendations = transition.get('recommendations', [])
        focus_areas = transition.get('focus_areas', [])

        # Calculer numéro semaine suivante
        week_num = int(self.week[1:]) if self.week.startswith('S') else 0
        next_week = f"S{week_num + 1:03d}"

        lines = [
            f"# Transition {self.week} → {next_week}\n",
            f"## État Final {self.week}\n"
        ]

        # État actuel
        lines.append(f"- **TSS total :** {current_state.get('total_tss', 0)}")
        lines.append(f"- **TSS moyen :** {current_state.get('avg_tss', 0):.1f}")
        lines.append(f"- **TSB final :** {current_state.get('final_tsb', 0):.1f}\n")

        # Recommandations
        lines.append(f"\n## Recommandations {next_week}\n")

        if recommendations:
            for rec in recommendations:
                lines.append(f"- {rec}")
        else:
            lines.append("- Continuer progression actuelle")

        lines.append("")

        # Focus areas
        if focus_areas:
            lines.append("\n## Points d'Attention\n")
            for focus in focus_areas:
                lines.append(f"- {focus}")
            lines.append("")

        return "\n".join(lines)

    def generate_bilan_final(self) -> str:
        """
        Générer bilan_final_sXXX.md.

        Format :
        # Bilan Final SXXX

        ## Objectifs vs Réalisé
        ## Métriques Clés
        ## Conclusion
        """
        summary = self.data.get('summary', {})
        compliance = self.data.get('compliance', {})

        lines = [
            f"# Bilan Final {self.week}\n",
            "## Objectifs vs Réalisé\n"
        ]

        # Compliance
        if compliance:
            rate = compliance.get('rate', 0)
            lines.append(f"- **Compliance :** {rate:.1f}%")
            lines.append(f"- **Séances planifiées :** {compliance.get('planned_count', 0)}")
            lines.append(f"- **Séances exécutées :** {compliance.get('executed_count', 0)}\n")

        # Métriques clés
        lines.append("\n## Métriques Clés\n")
        lines.append(f"- **TSS total :** {summary.get('total_tss', 0)}")
        lines.append(f"- **TSS moyen :** {summary.get('avg_tss', 0):.1f}")
        lines.append(f"- **IF moyen :** {summary.get('avg_if', 0):.2f}\n")

        # Conclusion
        lines.append("\n## Conclusion\n")
        lines.append("*Semaine complétée avec succès.*\n")

        return "\n".join(lines)

    def save_reports(self, reports: Dict[str, str], output_dir: Path) -> None:
        """
        Sauvegarder reports sur disque.

        Args:
            reports: Dict reports générés
            output_dir: Répertoire destination
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for report_name, content in reports.items():
            filename = f"{report_name}_{self.week.lower()}.md"
            filepath = output_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Saved {filename}")

    def _get_period(self) -> str:
        """Helper pour obtenir période formatée."""
        workouts = self.data.get('workouts', [])
        if not workouts:
            return "N/A"

        first_date = workouts[0].get('date', '')
        last_date = workouts[-1].get('date', '')

        return f"{first_date} → {last_date}"
