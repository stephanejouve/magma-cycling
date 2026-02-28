"""
Planning module for training plans and calendar management.

This module provides tools for creating, managing, and syncing training plans
with Intervals.icu.

Modules:
    planning_manager: Core planning functionality (plans, deadlines, objectives)
    calendar: Training calendar with session management and TSS tracking
    intervals_sync: Bidirectional sync with Intervals.icu API.
"""

from magma_cycling.planning.calendar import (
    TrainingCalendar,
    TrainingSession,
    WeeklySummary,
    WorkoutType,
)
from magma_cycling.planning.intervals_sync import IntervalsSync, SyncStatus
from magma_cycling.planning.planning_manager import (
    PlanningManager,
    TrainingObjective,
    TrainingPlan,
)

__all__ = [
    "TrainingObjective",
    "TrainingPlan",
    "PlanningManager",
    "TrainingCalendar",
    "TrainingSession",
    "WeeklySummary",
    "WorkoutType",
    "IntervalsSync",
    "SyncStatus",
]
