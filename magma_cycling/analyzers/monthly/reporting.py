"""Report generation and AI prompt mixin for MonthlyAnalyzer."""

from datetime import datetime


class ReportingMixin:
    """Monthly report and AI prompt generation."""

    def generate_report(self, stats: dict, ai_analysis: str | None = None) -> str:
        """Generate markdown report."""
        month_name = self.month_date.strftime("%B %Y")

        report = f"""# \U0001f4ca Analyse Mensuelle - {month_name}.

## R\u00e9sum\u00e9 Ex\u00e9cutif

**P\u00e9riode :** {stats['tss_by_week'][0]['start_date']} \u2192 {stats['tss_by_week'][-1]['end_date']}
**Semaines analys\u00e9es :** {stats['total_weeks']}

### Charge d'Entra\u00eenement (TSS)
- **TSS Cible :** {stats['tss_target_total']}
- **TSS R\u00e9alis\u00e9 :** {stats['tss_realized']}
- **Taux de r\u00e9alisation :** {stats['tss_achievement_rate']:.1f}%

### Sessions
- **Total planifi\u00e9 :** {stats['total_sessions']} sessions
- **Compl\u00e9t\u00e9es :** {stats['completed']} ({stats['completed'] / stats['total_sessions'] * 100:.1f}%)
- **Modifi\u00e9es :** {stats['modified']}
- **Saut\u00e9es :** {stats['skipped']}
- **Annul\u00e9es :** {stats['cancelled']}
- **Repos :** {stats['rest_days']}
- **Taux d'adh\u00e9rence :** {stats['adherence_rate']:.1f}%

## \U0001f4c8 Progression Hebdomadaire

| Semaine | Dates | TSS Cible | TSS R\u00e9alis\u00e9 | % R\u00e9alisation |
|---------|-------|-----------|-------------|---------------|.
"""
        for week in stats["tss_by_week"]:
            achievement = (
                (week["tss_actual"] / week["tss_target"] * 100) if week["tss_target"] > 0 else 0
            )
            report += f"| {week['week_id']} | {week['start_date']} \u2192 {week['end_date']} | {week['tss_target']} | {week['tss_actual']} | {achievement:.1f}% |\n"

        report += "\n## \U0001f3af R\u00e9partition par Type de S\u00e9ance\n\n"

        type_labels = {
            "END": "Endurance",
            "INT": "Intensit\u00e9",
            "REC": "R\u00e9cup\u00e9ration",
            "TEC": "Technique",
            "FOR": "Force",
            "CAD": "Cadence",
            "MIX": "Mixte",
        }

        for session_type, count in sorted(
            stats["sessions_by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                count / (stats["total_sessions"] - stats["rest_days"]) * 100
                if stats["total_sessions"] > stats["rest_days"]
                else 0
            )
            type_name = type_labels.get(session_type, session_type)
            report += f"- **{type_name} ({session_type})** : {count} sessions ({percentage:.1f}%)\n"

        report += "\n## \U0001f4ca Statut des Sessions\n\n"
        for status, count in sorted(
            stats["sessions_by_status"].items(), key=lambda x: x[1], reverse=True
        ):
            percentage = count / stats["total_sessions"] * 100
            report += f"- **{status.title()}** : {count} ({percentage:.1f}%)\n"

        # Add AI analysis if available
        if ai_analysis:
            report += f"\n## \U0001f916 Analyse IA - Insights & Recommandations\n\n{ai_analysis}\n"

        report += f"\n---\n*G\u00e9n\u00e9r\u00e9 le {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"

        return report

    def generate_ai_prompt(self, stats: dict) -> str:
        """Generate prompt for AI analysis."""
        month_name = self.month_date.strftime("%B %Y")

        prompt = f"""Analyse ce mois d'entra\u00eenement cyclisme ({month_name}) et fournis des insights :

\U0001f4ca DONN\u00c9ES MENSUELLES :
- {stats['total_weeks']} semaines analys\u00e9es
- TSS Cible : {stats['tss_target_total']}
- TSS R\u00e9alis\u00e9 : {stats['tss_realized']} ({stats['tss_achievement_rate']:.1f}%)
- Taux d'adh\u00e9rence : {stats['adherence_rate']:.1f}%
- Sessions compl\u00e9t\u00e9es : {stats['completed']}/{stats['total_sessions']}
- Sessions saut\u00e9es : {stats['skipped']}
- Repos : {stats['rest_days']}

\U0001f4c8 PROGRESSION HEBDOMADAIRE :
"""
        for week in stats["tss_by_week"]:
            prompt += f"\n- {week['week_id']} : {week['tss_actual']}/{week['tss_target']} TSS"

        prompt += "\n\n\U0001f3af R\u00c9PARTITION TYPES :\n"
        for session_type, count in sorted(
            stats["sessions_by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (
                count / (stats["total_sessions"] - stats["rest_days"]) * 100
                if stats["total_sessions"] > stats["rest_days"]
                else 0
            )
            prompt += f"- {session_type} : {count} sessions ({percentage:.0f}%)\n"

        prompt += """
ANALYSE DEMAND\u00c9E (format markdown) :

1. **\u00c9valuation Globale** (2-3 phrases)
   - Qualit\u00e9 du mois (excellent/bon/moyen/insuffisant)
   - Respect de la planification

2. **Points Forts** (3-4 bullets)
   - Ce qui a bien fonctionn\u00e9

3. **Points d'Am\u00e9lioration** (3-4 bullets)
   - Ce qui pourrait \u00eatre optimis\u00e9

4. **Analyse de P\u00e9riodisation** (2-3 phrases)
   - Coh\u00e9rence de la charge (progression/plateau/taper)
   - \u00c9quilibre intensit\u00e9/volume/r\u00e9cup\u00e9ration

5. **Recommandations pour le Mois Suivant** (3-5 bullets)
   - Ajustements sugg\u00e9r\u00e9s
   - Focus prioritaires

Sois concret, direct et orient\u00e9 action. Utilise des emojis pour la lisibilit\u00e9.
"""
        return prompt

    def _load_current_metrics(self) -> dict:
        """Load current athlete metrics for prompt enrichment."""
        from magma_cycling.prompts.prompt_builder import load_current_metrics

        return load_current_metrics()
