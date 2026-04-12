"""Prompt generation methods for WeeklyPlanner."""

import json
import sys
from pathlib import Path

_TEMPLATE_DIR = Path(__file__).parent / "templates"


class PromptMixin:
    """Full planning prompt assembly."""

    def generate_planning_prompt(self) -> str:
        """Generate le prompt complet pour l'assistant IA."""
        print("\n✍️ Génération du prompt de planification...", file=sys.stderr)

        next_week = self._next_week_number()
        date_start_str = self.start_date.strftime("%d/%m/%Y")
        date_end_str = self.end_date.strftime("%d/%m/%Y")

        periodization_context = self.load_periodization_context()
        self._periodization_context = periodization_context
        previous_week_workouts = self.load_previous_week_workouts()
        mesocycle_context = self._load_mesocycle_context()

        # Dynamic header
        prompt = (
            f"# Planification Hebdomadaire Cyclisme - {self.week_number}.\n\n"
            f"## Contexte Athlète\n\n"
            f"{self.context_files.get('project_prompt', '[Project prompt non chargé]')}\n\n"
            f"---\n\n"
            f"## Période à Planifier\n\n"
            f"- **Semaine** : {self.week_number}\n"
            f"- **Dates** : {date_start_str} → {date_end_str} (7 jours)\n"
            f"- **Semaine suivante** : {next_week}\n\n"
            f"---\n\n"
            f"## État Actuel\n\n"
            f"### Métriques Actuelles\n"
            f"```json\n{json.dumps(self.current_metrics, indent=2, ensure_ascii=False)}\n```\n\n"
            f"### Bilan Semaine Précédente ({self._previous_week_number()})\n\n"
            f"{self.previous_week_bilan}\n\n"
            f"{previous_week_workouts}\n\n"
            f"---\n"
        )

        # Conditional: periodization context
        if periodization_context:
            prompt += self._format_periodization_section(periodization_context)

        # Conditional: mesocycle context
        if mesocycle_context:
            prompt += mesocycle_context + "\n---\n"

        # Conditional: upcoming events (races, targets, etc.)
        events_section = self._load_week_events_section()
        if events_section:
            prompt += events_section + "\n---\n"

        # Static methodology template with variable substitution
        template_text = (_TEMPLATE_DIR / "peaks_methodology.md").read_text(encoding="utf-8")
        prompt += template_text.format(
            week_number=self.week_number,
            next_week=next_week,
            week_after_next=self._week_after_next(),
            date_start_str=date_start_str,
            date_end_str=date_end_str,
            planning_preferences=self.context_files.get(
                "planning_preferences", "[Préférences non chargées]"
            ),
            cycling_concepts=self.context_files.get("cycling_concepts", "[Concepts non chargés]"),
            protocols=self.context_files.get("protocols", "[Protocoles non chargés]"),
            intelligence=self.context_files.get(
                "intelligence", "[Aucune recommandation disponible]"
            ),
            zwift_workouts=self._load_available_zwift_workouts(),
        )

        return prompt

    def _format_periodization_section(self, pc: dict) -> str:
        """Format the periodization context section."""
        section = (
            f"\n## 🎯 Contexte Périodisation (Stratégie Macro-Cycle)\n\n"
            f"### Phase Actuelle : {pc['phase']}\n\n"
            f"**Objectifs Cycle** :\n"
            f"- CTL actuel : {pc['ctl_current']:.1f}\n"
            f"- CTL cible : {pc['ctl_target']:.0f}\n"
            f"- Déficit CTL : {pc['ctl_deficit']:.1f} points\n"
            f"- FTP actuel : {pc['ftp_current']}W\n"
            f"- FTP cible : {pc['ftp_target']}W\n\n"
            f"**Progression** :\n"
            f"- Durée reconstruction estimée : {pc['weeks_to_target']} semaines\n"
            f"- TSS semaines charge : {pc['weekly_tss_load']} TSS\n"
            f"- TSS semaines récupération : {pc['weekly_tss_recovery']} TSS\n"
            f"- Fréquence récupération : Tous les {pc['recovery_week_frequency']} semaines\n\n"
            f"**Distribution Intensité Recommandée pour Phase {pc['phase']}** :\n"
        )
        for zone, percentage in pc["intensity_distribution"].items():
            focus_marker = " ← **FOCUS**" if percentage >= 0.20 else ""
            section += f"- **{zone}** : {percentage * 100:.0f}%{focus_marker}\n"

        section += (
            f"\n**État PID Controller** : {pc['pid_status']}\n\n"
            f"**Rationale Phase** :\n{pc['rationale']}\n\n"
            f"**➡️ CRITIQUE pour Planification** : Les workouts de la semaine "
            f"{self.week_number} doivent être alignés avec la phase {pc['phase']}. "
            f"Respecter la distribution intensité recommandée ci-dessus et l'objectif "
            f"TSS hebdomadaire ({pc['weekly_tss_load']} TSS semaine charge, "
            f"{pc['weekly_tss_recovery']} TSS semaine récup).\n\n---\n"
        )
        return section
