"""Bilan Final AI Prompt Builder.

Constructs AI prompts for bilan_final report generation.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""

from typing import Any


def build_bilan_final_prompt(week_data: dict[str, Any]) -> str:
    """Build AI prompt for bilan_final report generation.

    Constructs synthesis-focused prompt including:
    - System instructions (synthesis role, strategic focus)
    - Week objectives vs realized
    - Workout history summary (input)
    - Protocol adaptations
    - Output format specification

    Args:
        week_data: Dictionary with all week data
            - week_number: str (e.g., "S076")
            - objectives: list[str] (planned objectives)
            - workout_history_summary: str (from workout_history report)
            - metrics_final: dict (final comparison metrics)
            - protocol_adaptations: list[dict] (protocol changes)

    Returns:
        Complete AI prompt string

    Raises:
        ValueError: If required data missing

    Examples:
        >>> week_data = {"week_number": "S076", "objectives": [...]}
        >>> prompt = build_bilan_final_prompt(week_data)
        >>> print(prompt[:100])
        You are a strategic cycling coach synthesizing weekly outcomes...
    """
    # Validate required data
    required_fields = [
        "week_number",
        "objectives",
        "workout_history_summary",
        "metrics_final",
    ]
    for field in required_fields:
        if field not in week_data:
            raise ValueError(f"Missing required field: {field}")

    # TODO: Implement full prompt construction
    # System instruction + Strategic context + Synthesis requirements

    raise NotImplementedError("Prompt construction not yet implemented")
