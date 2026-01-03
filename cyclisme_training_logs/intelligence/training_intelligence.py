"""
Training Intelligence & Feedback Loop Module.

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
    Sprint: R4
"""

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class AnalysisLevel(Enum):
    """Temporal level of training analysis.

    Attributes:
        DAILY: Post-session analysis
        WEEKLY: Week summary (6 markdown files)
        MONTHLY: Strategic trends
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

    Progression: LOW → MEDIUM → HIGH → VALIDATED
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
        ...     evidence=["S024-04: 2x10@88% RPE 7, découplage 5.2%"],
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
        - LOW (1-2 obs) → MEDIUM (3-5 obs)
        - MEDIUM (3-5 obs) → HIGH (6-10 obs)
        - HIGH (6-10 obs) → VALIDATED (10+ obs)

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
        - 1-2 observations → LOW
        - 3-5 observations → MEDIUM
        - 6-10 observations → HIGH
        - 10+ observations → VALIDATED
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
        ...     current_rule="Sleep < 6h → VETO",
        ...     proposed_rule="Sleep < 6.5h → VETO (master athlete)",
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


class TrainingIntelligence:
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

    def add_learning(
        self,
        category: str,
        description: str,
        evidence: list[str],
        level: AnalysisLevel,
        impact: str = "MEDIUM",
        confidence: ConfidenceLevel | None = None,
    ) -> TrainingLearning:
        """Add new learning or update existing one.

        Args:
            category: Learning category (e.g. "sweet-spot", "hydration")
            description: What was learned (concise, actionable)
            evidence: Supporting data points (session IDs + metrics)
            level: Analysis level where discovered
            impact: Estimated impact (LOW/MEDIUM/HIGH)
            confidence: Override confidence level (auto-computed if None)

        Returns:
            TrainingLearning: Created or updated learning

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> learning = intelligence.add_learning(
            ...     category="sweet-spot",
            ...     description="88-90% FTP sustainable 2x10min",
            ...     evidence=["S024-04: 2x10@88% RPE 7"],
            ...     level=AnalysisLevel.DAILY
            ... )
            >>> assert learning.confidence == ConfidenceLevel.LOW
        """
        # Check if learning already exists for this category
        existing_id = None
        for learning_id, learning in self.learnings.items():
            if learning.category == category and learning.description == description:
                existing_id = learning_id
                break

        if existing_id:
            # Update existing learning
            learning = self.learnings[existing_id]
            learning.evidence.extend(evidence)

            # Auto-promote confidence based on evidence count
            evidence_count = len(learning.evidence)
            if evidence_count >= 10:
                learning.confidence = ConfidenceLevel.VALIDATED
                learning.validated = True
            elif evidence_count >= 6:
                learning.confidence = ConfidenceLevel.HIGH
            elif evidence_count >= 3:
                learning.confidence = ConfidenceLevel.MEDIUM
            else:
                learning.confidence = ConfidenceLevel.LOW

            return learning
        else:
            # Create new learning
            timestamp = datetime.now()
            learning_id = f"{category}_{int(timestamp.timestamp())}"

            # Determine confidence from evidence count
            if confidence is None:
                evidence_count = len(evidence)
                if evidence_count >= 10:
                    confidence = ConfidenceLevel.VALIDATED
                elif evidence_count >= 6:
                    confidence = ConfidenceLevel.HIGH
                elif evidence_count >= 3:
                    confidence = ConfidenceLevel.MEDIUM
                else:
                    confidence = ConfidenceLevel.LOW

            learning = TrainingLearning(
                id=learning_id,
                timestamp=timestamp,
                level=level,
                category=category,
                description=description,
                evidence=evidence,
                confidence=confidence,
                impact=impact,
                validated=(confidence == ConfidenceLevel.VALIDATED),
            )

            self.learnings[learning_id] = learning
            return learning

    def identify_pattern(
        self,
        name: str,
        trigger_conditions: dict[str, Any],
        observed_outcome: str,
        observation_date: date,
    ) -> Pattern:
        """Identify or update recurring pattern.

        Args:
            name: Pattern name (descriptive, snake_case)
            trigger_conditions: Conditions triggering pattern
            observed_outcome: What happens when triggered
            observation_date: Date of this observation

        Returns:
            Pattern: Created or updated pattern

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> pattern = intelligence.identify_pattern(
            ...     name="sleep_debt_vo2_failure",
            ...     trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
            ...     observed_outcome="Unable to complete intervals, RPE 9+",
            ...     observation_date=date(2026, 1, 5)
            ... )
            >>> assert pattern.frequency == 1
        """
        # Check if pattern already exists
        existing_id = None
        for pattern_id, pattern in self.patterns.items():
            if pattern.name == name:
                existing_id = pattern_id
                break

        if existing_id:
            # Update existing pattern
            pattern = self.patterns[existing_id]
            pattern.frequency += 1
            pattern.last_seen = observation_date
            pattern.promote_confidence()
            return pattern
        else:
            # Create new pattern
            timestamp = int(datetime.now().timestamp())
            pattern_id = f"pattern_{name}_{timestamp}"

            pattern = Pattern(
                id=pattern_id,
                name=name,
                trigger_conditions=trigger_conditions,
                observed_outcome=observed_outcome,
                frequency=1,
                first_seen=observation_date,
                last_seen=observation_date,
                confidence=ConfidenceLevel.LOW,
            )

            self.patterns[pattern_id] = pattern
            return pattern

    def propose_adaptation(
        self,
        protocol_name: str,
        adaptation_type: str,
        current_rule: str,
        proposed_rule: str,
        justification: str,
        evidence: list[str],
    ) -> ProtocolAdaptation:
        """Propose protocol adaptation based on evidence.

        Args:
            protocol_name: Name of protocol to adapt
            adaptation_type: Type of change (ADD/MODIFY/REMOVE)
            current_rule: Existing protocol rule
            proposed_rule: Proposed new rule
            justification: Why this adaptation is recommended
            evidence: Supporting data points

        Returns:
            ProtocolAdaptation: Created adaptation proposal

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> adaptation = intelligence.propose_adaptation(
            ...     protocol_name="vo2_veto",
            ...     adaptation_type="MODIFY",
            ...     current_rule="Sleep < 6h → VETO",
            ...     proposed_rule="Sleep < 6.5h → VETO",
            ...     justification="Master athlete requires more sleep",
            ...     evidence=["S024-05: 6.2h sleep, VO2 RPE 9"]
            ... )
        """
        timestamp = int(datetime.now().timestamp())
        adaptation_id = f"{protocol_name}_{adaptation_type}_{timestamp}"

        # Determine confidence from evidence count
        evidence_count = len(evidence)
        if evidence_count >= 10:
            confidence = ConfidenceLevel.VALIDATED
        elif evidence_count >= 6:
            confidence = ConfidenceLevel.HIGH
        elif evidence_count >= 3:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        adaptation = ProtocolAdaptation(
            id=adaptation_id,
            protocol_name=protocol_name,
            adaptation_type=adaptation_type,
            current_rule=current_rule,
            proposed_rule=proposed_rule,
            justification=justification,
            evidence=evidence,
            confidence=confidence,
            status="PROPOSED",
        )

        self.adaptations[adaptation_id] = adaptation
        return adaptation

    def get_daily_insights(self, context: dict[str, Any]) -> dict[str, Any]:
        """Get daily insights based on current context and accumulated intelligence.

        Args:
            context: Current session/day context (workout_type, intensity, etc.)

        Returns:
            Dict with keys:
                - relevant_learnings: List[TrainingLearning]
                - active_patterns: List[Pattern] (matching current conditions)
                - recommendations: List[str]

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> insights = intelligence.get_daily_insights({
            ...     "workout_type": "sweet-spot",
            ...     "planned_intensity": 89
            ... })
        """
        relevant_learnings = []
        active_patterns = []
        recommendations = []

        # Find relevant learnings
        workout_type = context.get("workout_type", "")
        for learning in self.learnings.values():
            if workout_type.lower() in learning.category.lower():
                relevant_learnings.append(learning)

                # Generate recommendation
                conf_str = learning.confidence.value.upper()
                evidence_count = len(learning.evidence)
                rec = f"{learning.description} (Confidence: {conf_str}, {evidence_count} observations)"
                recommendations.append(rec)

        # Find matching patterns
        for pattern in self.patterns.values():
            if pattern.matches(context):
                active_patterns.append(pattern)

                # Add warning recommendation
                warning = f"⚠️ Pattern detected: {pattern.name} - {pattern.observed_outcome}"
                recommendations.append(warning)

        return {
            "relevant_learnings": relevant_learnings,
            "active_patterns": active_patterns,
            "recommendations": recommendations,
        }

    def get_weekly_synthesis(self, week_number: int) -> dict[str, Any]:
        """Get weekly synthesis of intelligence state.

        Args:
            week_number: ISO week number

        Returns:
            Dict with keys:
                - total_learnings: int
                - high_confidence_learnings: List[TrainingLearning]
                - active_patterns: List[Pattern]
                - pending_adaptations: List[ProtocolAdaptation]

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> synthesis = intelligence.get_weekly_synthesis(week_num=2)
        """
        high_confidence_learnings = [
            learning
            for learning in self.learnings.values()
            if learning.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VALIDATED]
        ]

        active_patterns = [
            pattern
            for pattern in self.patterns.values()
            if pattern.confidence
            in [ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH, ConfidenceLevel.VALIDATED]
        ]

        pending_adaptations = [
            adaptation
            for adaptation in self.adaptations.values()
            if adaptation.status == "PROPOSED"
        ]

        return {
            "total_learnings": len(self.learnings),
            "high_confidence_learnings": high_confidence_learnings,
            "active_patterns": active_patterns,
            "pending_adaptations": pending_adaptations,
        }

    def get_monthly_trends(self, month: int, year: int) -> dict[str, Any]:
        """Get monthly trends analysis.

        Args:
            month: Month number (1-12)
            year: Year

        Returns:
            Dict with keys:
                - validated_learnings: List[TrainingLearning]
                - top_patterns: List[Pattern] (sorted by frequency)
                - validated_adaptations: List[ProtocolAdaptation]

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> trends = intelligence.get_monthly_trends(month=1, year=2026)
        """
        validated_learnings = [
            learning for learning in self.learnings.values() if learning.validated
        ]

        # Sort patterns by frequency
        top_patterns = sorted(self.patterns.values(), key=lambda p: p.frequency, reverse=True)[
            :10
        ]  # Top 10 patterns

        validated_adaptations = [
            adaptation
            for adaptation in self.adaptations.values()
            if adaptation.status == "VALIDATED"
        ]

        return {
            "validated_learnings": validated_learnings,
            "top_patterns": top_patterns,
            "validated_adaptations": validated_adaptations,
        }

    def get_pid_correction(
        self, current_ftp: float, target_ftp: float, dt: float = 1.0
    ) -> dict[str, Any]:
        """
        Obtenir correction PID automatique pour progression FTP.

        Calcule gains PID adaptatifs depuis intelligence accumulée,
        puis compute correction TSS recommandée.

        Args:
            current_ftp: FTP actuelle (W)
            target_ftp: FTP cible (W)
            dt: Delta temps depuis dernière correction (semaines, défaut 1.0)

        Returns:
            Dict with keys:
                - correction: Dict from PIDController.compute()
                - recommendation: str action suggérée (français)
                - gains: {"kp": float, "ki": float, "kd": float}

        Example:
            >>> intelligence = TrainingIntelligence.load_from_file(Path("intelligence.json"))
            >>> result = intelligence.get_pid_correction(
            ...     current_ftp=220,
            ...     target_ftp=260,
            ...     dt=1.0
            ... )
            >>> print(result["recommendation"])
            Augmenter TSS +25/semaine - Focus Sweet-Spot 88-90% FTP
        """
        from cyclisme_training_logs.intelligence.pid_controller import (
            PIDController,
            compute_pid_gains_from_intelligence,
        )

        # Calculate gains from current intelligence
        gains = compute_pid_gains_from_intelligence(self)

        # Initialize PID controller
        pid = PIDController(kp=gains["kp"], ki=gains["ki"], kd=gains["kd"], setpoint=target_ftp)

        # Compute correction
        correction = pid.compute(current_ftp, dt)
        recommendation = pid.get_action_recommendation(correction)

        return {"correction": correction, "recommendation": recommendation, "gains": gains}

    def save_to_file(self, file_path: Path) -> None:
        """Save intelligence state to JSON file.

        Args:
            file_path: Path to save file (in-memory, no hardcoded paths)

        Example:
            >>> intelligence = TrainingIntelligence()
            >>> from pathlib import Path
            >>> intelligence.save_to_file(Path("/tmp/intelligence_state.json"))
        """

        def serialize_obj(obj: Any) -> Any:
            """Serialize dataclass objects to dict."""
            if isinstance(obj, TrainingLearning | Pattern | ProtocolAdaptation):
                data = asdict(obj)
                # Convert enums to strings
                if "level" in data and isinstance(data["level"], AnalysisLevel):
                    data["level"] = data["level"].value
                if "confidence" in data and isinstance(data["confidence"], ConfidenceLevel):
                    data["confidence"] = data["confidence"].value
                # Convert datetime/date to ISO format
                if "timestamp" in data and isinstance(data["timestamp"], datetime):
                    data["timestamp"] = data["timestamp"].isoformat()
                if "first_seen" in data and isinstance(data["first_seen"], date):
                    data["first_seen"] = data["first_seen"].isoformat()
                if "last_seen" in data and isinstance(data["last_seen"], date):
                    data["last_seen"] = data["last_seen"].isoformat()
                return data
            return obj

        state = {
            "learnings": {lid: serialize_obj(lrn) for lid, lrn in self.learnings.items()},
            "patterns": {pid: serialize_obj(p) for pid, p in self.patterns.items()},
            "adaptations": {aid: serialize_obj(a) for aid, a in self.adaptations.items()},
        }

        with open(file_path, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, file_path: Path) -> "TrainingIntelligence":
        """Load intelligence state from JSON file.

        Args:
            file_path: Path to load file (in-memory, no hardcoded paths)

        Returns:
            TrainingIntelligence: Loaded instance

        Example:
            >>> from pathlib import Path
            >>> intelligence = TrainingIntelligence.load_from_file(
            ...     Path("/tmp/intelligence_state.json")
            ... )
        """
        with open(file_path) as f:
            state = json.load(f)

        intelligence = cls()

        # Load learnings
        for learning_id, learning_data in state.get("learnings", {}).items():
            learning_data["level"] = AnalysisLevel(learning_data["level"])
            learning_data["confidence"] = ConfidenceLevel(learning_data["confidence"])
            learning_data["timestamp"] = datetime.fromisoformat(learning_data["timestamp"])
            intelligence.learnings[learning_id] = TrainingLearning(**learning_data)

        # Load patterns
        for pattern_id, pattern_data in state.get("patterns", {}).items():
            pattern_data["confidence"] = ConfidenceLevel(pattern_data["confidence"])
            pattern_data["first_seen"] = date.fromisoformat(pattern_data["first_seen"])
            pattern_data["last_seen"] = date.fromisoformat(pattern_data["last_seen"])
            intelligence.patterns[pattern_id] = Pattern(**pattern_data)

        # Load adaptations
        for adaptation_id, adaptation_data in state.get("adaptations", {}).items():
            adaptation_data["confidence"] = ConfidenceLevel(adaptation_data["confidence"])
            intelligence.adaptations[adaptation_id] = ProtocolAdaptation(**adaptation_data)

        return intelligence
