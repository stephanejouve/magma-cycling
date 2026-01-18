"""Bilan Final Report Template.

Defines structure for bilan_final_sXXX.md reports.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""


class BilanFinalTemplate:
    """Template for bilan_final_sXXX.md report.

    Defines the expected structure and required data fields for
    comprehensive weekly synthesis and final assessment reports.

    Attributes:
        REPORT_TYPE: Type identifier ("bilan_final")
        MAX_WORD_COUNT: Maximum words allowed (1500)
        LANGUAGE: Report language ("fr")
    """

    REPORT_TYPE = "bilan_final"
    MAX_WORD_COUNT = 1500
    LANGUAGE = "fr"

    @staticmethod
    def get_required_data() -> list[str]:
        """Return list of required data fields.

        Returns:
            List of required data field names

        Examples:
            >>> BilanFinalTemplate.get_required_data()
            ['week_number', 'objectives', 'workout_history_summary', ...]
        """
        return [
            "week_number",  # e.g., "S076"
            "objectives",  # Week objectives (planned)
            "workout_history_summary",  # Summary from workout_history report
            "metrics_final",  # Final metrics comparison
            "protocol_adaptations",  # Training intelligence protocol changes
            "key_sessions",  # Critical sessions (successes/failures)
            "behavioral_learnings",  # Behavioral insights
        ]

    @staticmethod
    def get_structure() -> dict:
        """Return expected markdown structure.

        Returns:
            Dictionary defining report structure

        Examples:
            >>> structure = BilanFinalTemplate.get_structure()
            >>> structure["sections"]
            ['Objectifs vs Réalisé', 'Métriques Finales', ...]
        """
        return {
            "sections": [
                "Objectifs vs Réalisé",  # Objectives planned vs realized
                "Métriques Finales",  # Final metrics comparison
                "Découvertes Majeures",  # Major discoveries (max 3-4)
                "Séances Clés",  # Key sessions analyzed
                "Protocoles Établis/Validés",  # Protocols established/validated
                "Ajustements Recommandés",  # Adjustments for next cycle
                "Enseignements Comportementaux",  # Behavioral learnings
                "Conclusion",  # Synthesis conclusion (2-3 sentences)
            ],
            "format": "markdown",
            "max_length": 1500,  # words
            "language": "fr",
            "style": "synthesis",  # Synthetic, strategic, actionable
        }

    @staticmethod
    def get_format_guidelines() -> dict:
        """Return formatting guidelines for AI generation.

        Returns:
            Dictionary with formatting rules

        Examples:
            >>> guidelines = BilanFinalTemplate.get_format_guidelines()
            >>> guidelines["discoveries_max"]
            4
        """
        return {
            "heading_levels": {
                "title": "# Bilan Final SXXX",
                "section": "## Section Name",
                "subsection": "### Subsection",
            },
            "discoveries_max": 4,  # Max 3-4 major discoveries
            "conclusion_sentences": 3,  # Max 2-3 sentences
            "tone": "Strategic, synthesis-focused, actionable",
            "constraints": [
                "Focus on high-level insights (not session details)",
                "Maximum 3-4 major discoveries",
                "All claims must reference workout_history data",
                "Conclusion must be concise (2-3 sentences)",
                "Max 1500 words total",
            ],
        }
