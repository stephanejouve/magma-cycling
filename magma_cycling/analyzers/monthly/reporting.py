"""Report generation and AI prompt mixin for MonthlyAnalyzer."""

from datetime import datetime


class ReportingMixin:
    """Monthly report and AI prompt generation."""

    def generate_report(self, stats: dict, ai_analysis: str | None = None) -> str:
        """Generate markdown report.

        BT-039 : affiche 3 chiffres côte-à-côte pour la cible TSS —
        initiale (intention pré-semaine), active (post-annulations,
        référence adhérence), réalisé. Écart initial → active en valeur
        absolue (pas %, illisible sur cibles reconstruction 60-90 TSS).
        Légende bilan indique les sessions dont le TSS provient du
        fallback ``planned`` (pas de match Intervals.icu).
        """
        month_name = self.month_date.strftime("%B %Y")
        target_init = stats["tss_target_total"]
        target_active = stats["tss_target_active_total"]
        realized = stats["tss_realized"]
        drift_abs = target_init - target_active
        # BT-039 : taux d'adhérence peut être None (semaine 100 % annulée
        # avec active=0 → division par zéro). Affichage « — » explicite.
        achievement_str = (
            f"{stats['tss_achievement_rate']:.1f}%"
            if stats["tss_achievement_rate"] is not None
            else "\u2014"
        )
        drift_line = (
            f"- **\u00c9cart intention \u2192 active :** \u2212{drift_abs} TSS "
            "(sessions annul\u00e9es en cours de semaine)\n"
            if drift_abs > 0
            else ""
        )

        report = f"""# \U0001f4ca Analyse Mensuelle - {month_name}.

## R\u00e9sum\u00e9 Ex\u00e9cutif

**P\u00e9riode :** {stats['tss_by_week'][0]['start_date']} \u2192 {stats['tss_by_week'][-1]['end_date']}
**Semaines analys\u00e9es :** {stats['total_weeks']}

### Charge d'Entra\u00eenement (TSS)
- **TSS Cible initiale :** {target_init} (intention en d\u00e9but de semaine)
- **TSS Cible active :** {target_active} (r\u00e9f\u00e9rence adh\u00e9rence, post-annulations)
- **TSS R\u00e9alis\u00e9 :** {realized}
- **Taux de r\u00e9alisation :** {achievement_str} (sur cible active)
{drift_line}

### Sessions
- **Total planifi\u00e9 :** {stats['total_sessions']} sessions
- **Compl\u00e9t\u00e9es :** {stats['completed']} ({stats['completed'] / stats['total_sessions'] * 100:.1f}%)
- **Modifi\u00e9es :** {stats['modified']}
- **Saut\u00e9es :** {stats['skipped']}
- **Annul\u00e9es :** {stats['cancelled']}
- **Repos :** {stats['rest_days']}
- **Taux d'adh\u00e9rence :** {stats['adherence_rate']:.1f}%

## \U0001f4c8 Progression Hebdomadaire

| Semaine | Dates | TSS Initial | TSS Actif | TSS R\u00e9alis\u00e9 | % R\u00e9alisation |
|---------|-------|-------------|-----------|---------------|---------------|
"""
        for week in stats["tss_by_week"]:
            active = week.get("tss_target_active", week["tss_target"])
            achievement = (week["tss_actual"] / active * 100) if active > 0 else None
            achievement_cell = f"{achievement:.1f}%" if achievement is not None else "\u2014"
            report += (
                f"| {week['week_id']} | {week['start_date']} \u2192 {week['end_date']} | "
                f"{week['tss_target']} | {active} | {week['tss_actual']} | "
                f"{achievement_cell} |\n"
            )

        # BT-039 : l\u00e9gende marqueur origine TSS r\u00e9alis\u00e9
        fallback_ids = stats.get("tss_source_map", {}).get("planned_fallback", [])
        if fallback_ids:
            preview = ", ".join(fallback_ids[:10])
            if len(fallback_ids) > 10:
                preview += f", ... (+{len(fallback_ids) - 10} autres)"
            report += (
                f"\n> \u2139\ufe0f **Marqueur origine TSS** : {len(fallback_ids)} session(s) "
                f"comptabilis\u00e9es depuis ``tss_planned`` (pas d'intervals_id ou pas de match "
                f"Intervals.icu) : {preview}\n"
            )

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

        # BT-042 + BT-049 : mention datée systématique dans TOUS les rapports.
        # Motif : un lecteur futur doit pouvoir dater le code qui a produit
        # chaque fichier. La version serveur référe le CHANGELOG (source de
        # vérité pour les BT actives à la génération). BT-049 : suppression
        # du « BT-039 actif » ambigu (n'indiquait rien sur BT-048).
        try:
            from magma_cycling import __version__ as _mc_version
        except Exception:
            _mc_version = "unknown"
        _now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        report += f"\n---\n> Généré {_now_iso} — magma-cycling v{_mc_version}\n"

        return report

    def generate_ai_prompt(self, stats: dict) -> str:
        """Generate prompt for AI analysis.

        BT-039 : expose les 2 cibles distinctes à l'IA — initiale
        (intention) et active (référence adhérence). L'IA voit le vrai
        signal d'adhérence sans être trompée par une cible gonflée.
        """
        month_name = self.month_date.strftime("%B %Y")
        achievement_str = (
            f"{stats['tss_achievement_rate']:.1f}%"
            if stats["tss_achievement_rate"] is not None
            else "\u2014"
        )

        prompt = f"""Analyse ce mois d'entra\u00eenement cyclisme ({month_name}) et fournis des insights :

\U0001f4ca DONN\u00c9ES MENSUELLES :
- {stats['total_weeks']} semaines analys\u00e9es
- TSS Cible initiale : {stats['tss_target_total']} (intention pr\u00e9-semaine)
- TSS Cible active : {stats['tss_target_active_total']} (post-annulations, r\u00e9f\u00e9rence adh\u00e9rence)
- TSS R\u00e9alis\u00e9 : {stats['tss_realized']} ({achievement_str} sur cible active)
- Taux d'adh\u00e9rence : {stats['adherence_rate']:.1f}%
- Sessions compl\u00e9t\u00e9es : {stats['completed']}/{stats['total_sessions']}
- Sessions saut\u00e9es : {stats['skipped']}
- Repos : {stats['rest_days']}

\U0001f4c8 PROGRESSION HEBDOMADAIRE :
"""
        for week in stats["tss_by_week"]:
            active = week.get("tss_target_active", week["tss_target"])
            drift = week["tss_target"] - active
            drift_str = f" (\u2212{drift} annul\u00e9)" if drift > 0 else ""
            prompt += (
                f"\n- {week['week_id']} : {week['tss_actual']}/{active} TSS "
                f"[cible init {week['tss_target']}{drift_str}]"
            )

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
