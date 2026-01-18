"""Workout History AI Prompt Builder.

Constructs AI prompts for workout_history report generation.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""

from typing import Any


def build_workout_history_prompt(week_data: dict[str, Any]) -> str:
    """Build AI prompt for workout_history report generation.

    Constructs comprehensive prompt including:
    - System instructions (role, style, constraints)
    - Week context (TSS, activities, wellness)
    - Training intelligence (learnings, patterns)
    - Output format specification
    - Example report structure (few-shot learning)

    Args:
        week_data: Dictionary with all week data
            - week_number: str (e.g., "S076")
            - activities: list[dict] (Intervals.icu activities)
            - wellness_data: dict (HRV, sleep, etc.)
            - learnings: list[dict] (Training intelligence)
            - metrics_evolution: dict (start vs end metrics)

    Returns:
        Complete AI prompt string

    Raises:
        ValueError: If required data missing

    Examples:
        >>> week_data = {"week_number": "S076", "activities": [...]}
        >>> prompt = build_workout_history_prompt(week_data)
        >>> print(prompt[:100])
        You are an expert cycling coach analyzing training data...
    """
    # Validate required data
    required_fields = [
        "week_number",
        "activities",
        "wellness_data",
        "learnings",
        "metrics_evolution",
    ]
    for field in required_fields:
        if field not in week_data:
            raise ValueError(f"Missing required field: {field}")

    # TODO: Implement full prompt construction
    # System instruction + User context + Format spec + Examples

    raise NotImplementedError("Prompt construction not yet implemented")
