"""
Planning module for training plans and calendar management.

This module provides tools for creating, managing, and syncing training plans
with Intervals.icu.

Modules:
    planning_manager: Core planning functionality (plans, deadlines, objectives)
    calendar: Training calendar with session management and TSS tracking
    intervals_sync: Bidirectional sync with Intervals.icu API.
"""

from cyclisme_training_logs.planning.calendar import (
    TrainingCalendar,
    TrainingSession,
    WeeklySummary,
    WorkoutType,
)
from cyclisme_training_logs.planning.intervals_sync import IntervalsSync, SyncStatus
from cyclisme_training_logs.planning.planning_manager import (
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
