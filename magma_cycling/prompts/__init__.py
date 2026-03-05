"""AI coaching prompt assembly package.

Exports build_prompt() for all workflows.
"""

from magma_cycling.prompts.prompt_builder import (
    build_prompt,
    format_athlete_profile,
    load_current_metrics,
)

__all__ = ["build_prompt", "format_athlete_profile", "load_current_metrics"]
