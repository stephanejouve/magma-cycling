"""
Training Intelligence & Feedback Loop Module — Facade.

Maintains unified memory across temporal scales (daily/weekly/monthly) to:
- Accumulate learnings with progressive validation
- Detect recurring patterns automatically
- Propose evidence-based protocol adaptations
- Provide context-aware insights and recommendations

Metadata:
    Created: 2026-01-01
    Author: Cyclisme Training Logs Team
    Category: INTELLIGENCE
    Status: Production
    Priority: P1
    Version: 2.1.0
    Sprint: R4.
"""

from magma_cycling.intelligence.models import (
    AnalysisLevel,
    ConfidenceLevel,
    Pattern,
    ProtocolAdaptation,
    TrainingLearning,
)
from magma_cycling.intelligence.training.core import CoreMixin
from magma_cycling.intelligence.training.insights import InsightsMixin
from magma_cycling.intelligence.training.pid import PIDMixin
from magma_cycling.intelligence.training.storage import StorageMixin

# Re-export models for backward compatibility
__all__ = [
    "AnalysisLevel",
    "ConfidenceLevel",
    "TrainingLearning",
    "Pattern",
    "ProtocolAdaptation",
    "TrainingIntelligence",
]


class TrainingIntelligence(CoreMixin, InsightsMixin, PIDMixin, StorageMixin):
    """Central intelligence managing learnings, patterns, and protocol adaptations.

    Maintains unified memory across temporal scales (daily/weekly/monthly) to:
    - Accumulate learnings with progressive validation
    - Detect recurring patterns automatically
    - Propose evidence-based protocol adaptations
    - Provide context-aware insights and recommendations

    Attributes:
        learnings: Dict[str, TrainingLearning] - Indexed by learning.id
        patterns: Dict[str, Pattern] - Indexed by pattern.id
        adaptations: Dict[str, ProtocolAdaptation] - Indexed by adaptation.id

    Example:
        >>> intelligence = TrainingIntelligence()
        >>>
        >>> # Add learning from daily analysis
        >>> learning = intelligence.add_learning(
        ...     category="sweet-spot",
        ...     description="88-90% FTP sustainable 2x10min",
        ...     evidence=["S024-04: 2x10@88% RPE 7"],
        ...     level=AnalysisLevel.DAILY
        ... )
        >>>
        >>> # Get daily insights
        >>> insights = intelligence.get_daily_insights({
        ...     "workout_type": "sweet-spot",
        ...     "planned_intensity": 89
        ... })
        >>> print(insights["recommendations"])
        ["88-90% FTP validated (Confidence: MEDIUM, 3 observations)"]
    """

    def __init__(self) -> None:
        """Initialize TrainingIntelligence with empty memory stores."""
        self.learnings: dict[str, TrainingLearning] = {}
        self.patterns: dict[str, Pattern] = {}
        self.adaptations: dict[str, ProtocolAdaptation] = {}
