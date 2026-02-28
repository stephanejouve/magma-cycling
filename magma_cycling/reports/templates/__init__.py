"""Report templates module.

Defines structure and requirements for each report type.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""

from magma_cycling.reports.templates.bilan_final import BilanFinalTemplate
from magma_cycling.reports.templates.workout_history import (
    WorkoutHistoryTemplate,
)

__all__ = ["WorkoutHistoryTemplate", "BilanFinalTemplate"]
