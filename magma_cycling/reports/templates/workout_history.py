"""Workout History Report Template.

Defines structure for workout_history_sXXX.md reports.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""


class WorkoutHistoryTemplate:
    """Template for workout_history_sXXX.md report.

    Defines the expected structure and required data fields for
    comprehensive weekly workout history reports.

    Attributes:
        REPORT_TYPE: Type identifier ("workout_history")
        MAX_WORD_COUNT: Maximum words allowed (2000)
        LANGUAGE: Report language ("fr")
    """

    REPORT_TYPE = "workout_history"
    MAX_WORD_COUNT = 2000
    LANGUAGE = "fr"

    @staticmethod
    def get_required_data() -> list[str]:
        """Return list of required data fields.

        Returns:
            List of required data field names

        Examples:
            >>> WorkoutHistoryTemplate.get_required_data()
            ['week_number', 'activities', 'wellness_data', ...]
        """
        return [
            "week_number",  # e.g., "S076"
            "start_date",  # ISO format: "2026-01-13"
            "end_date",  # ISO format: "2026-01-19"
            "tss_planned",  # Planned TSS for week
            "tss_realized",  # Actual TSS realized
            "activities",  # List of activity dicts from Intervals.icu
            "wellness_data",  # Wellness metrics (HRV, sleep, etc.)
            "learnings",  # Training intelligence learnings
            "metrics_evolution",  # Evolution metrics (start vs end)
        ]

    @staticmethod
    def get_structure() -> dict:
        """Return expected markdown structure.

        Returns:
            Dictionary defining report structure

        Examples:
            >>> structure = WorkoutHistoryTemplate.get_structure()
            >>> structure["sections"]
            ['Contexte Semaine', 'Chronologie Complète', ...]
        """
        return {
            "sections": [
                "Contexte Semaine",  # Week overview (TSS, objectives)
                "Chronologie Complète",  # 7 sessions detailed chronology
                "Métriques Évolution",  # Evolution metrics (start vs end)
                "Enseignements Majeurs",  # Key learnings (3-5 points)
                "Recommandations",  # Recommendations for next week
            ],
            "format": "markdown",
            "max_length": 2000,  # words
            "language": "fr",
            "style": "factual",  # Factual, data-driven, concise
        }

    @staticmethod
    def get_format_guidelines() -> dict:
        """Return formatting guidelines for AI generation.

        Returns:
            Dictionary with formatting rules

        Examples:
            >>> guidelines = WorkoutHistoryTemplate.get_format_guidelines()
            >>> guidelines["session_format"]
            'Durée | TSS | IF | RPE + métriques pré/post'
        """
        return {
            "session_format": "Durée | TSS | IF | RPE + métriques pré/post",
            "heading_levels": {
                "title": "# Workout History SXXX",
                "section": "## Section Name",
                "subsection": "### Subsection",
            },
            "metrics_format": "Table avec colonnes: Métrique | Début | Fin | Évolution",
            "lists": "Bullet points pour enseignements et recommandations",
            "tone": "Professional, factual, technical",
            "constraints": [
                "Use ONLY provided data (no hallucinations)",
                "All metrics must be verifiable",
                "Sessions in chronological order",
                "Max 2000 words total",
            ],
        }
