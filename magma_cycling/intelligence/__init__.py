"""
Intelligence Module - Training Intelligence & Feedback Loop.

Sprint R4 module for unified memory across temporal scales (daily/weekly/monthly).

Exports:
    Enums:
        - AnalysisLevel: Temporal level (DAILY/WEEKLY/MONTHLY)
        - ConfidenceLevel: Confidence level (LOW/MEDIUM/HIGH/VALIDATED)

    Dataclasses:
        - TrainingLearning: Learning with progressive validation
        - Pattern: Recurring pattern across sessions
        - ProtocolAdaptation: Recommended protocol adaptation

    Main Class:
        - TrainingIntelligence: Central intelligence manager

Metadata:
    Created: 2026-01-01
    Author: Cyclisme Training Logs Team
    Category: INTELLIGENCE
    Status: Production
    Priority: P1
    Version: 2.1.0
    Sprint: R4.
"""

from magma_cycling.intelligence.pid_controller import (
    PIDController,
    PIDState,
    compute_pid_gains_from_intelligence,
)
from magma_cycling.intelligence.training_intelligence import (
    AnalysisLevel,
    ConfidenceLevel,
    Pattern,
    ProtocolAdaptation,
    TrainingIntelligence,
    TrainingLearning,
)

__all__ = [
    # Enums
    "AnalysisLevel",
    "ConfidenceLevel",
    # Dataclasses
    "TrainingLearning",
    "Pattern",
    "ProtocolAdaptation",
    # Main Class
    "TrainingIntelligence",
    # PID Controller (Sprint R4++)
    "PIDController",
    "PIDState",
    "compute_pid_gains_from_intelligence",
]
