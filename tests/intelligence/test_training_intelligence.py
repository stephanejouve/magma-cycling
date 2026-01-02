"""
Tests for Training Intelligence module (Sprint R4).

Tests cover:
- Dataclasses (TrainingLearning, Pattern, ProtocolAdaptation)
- Core methods (add_learning, identify_pattern, propose_adaptation)
- Multi-temporal insights (daily, weekly, monthly)
- Persistence (save/load JSON)

Metadata:
    Created: 2026-01-01
    Author: Cyclisme Training Logs Team
    Category: TESTS
    Status: Production
    Priority: P1
    Version: 2.1.0
    Sprint: R4
"""

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from cyclisme_training_logs.intelligence.training_intelligence import (
    AnalysisLevel,
    ConfidenceLevel,
    Pattern,
    ProtocolAdaptation,
    TrainingIntelligence,
    TrainingLearning,
)


# ============================================================================
# TESTS DATACLASSES (3)
# ============================================================================


def test_training_learning_promote_confidence():
    """Test confidence progression LOW→MEDIUM→HIGH→VALIDATED."""
    learning = TrainingLearning(
        id="test_123",
        timestamp=datetime.now(),
        level=AnalysisLevel.DAILY,
        category="test",
        description="Test learning",
        evidence=["Evidence 1"],
        confidence=ConfidenceLevel.LOW,
        impact="MEDIUM"
    )

    assert learning.confidence == ConfidenceLevel.LOW
    assert learning.validated is False

    learning.promote_confidence()
    assert learning.confidence == ConfidenceLevel.MEDIUM
    assert learning.validated is False

    learning.promote_confidence()
    assert learning.confidence == ConfidenceLevel.HIGH
    assert learning.validated is False

    learning.promote_confidence()
    assert learning.confidence == ConfidenceLevel.VALIDATED
    assert learning.validated is True


def test_pattern_matches_conditions():
    """Test pattern matching with various condition operators."""
    pattern = Pattern(
        id="test_pattern",
        name="test",
        trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        observed_outcome="Failure",
        frequency=1,
        first_seen=date.today(),
        last_seen=date.today(),
        confidence=ConfidenceLevel.LOW
    )

    # Should match
    assert pattern.matches({"sleep": 5.5, "workout_type": "VO2"}) is True

    # Should not match (sleep >= 6)
    assert pattern.matches({"sleep": 6.5, "workout_type": "VO2"}) is False

    # Should not match (wrong workout_type)
    assert pattern.matches({"sleep": 5.5, "workout_type": "Endurance"}) is False

    # Should not match (missing condition key)
    assert pattern.matches({"sleep": 5.5}) is False


def test_protocol_adaptation_creation():
    """Test ProtocolAdaptation initialization."""
    adaptation = ProtocolAdaptation(
        id="test_adaptation",
        protocol_name="test_protocol",
        adaptation_type="MODIFY",
        current_rule="Old rule",
        proposed_rule="New rule",
        justification="Better performance",
        evidence=["Evidence 1", "Evidence 2"],
        confidence=ConfidenceLevel.MEDIUM,
        status="PROPOSED"
    )

    assert adaptation.protocol_name == "test_protocol"
    assert adaptation.adaptation_type == "MODIFY"
    assert adaptation.status == "PROPOSED"
    assert len(adaptation.evidence) == 2
    assert adaptation.confidence == ConfidenceLevel.MEDIUM


# ============================================================================
# TESTS ADD_LEARNING (3)
# ============================================================================


def test_add_learning_new():
    """Test adding new learning creates LOW confidence."""
    intelligence = TrainingIntelligence()

    learning = intelligence.add_learning(
        category="sweet-spot",
        description="88% FTP sustainable",
        evidence=["S024-04: Success"],
        level=AnalysisLevel.DAILY,
        impact="MEDIUM"
    )

    assert learning.confidence == ConfidenceLevel.LOW
    assert len(learning.evidence) == 1
    assert len(intelligence.learnings) == 1
    assert learning.category == "sweet-spot"
    assert learning.level == AnalysisLevel.DAILY


def test_add_learning_reinforce_similar():
    """Test adding similar learning reinforces existing."""
    intelligence = TrainingIntelligence()

    # First learning
    learning1 = intelligence.add_learning(
        category="sweet-spot",
        description="88% FTP sustainable",
        evidence=["S024-04: Success"],
        level=AnalysisLevel.DAILY
    )
    assert learning1.confidence == ConfidenceLevel.LOW

    # Similar learning (should reinforce)
    learning2 = intelligence.add_learning(
        category="sweet-spot",
        description="88% FTP sustainable",  # Exact match
        evidence=["S024-06: Success"],
        level=AnalysisLevel.DAILY
    )

    # Should be same learning, reinforced
    assert learning1.id == learning2.id
    assert len(learning2.evidence) == 2
    assert learning2.confidence == ConfidenceLevel.LOW  # Still LOW (need 3 for MEDIUM)
    assert len(intelligence.learnings) == 1  # Still only 1 learning

    # Add third evidence to reach MEDIUM
    learning3 = intelligence.add_learning(
        category="sweet-spot",
        description="88% FTP sustainable",
        evidence=["S024-08: Success"],
        level=AnalysisLevel.DAILY
    )
    assert len(learning3.evidence) == 3
    assert learning3.confidence == ConfidenceLevel.MEDIUM


def test_add_learning_different_creates_new():
    """Test adding different learning creates separate entry."""
    intelligence = TrainingIntelligence()

    learning1 = intelligence.add_learning(
        category="sweet-spot",
        description="88% FTP sustainable",
        evidence=["Evidence 1"],
        level=AnalysisLevel.DAILY
    )

    learning2 = intelligence.add_learning(
        category="hydration",  # Different category
        description="500ml/h optimal",
        evidence=["Evidence 2"],
        level=AnalysisLevel.DAILY
    )

    assert learning1.id != learning2.id
    assert len(intelligence.learnings) == 2
    assert learning1.category == "sweet-spot"
    assert learning2.category == "hydration"


# ============================================================================
# TESTS IDENTIFY_PATTERN (3)
# ============================================================================


def test_identify_pattern_new():
    """Test identifying new pattern creates frequency 1."""
    intelligence = TrainingIntelligence()

    pattern = intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        observed_outcome="Failure",
        observation_date=date.today()
    )

    assert pattern.frequency == 1
    assert pattern.confidence == ConfidenceLevel.LOW
    assert pattern.first_seen == date.today()
    assert pattern.last_seen == date.today()
    assert len(intelligence.patterns) == 1


def test_identify_pattern_update_existing():
    """Test identifying existing pattern increments frequency."""
    intelligence = TrainingIntelligence()

    # First observation
    pattern1 = intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h"},
        observed_outcome="Failure",
        observation_date=date(2026, 1, 1)
    )
    assert pattern1.frequency == 1

    # Second observation (same name)
    pattern2 = intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h"},
        observed_outcome="Failure",
        observation_date=date(2026, 1, 2)
    )

    assert pattern1.id == pattern2.id
    assert pattern2.frequency == 2
    assert pattern2.last_seen == date(2026, 1, 2)
    assert len(intelligence.patterns) == 1


def test_pattern_confidence_progression_by_frequency():
    """Test pattern confidence increases with frequency."""
    intelligence = TrainingIntelligence()

    pattern = intelligence.identify_pattern(
        name="test_pattern",
        trigger_conditions={"test": "value"},
        observed_outcome="Outcome",
        observation_date=date.today()
    )

    # Frequency 1 → LOW
    assert pattern.confidence == ConfidenceLevel.LOW

    # Simulate 2 more observations → MEDIUM (frequency 3)
    for _ in range(2):
        pattern = intelligence.identify_pattern(
            name="test_pattern",
            trigger_conditions={"test": "value"},
            observed_outcome="Outcome",
            observation_date=date.today()
        )
    assert pattern.frequency == 3
    assert pattern.confidence == ConfidenceLevel.MEDIUM

    # Simulate 3 more observations → HIGH (frequency 6)
    for _ in range(3):
        pattern = intelligence.identify_pattern(
            name="test_pattern",
            trigger_conditions={"test": "value"},
            observed_outcome="Outcome",
            observation_date=date.today()
        )
    assert pattern.frequency == 6
    assert pattern.confidence == ConfidenceLevel.HIGH

    # Simulate 4 more observations → VALIDATED (frequency 10)
    for _ in range(4):
        pattern = intelligence.identify_pattern(
            name="test_pattern",
            trigger_conditions={"test": "value"},
            observed_outcome="Outcome",
            observation_date=date.today()
        )
    assert pattern.frequency == 10
    assert pattern.confidence == ConfidenceLevel.VALIDATED


# ============================================================================
# TESTS PROPOSE_ADAPTATION (3)
# ============================================================================


def test_propose_adaptation_confidence_by_evidence():
    """Test adaptation confidence based on evidence count."""
    intelligence = TrainingIntelligence()

    # 1-2 evidence → LOW
    adaptation1 = intelligence.propose_adaptation(
        protocol_name="test",
        adaptation_type="MODIFY",
        current_rule="Old",
        proposed_rule="New",
        justification="Better",
        evidence=["E1"]
    )
    assert adaptation1.confidence == ConfidenceLevel.LOW

    # 3-5 evidence → MEDIUM
    adaptation2 = intelligence.propose_adaptation(
        protocol_name="test2",
        adaptation_type="ADD",
        current_rule="None",
        proposed_rule="New rule",
        justification="Needed",
        evidence=["E1", "E2", "E3"]
    )
    assert adaptation2.confidence == ConfidenceLevel.MEDIUM

    # 6+ evidence → HIGH
    adaptation3 = intelligence.propose_adaptation(
        protocol_name="test3",
        adaptation_type="REMOVE",
        current_rule="Old rule",
        proposed_rule="None",
        justification="Obsolete",
        evidence=["E1", "E2", "E3", "E4", "E5", "E6"]
    )
    assert adaptation3.confidence == ConfidenceLevel.HIGH

    # 10+ evidence → VALIDATED
    adaptation4 = intelligence.propose_adaptation(
        protocol_name="test4",
        adaptation_type="MODIFY",
        current_rule="Old",
        proposed_rule="New",
        justification="Proven",
        evidence=["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10"]
    )
    assert adaptation4.confidence == ConfidenceLevel.VALIDATED


def test_propose_adaptation_status_proposed():
    """Test new adaptations always have status PROPOSED."""
    intelligence = TrainingIntelligence()

    adaptation = intelligence.propose_adaptation(
        protocol_name="test",
        adaptation_type="MODIFY",
        current_rule="Old",
        proposed_rule="New",
        justification="Better",
        evidence=["E1", "E2", "E3"]
    )

    assert adaptation.status == "PROPOSED"
    assert len(intelligence.adaptations) == 1


def test_propose_adaptation_types():
    """Test all adaptation types (ADD/MODIFY/REMOVE)."""
    intelligence = TrainingIntelligence()

    add = intelligence.propose_adaptation(
        protocol_name="test1",
        adaptation_type="ADD",
        current_rule="None",
        proposed_rule="New",
        justification="Needed",
        evidence=["E1"]
    )
    assert add.adaptation_type == "ADD"

    modify = intelligence.propose_adaptation(
        protocol_name="test2",
        adaptation_type="MODIFY",
        current_rule="Old",
        proposed_rule="New",
        justification="Better",
        evidence=["E1"]
    )
    assert modify.adaptation_type == "MODIFY"

    remove = intelligence.propose_adaptation(
        protocol_name="test3",
        adaptation_type="REMOVE",
        current_rule="Old",
        proposed_rule="None",
        justification="Obsolete",
        evidence=["E1"]
    )
    assert remove.adaptation_type == "REMOVE"

    assert len(intelligence.adaptations) == 3


# ============================================================================
# TESTS MULTI-TEMPORAL INSIGHTS (4)
# ============================================================================


def test_get_daily_insights_pattern_matching():
    """Test daily insights match patterns and warn."""
    intelligence = TrainingIntelligence()

    # Add pattern
    intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        observed_outcome="Failure",
        observation_date=date.today()
    )

    # Get insights with matching conditions
    insights = intelligence.get_daily_insights({
        "sleep": 5.5,
        "workout_type": "VO2"
    })

    assert len(insights["active_patterns"]) == 1
    assert len(insights["recommendations"]) == 1
    assert "sleep_debt_vo2_failure" in insights["recommendations"][0]
    assert "⚠️" in insights["recommendations"][0]


def test_get_daily_insights_relevant_learnings():
    """Test daily insights return relevant validated learnings."""
    intelligence = TrainingIntelligence()

    # Add learning with HIGH confidence
    learning = intelligence.add_learning(
        category="sweet-spot",
        description="88-90% FTP optimal",
        evidence=["E1", "E2", "E3", "E4", "E5", "E6"],
        level=AnalysisLevel.DAILY
    )
    assert learning.confidence == ConfidenceLevel.HIGH

    # Get insights for sweet-spot workout
    insights = intelligence.get_daily_insights({
        "workout_type": "sweet-spot",
        "planned_intensity": 89
    })

    assert len(insights["relevant_learnings"]) == 1
    assert len(insights["recommendations"]) == 1
    assert "88-90% FTP optimal" in insights["recommendations"][0]
    assert "HIGH" in insights["recommendations"][0]


def test_get_weekly_synthesis_high_confidence_learnings():
    """Test weekly synthesis identifies high confidence learnings."""
    intelligence = TrainingIntelligence()

    # Add LOW confidence learning
    intelligence.add_learning(
        category="test1",
        description="Test 1",
        evidence=["E1"],
        level=AnalysisLevel.DAILY
    )

    # Add HIGH confidence learning
    learning_high = intelligence.add_learning(
        category="test2",
        description="Test 2",
        evidence=["E1", "E2", "E3", "E4", "E5", "E6"],
        level=AnalysisLevel.WEEKLY
    )
    assert learning_high.confidence == ConfidenceLevel.HIGH

    synthesis = intelligence.get_weekly_synthesis(week_number=2)

    assert synthesis["total_learnings"] == 2
    assert len(synthesis["high_confidence_learnings"]) == 1
    assert synthesis["high_confidence_learnings"][0].category == "test2"


def test_get_monthly_trends_validated_protocols():
    """Test monthly trends list validated protocols."""
    intelligence = TrainingIntelligence()

    # Add learning and manually promote to VALIDATED
    learning = intelligence.add_learning(
        category="sweet-spot",
        description="88-90% optimal",
        evidence=["E" + str(i) for i in range(10)],
        level=AnalysisLevel.DAILY
    )
    assert learning.confidence == ConfidenceLevel.VALIDATED
    assert learning.validated is True

    trends = intelligence.get_monthly_trends(month=1, year=2026)

    assert len(trends["validated_learnings"]) == 1
    assert trends["validated_learnings"][0].description == "88-90% optimal"
    assert trends["validated_learnings"][0].validated is True


# ============================================================================
# TESTS PERSISTENCE (3)
# ============================================================================


def test_save_and_load_json(tmp_path):
    """Test save/load roundtrip preserves all data."""
    intelligence = TrainingIntelligence()

    # Add data
    learning = intelligence.add_learning(
        category="test",
        description="Test learning",
        evidence=["E1", "E2"],
        level=AnalysisLevel.DAILY
    )

    pattern = intelligence.identify_pattern(
        name="test_pattern",
        trigger_conditions={"test": "value"},
        observed_outcome="Outcome",
        observation_date=date.today()
    )

    adaptation = intelligence.propose_adaptation(
        protocol_name="test_protocol",
        adaptation_type="MODIFY",
        current_rule="Old",
        proposed_rule="New",
        justification="Better",
        evidence=["E1", "E2", "E3"]
    )

    # Save
    filepath = tmp_path / "test_intelligence.json"
    intelligence.save_to_file(filepath)

    # Verify file exists
    assert filepath.exists()

    # Load
    loaded = TrainingIntelligence.load_from_file(filepath)

    # Verify counts
    assert len(loaded.learnings) == 1
    assert len(loaded.patterns) == 1
    assert len(loaded.adaptations) == 1

    # Verify learning preserved
    loaded_learning = list(loaded.learnings.values())[0]
    assert loaded_learning.category == "test"
    assert loaded_learning.description == "Test learning"
    assert len(loaded_learning.evidence) == 2
    assert loaded_learning.level == AnalysisLevel.DAILY
    assert loaded_learning.confidence == ConfidenceLevel.LOW

    # Verify pattern preserved
    loaded_pattern = list(loaded.patterns.values())[0]
    assert loaded_pattern.name == "test_pattern"
    assert loaded_pattern.frequency == 1
    assert loaded_pattern.trigger_conditions == {"test": "value"}

    # Verify adaptation preserved
    loaded_adaptation = list(loaded.adaptations.values())[0]
    assert loaded_adaptation.protocol_name == "test_protocol"
    assert loaded_adaptation.adaptation_type == "MODIFY"
    assert loaded_adaptation.status == "PROPOSED"


def test_save_creates_valid_json(tmp_path):
    """Test save creates valid JSON that can be read."""
    intelligence = TrainingIntelligence()

    intelligence.add_learning(
        category="test",
        description="Test",
        evidence=["E1"],
        level=AnalysisLevel.DAILY
    )

    filepath = tmp_path / "test_intelligence.json"
    intelligence.save_to_file(filepath)

    # Verify JSON is valid
    with open(filepath, 'r') as f:
        data = json.load(f)

    assert "learnings" in data
    assert "patterns" in data
    assert "adaptations" in data
    assert len(data["learnings"]) == 1


def test_load_empty_intelligence(tmp_path):
    """Test loading empty intelligence state."""
    intelligence = TrainingIntelligence()

    filepath = tmp_path / "empty_intelligence.json"
    intelligence.save_to_file(filepath)

    loaded = TrainingIntelligence.load_from_file(filepath)

    assert len(loaded.learnings) == 0
    assert len(loaded.patterns) == 0
    assert len(loaded.adaptations) == 0
