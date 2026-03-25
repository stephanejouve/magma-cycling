"""Training Intelligence data models — Enums and Dataclasses.

Extracted from training_intelligence.py for god class decomposition.

Metadata:
    Created: 2026-01-01
    Author: Cyclisme Training Logs Team
    Category: INTELLIGENCE
    Status: Production
    Priority: P1
    Version: 2.1.0
    Sprint: R4.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any


class AnalysisLevel(Enum):
    """Temporal level of training analysis.

    Attributes:
        DAILY: Post-session analysis
        WEEKLY: Week summary (6 markdown files)
        MONTHLY: Strategic trends.
    """

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ConfidenceLevel(Enum):
    """Confidence in a learning or pattern discovery.

    Confidence levels based on number of observations:
    - LOW: 1-2 observations
    - MEDIUM: 3-5 observations
    - HIGH: 6-10 observations
    - VALIDATED: 10+ observations, official protocol

    Progression: LOW -> MEDIUM -> HIGH -> VALIDATED.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VALIDATED = "validated"


@dataclass
class TrainingLearning:
    """A learning extracted from training data with progressive validation.

    Attributes:
        id: Unique identifier (category_timestamp)
        timestamp: When learning was discovered
        level: Analysis level where discovered (DAILY/WEEKLY/MONTHLY)
        category: Learning category (e.g. "sweet-spot", "hydration", "recovery")
        description: What was learned (concise, actionable)
        evidence: Supporting data points (session IDs + metrics)
        confidence: Confidence level based on observations count
        impact: Estimated impact (LOW/MEDIUM/HIGH)
        applied: Whether learning has been applied to protocols
        validated: Whether learning has reached VALIDATED status

    Example:
        >>> learning = TrainingLearning(
        ...     id="sweet-spot_1735689600",
        ...     timestamp=datetime.now(),
        ...     level=AnalysisLevel.DAILY,
        ...     category="sweet-spot",
        ...     description="88-90% FTP sustainable 2x10min",
        ...     evidence=["S024-04: 2x10@88% RPE 7, decouplage 5.2%"],
        ...     confidence=ConfidenceLevel.LOW,
        ...     impact="MEDIUM"
        ... )
    """

    id: str
    timestamp: datetime
    level: AnalysisLevel
    category: str
    description: str
    evidence: list[str]
    confidence: ConfidenceLevel
    impact: str  # LOW/MEDIUM/HIGH
    applied: bool = False
    validated: bool = False

    def promote_confidence(self) -> None:
        """Promote confidence level after additional validation.

        Transition rules:
        - LOW (1-2 obs) -> MEDIUM (3-5 obs)
        - MEDIUM (3-5 obs) -> HIGH (6-10 obs)
        - HIGH (6-10 obs) -> VALIDATED (10+ obs)

        Example:
            >>> learning = TrainingLearning(..., confidence=ConfidenceLevel.LOW)
            >>> learning.evidence.append("S024-06: 2x10@89% RPE 7")
            >>> learning.promote_confidence()
            >>> assert learning.confidence == ConfidenceLevel.MEDIUM
        """
        transitions = {
            ConfidenceLevel.LOW: ConfidenceLevel.MEDIUM,
            ConfidenceLevel.MEDIUM: ConfidenceLevel.HIGH,
            ConfidenceLevel.HIGH: ConfidenceLevel.VALIDATED,
        }
        if self.confidence in transitions:
            self.confidence = transitions[self.confidence]

            # Mark as validated if reached VALIDATED status
            if self.confidence == ConfidenceLevel.VALIDATED:
                self.validated = True


@dataclass
class Pattern:
    """Recurring pattern identified across multiple training sessions.

    Attributes:
        id: Unique identifier (pattern_name_timestamp)
        name: Pattern name (descriptive, snake_case)
        trigger_conditions: Conditions triggering pattern (Dict)
        observed_outcome: What happens when triggered
        frequency: Number of times pattern observed
        first_seen: Date first observed
        last_seen: Date last observed
        confidence: Confidence level based on frequency

    Example:
        >>> pattern = Pattern(
        ...     id="pattern_sleep_debt_vo2_failure_1735689600",
        ...     name="sleep_debt_vo2_failure",
        ...     trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        ...     observed_outcome="Unable to complete intervals, RPE 9+",
        ...     frequency=4,
        ...     first_seen=date(2026, 1, 5),
        ...     last_seen=date(2026, 1, 20),
        ...     confidence=ConfidenceLevel.MEDIUM
        ... )
    """

    id: str
    name: str
    trigger_conditions: dict[str, Any]
    observed_outcome: str
    frequency: int
    first_seen: date
    last_seen: date
    confidence: ConfidenceLevel

    def matches(self, conditions: dict[str, Any]) -> bool:
        """Check if current conditions match this pattern triggers.

        Args:
            conditions: Current session/day conditions

        Returns:
            True if pattern triggers match, False otherwise

        Example:
            >>> pattern = Pattern(
            ...     trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
            ...     ...
            ... )
            >>> pattern.matches({"sleep": 5.5, "workout_type": "VO2"})
            True
            >>> pattern.matches({"sleep": 7.0, "workout_type": "VO2"})
            False
        """
        for key, condition in self.trigger_conditions.items():
            if key not in conditions:
                return False

            value = conditions[key]

            # Handle string conditions (e.g. "<6h", "=VO2")
            if isinstance(condition, str):
                if condition.startswith("<"):
                    threshold = float(condition[1:].replace("h", ""))
                    if not (isinstance(value, int | float) and value < threshold):
                        return False
                elif condition.startswith(">"):
                    threshold = float(condition[1:].replace("h", ""))
                    if not (isinstance(value, int | float) and value > threshold):
                        return False
                elif condition.startswith("="):
                    expected = condition[1:]
                    if value != expected:
                        return False
                else:
                    # Exact match
                    if value != condition:
                        return False
            else:
                # Direct comparison
                if value != condition:
                    return False

        return True

    def promote_confidence(self) -> None:
        """Promote confidence based on frequency.

        Rules:
        - 1-2 observations -> LOW
        - 3-5 observations -> MEDIUM
        - 6-10 observations -> HIGH
        - 10+ observations -> VALIDATED.
        """
        if self.frequency >= 10:
            self.confidence = ConfidenceLevel.VALIDATED
        elif self.frequency >= 6:
            self.confidence = ConfidenceLevel.HIGH
        elif self.frequency >= 3:
            self.confidence = ConfidenceLevel.MEDIUM
        else:
            self.confidence = ConfidenceLevel.LOW


@dataclass
class ProtocolAdaptation:
    """Recommended adaptation to existing training protocol.

    Attributes:
        id: Unique identifier (protocol_type_timestamp)
        protocol_name: Name of protocol to adapt (e.g. "hydration", "vo2_veto")
        adaptation_type: Type of change (ADD/MODIFY/REMOVE)
        current_rule: Existing protocol rule
        proposed_rule: Proposed new rule
        justification: Why this adaptation is recommended
        evidence: Supporting data points
        confidence: Confidence based on evidence count
        status: Current status (PROPOSED/TESTED/VALIDATED/REJECTED)

    Example:
        >>> adaptation = ProtocolAdaptation(
        ...     id="vo2_veto_MODIFY_1735689600",
        ...     protocol_name="vo2_veto",
        ...     adaptation_type="MODIFY",
        ...     current_rule="Sleep < 6h -> VETO",
        ...     proposed_rule="Sleep < 6.5h -> VETO (master athlete)",
        ...     justification="6-6.5h sleep shows degraded performance",
        ...     evidence=["S024-05: 6.2h sleep, VO2 RPE 9 vs target 7-8"],
        ...     confidence=ConfidenceLevel.LOW,
        ...     status="PROPOSED"
        ... )
    """

    id: str
    protocol_name: str
    adaptation_type: str  # ADD/MODIFY/REMOVE
    current_rule: str
    proposed_rule: str
    justification: str
    evidence: list[str]
    confidence: ConfidenceLevel
    status: str  # PROPOSED/TESTED/VALIDATED/REJECTED
