"""
Composable prompt generation system for AI analysis.

GARTNER_TIME: I
STATUS: Development
LAST_REVIEW: 2025-12-26
PRIORITY: P1
MIGRATION_SOURCE: cyclisme-training-automation-v2/src/core/prompt_generator.py
DOCSTRING: v2

Système de génération de prompts composables pour analyses IA.
Supporte building blocks réutilisables (intro, context, data, instructions,
output_format) avec templates personnalisables.

Examples:
    Basic prompt generation::

        from cyclisme_training_logs.core.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        # Prompt simple
        prompt = generator.generate_daily_analysis_prompt(
            activity_id="i123456",
            workout_data={"duration": 3600, "tss": 45}
        )

        print(prompt)  # Prompt markdown complet

    Custom prompt with blocks::

        # Composition manuelle
        blocks = [
            generator.intro_block("Analyse séance"),
            generator.context_block({"FTP": 220, "Weight": 84}),
            generator.data_block(workout_data),
            generator.instructions_block("Analyser découplage"),
            generator.output_format_block("markdown")
        ]

        custom_prompt = "\\n\\n".join(blocks)

    Weekly prompt generation::

        # Prompt hebdomadaire (Phase 2)
        weekly_prompt = generator.generate_weekly_analysis_prompt(
            week="S073",
            workouts=[...],
            metrics={...}
        )

Author: Claude Code
Created: 2025-12-26 (Migrated from v2)
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import date, datetime


class PromptGenerator:
    """
    Générateur de prompts composables pour analyses IA.

    Building blocks réutilisables :
    - intro_block : Introduction analyse
    - context_block : Contexte athlète/entraînement
    - data_block : Données activité
    - instructions_block : Instructions spécifiques
    - output_format_block : Format sortie attendu
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialiser générateur.

        Args:
            templates_dir: Répertoire templates custom (optionnel)
        """
        self.templates_dir = templates_dir

    def intro_block(self, analysis_type: str) -> str:
        """
        Bloc introduction analyse.

        Args:
            analysis_type: Type analyse (daily, weekly, cycle)

        Returns:
            Bloc markdown introduction
        """
        intros = {
            "daily": "# Analyse Séance Quotidienne",
            "weekly": "# Analyse Hebdomadaire",
            "cycle": "# Analyse Cycle (4 semaines)"
        }

        return intros.get(analysis_type, "# Analyse")

    def context_block(self, athlete_data: Dict[str, Any]) -> str:
        """
        Bloc contexte athlète et entraînement.

        Args:
            athlete_data: Données athlète (FTP, poids, objectifs, etc.)

        Returns:
            Bloc markdown contexte
        """
        context = "## Contexte Athlète\n\n"

        if 'FTP' in athlete_data:
            context += f"- **FTP actuelle :** {athlete_data['FTP']}W\n"

        if 'weight' in athlete_data:
            context += f"- **Poids :** {athlete_data['weight']}kg\n"

        if 'goals' in athlete_data:
            context += f"- **Objectifs :** {athlete_data['goals']}\n"

        if 'resting_hr' in athlete_data:
            context += f"- **FC repos :** {athlete_data['resting_hr']} bpm\n"

        return context

    def data_block(self, workout_data: Dict[str, Any]) -> str:
        """
        Bloc données workout.

        Args:
            workout_data: Données activité (durée, TSS, puissance, etc.)

        Returns:
            Bloc markdown données
        """
        data = "## Données Séance\n\n"

        if 'duration' in workout_data:
            duration_min = workout_data['duration'] // 60
            data += f"- **Durée :** {duration_min} min\n"

        if 'tss' in workout_data:
            data += f"- **TSS :** {workout_data['tss']}\n"

        if 'normalized_power' in workout_data:
            data += f"- **Puissance normalisée :** {workout_data['normalized_power']}W\n"

        if 'average_power' in workout_data:
            data += f"- **Puissance moyenne :** {workout_data['average_power']}W\n"

        if 'intensity_factor' in workout_data:
            data += f"- **IF :** {workout_data['intensity_factor']:.2f}\n"

        return data

    def instructions_block(self, instructions: str) -> str:
        """
        Bloc instructions spécifiques analyse.

        Args:
            instructions: Instructions texte

        Returns:
            Bloc markdown instructions
        """
        return f"## Instructions\n\n{instructions}\n"

    def output_format_block(self, format_type: str = "markdown") -> str:
        """
        Bloc format sortie attendu.

        Args:
            format_type: Type format (markdown, json, etc.)

        Returns:
            Bloc markdown format
        """
        formats = {
            "markdown": """## Format Sortie

Répondre en markdown avec :

### SXXX-XX (YYYY-MM-DD)
**Durée:** XXmin | **TSS:** XX | **IF:** X.XX

#### Métriques Pré-séance
- CTL: XX
- ATL: XX
- TSB: XX

#### Exécution
- Découplage: X.X%
- RPE: X/10

#### Analyse
[Analyse détaillée]
""",
            "json": """## Format Sortie

Répondre en JSON :
```json
{
  "session_id": "SXXX-XX",
  "date": "YYYY-MM-DD",
  "metrics": {...},
  "analysis": "..."
}
```
"""
        }

        return formats.get(format_type, "")

    def generate_daily_analysis_prompt(
        self,
        activity_id: str,
        workout_data: Dict[str, Any],
        athlete_data: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None
    ) -> str:
        """
        Générer prompt complet analyse daily.

        Args:
            activity_id: ID activité Intervals.icu
            workout_data: Données workout
            athlete_data: Données athlète (optionnel)
            feedback: Feedback athlète (optionnel)

        Returns:
            Prompt markdown complet
        """
        blocks = [
            self.intro_block("daily"),
            ""
        ]

        # Contexte athlète si fourni
        if athlete_data:
            blocks.append(self.context_block(athlete_data))
            blocks.append("")

        # Données workout
        blocks.append(self.data_block(workout_data))
        blocks.append("")

        # Feedback si fourni
        if feedback:
            blocks.append(f"## Feedback Athlète\n\n{feedback}\n")
            blocks.append("")

        # Instructions
        instructions = """Analyser cette séance en détail :

1. **Métriques clés** : TSS, IF, découplage cardiovasculaire
2. **Qualité exécution** : Respect zones, pattern technique
3. **Recommandations** : Adaptations séance suivante
4. **Points vigilance** : Fatigue, récupération nécessaire"""

        blocks.append(self.instructions_block(instructions))
        blocks.append("")

        # Format sortie
        blocks.append(self.output_format_block("markdown"))

        return "\n".join(blocks)

    def generate_weekly_analysis_prompt(
        self,
        week: str,
        workouts: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> str:
        """
        Générer prompt analyse hebdomadaire (Phase 2).

        Args:
            week: Numéro semaine (S073)
            workouts: Liste workouts semaine
            metrics: Métriques CTL/ATL/TSB

        Returns:
            Prompt markdown complet
        """
        # Implémentation Phase 2
        raise NotImplementedError("Weekly prompt generation (Phase 2)")
