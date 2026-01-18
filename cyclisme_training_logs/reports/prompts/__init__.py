"""AI Prompts module.

Constructs AI prompts with context for report generation.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""

from cyclisme_training_logs.reports.prompts.bilan_final_prompt import (
    build_bilan_final_prompt,
)
from cyclisme_training_logs.reports.prompts.workout_history_prompt import (
    build_workout_history_prompt,
)

__all__ = ["build_workout_history_prompt", "build_bilan_final_prompt"]
