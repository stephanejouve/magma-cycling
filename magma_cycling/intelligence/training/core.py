"""CoreMixin — CRUD operations for learnings, patterns, and adaptations."""

from datetime import date, datetime
from typing import Any

from magma_cycling.intelligence.models import (
    AnalysisLevel,
    ConfidenceLevel,
    Pattern,
    ProtocolAdaptation,
    TrainingLearning,
)


class CoreMixin:
    """CRUD operations for the three intelligence stores."""

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
            # Update existing learning (deduplicate evidence)
            learning = self.learnings[existing_id]
            existing_evidence = set(learning.evidence)
            learning.evidence.extend(e for e in evidence if e not in existing_evidence)

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
            ...     current_rule="Sleep < 6h -> VETO",
            ...     proposed_rule="Sleep < 6.5h -> VETO",
            ...     justification="Master athlete requires more sleep",
            ...     evidence=["S024-05: 6.2h sleep, VO2 RPE 9"]
            ... )
        """
        # Upsert: find existing PROPOSED adaptation with same key
        existing_id = None
        for aid, adapt in self.adaptations.items():
            if (
                adapt.protocol_name == protocol_name
                and adapt.adaptation_type == adaptation_type
                and adapt.status == "PROPOSED"
            ):
                existing_id = aid
                break

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

        if existing_id:
            # Update existing adaptation in place
            adaptation = self.adaptations[existing_id]
            adaptation.current_rule = current_rule
            adaptation.proposed_rule = proposed_rule
            adaptation.justification = justification
            adaptation.evidence = evidence
            adaptation.confidence = confidence
            return adaptation

        # Create new adaptation (ensure unique ID)
        timestamp = int(datetime.now().timestamp())
        adaptation_id = f"{protocol_name}_{adaptation_type}_{timestamp}"
        if adaptation_id in self.adaptations:
            adaptation_id = f"{protocol_name}_{adaptation_type}_{timestamp}_1"

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

    def expire_stale_adaptations(self, max_age_days: int = 14) -> int:
        """Expire PROPOSED adaptations older than max_age_days.

        Extracts timestamp from adaptation ID (format: protocol_type_TIMESTAMP)
        and marks as EXPIRED if older than max_age_days.

        Args:
            max_age_days: Maximum age in days before expiration (default: 14)

        Returns:
            Number of adaptations expired
        """
        now = datetime.now()
        expired_count = 0

        for adaptation in self.adaptations.values():
            if adaptation.status != "PROPOSED":
                continue

            # Extract timestamp from ID (last segment after last '_')
            try:
                ts_str = adaptation.id.rsplit("_", 1)[-1]
                ts = datetime.fromtimestamp(int(ts_str))
                age_days = (now - ts).total_seconds() / 86400
                if age_days > max_age_days:
                    adaptation.status = "EXPIRED"
                    expired_count += 1
            except (ValueError, IndexError, OSError):
                continue

        return expired_count
