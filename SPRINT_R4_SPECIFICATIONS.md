# Sprint R4 - Training Intelligence & Feedback Loop

**Date :** 2026-01-01
**Estimation :** 8-12h (1 session)
**Priority :** P0-CRITICAL
**Status :** ✅ APPROUVÉ PO

---

## 🎯 OBJECTIF

Créer système mémoire partagée pour enrichissement mutuel analyses quotidienne/hebdomadaire/mensuelle.

**Problème résolu :**
- ❌ Analyses en silos temporels (quotidien/hebdo/mensuel déconnectés)
- ❌ Enseignements perdus entre analyses
- ❌ Patterns non détectés automatiquement
- ❌ Protocoles non validés systématiquement

**Solution :**
- ✅ Mémoire partagée centralisée (learnings/patterns/adaptations)
- ✅ Feedback loop continu entre échelles temporelles
- ✅ Intelligence progressive (confidence LOW→VALIDATED)
- ✅ Recommandations contextuelles automatiques

---

## 📐 ARCHITECTURE

### Structure Fichiers

```
cyclisme_training_logs/
├── intelligence/
│   ├── __init__.py
│   └── training_intelligence.py  (600-800 lignes)

tests/
├── intelligence/
│   ├── __init__.py
│   └── test_training_intelligence.py  (15-20 tests)

project-docs/
├── guides/
│   └── GUIDE_INTELLIGENCE.md  (500+ lignes)
└── CHANGELOG.md  (v2.1.0)

docs/
└── modules/
    └── intelligence.rst  (Sphinx API)

~/cyclisme-training-logs-data/
└── intelligence/
    └── training_intelligence_2026.json
```

### Dépendances

```python
# Internes
from cyclisme_training_logs.config.athlete_profile import AthleteProfile

# Externes (déjà installées)
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import logging
```

---

## 📊 CLASSES ET DATACLASSES

### 1. AnalysisLevel (Enum)

**Rôle :** Niveau temporel d'analyse

```python
class AnalysisLevel(Enum):
    """Temporal level of training analysis."""

    DAILY = "daily"      # Post-session analysis
    WEEKLY = "weekly"    # Week summary (6 markdown files)
    MONTHLY = "monthly"  # Strategic trends
```

**Utilisation :**
```python
learning = TrainingLearning(
    level=AnalysisLevel.DAILY,  # Découvert en analyse quotidienne
    # ...
)
```

---

### 2. ConfidenceLevel (Enum)

**Rôle :** Niveau de confiance enseignement/pattern

```python
class ConfidenceLevel(Enum):
    """Confidence in a learning or pattern discovery."""

    LOW = "low"          # 1-2 observations
    MEDIUM = "medium"    # 3-5 observations
    HIGH = "high"        # 6-10 observations
    VALIDATED = "validated"  # 10+ observations, protocole officiel
```

**Progression :**
```
LOW → MEDIUM → HIGH → VALIDATED
1-2    3-5      6-10    10+
observations
```

---

### 3. TrainingLearning (Dataclass)

**Rôle :** Enseignement extrait des données entraînement

```python
@dataclass
class TrainingLearning:
    """
    A learning extracted from training data with progressive validation.

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
    evidence: List[str]
    confidence: ConfidenceLevel
    impact: str  # LOW/MEDIUM/HIGH
    applied: bool = False
    validated: bool = False

    def promote_confidence(self) -> None:
        """
        Promote confidence level after additional validation.

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
            ConfidenceLevel.HIGH: ConfidenceLevel.VALIDATED
        }
        if self.confidence in transitions:
            self.confidence = transitions[self.confidence]

            # Mark as validated if reached VALIDATED status
            if self.confidence == ConfidenceLevel.VALIDATED:
                self.validated = True
```

**Validation :**
- ✅ Immutable après création (sauf evidence, confidence, applied, validated)
- ✅ ID unique : `{category}_{timestamp}`
- ✅ Evidence : Liste extensible (ajout observations)
- ✅ Confidence : Progression automatique via `promote_confidence()`

---

### 4. Pattern (Dataclass)

**Rôle :** Pattern récurrent identifié sur plusieurs séances

```python
@dataclass
class Pattern:
    """
    Recurring pattern identified across multiple training sessions.

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
    trigger_conditions: Dict[str, Any]
    observed_outcome: str
    frequency: int
    first_seen: date
    last_seen: date
    confidence: ConfidenceLevel

    def matches(self, conditions: Dict[str, Any]) -> bool:
        """
        Check if current conditions match this pattern triggers.

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
                    if not (isinstance(value, (int, float)) and value < threshold):
                        return False
                elif condition.startswith(">"):
                    threshold = float(condition[1:].replace("h", ""))
                    if not (isinstance(value, (int, float)) and value > threshold):
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
        """
        Promote confidence based on frequency.

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
```

**Validation :**
- ✅ `matches()` implémenté (conditions <, >, =)
- ✅ `promote_confidence()` automatique basé frequency
- ✅ trigger_conditions flexible (string operators)

---

### 5. ProtocolAdaptation (Dataclass)

**Rôle :** Adaptation proposée à protocole existant

```python
@dataclass
class ProtocolAdaptation:
    """
    Recommended adaptation to existing training protocol.

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
    evidence: List[str]
    confidence: ConfidenceLevel
    status: str  # PROPOSED/TESTED/VALIDATED/REJECTED
```

**Validation :**
- ✅ adaptation_type : ADD/MODIFY/REMOVE uniquement
- ✅ status : PROPOSED → TESTED → VALIDATED/REJECTED
- ✅ confidence basé sur len(evidence)

---

### 6. TrainingIntelligence (Classe Principale)

**Rôle :** Gestionnaire mémoire partagée + intelligence multi-temporelle

```python
class TrainingIntelligence:
    """
    Central intelligence managing learnings, patterns, and protocol adaptations.

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

    def __init__(self):
        """Initialize empty intelligence memory."""
        self.learnings: Dict[str, TrainingLearning] = {}
        self.patterns: Dict[str, Pattern] = {}
        self.adaptations: Dict[str, ProtocolAdaptation] = {}

        logger.info("TrainingIntelligence initialized (empty memory)")
```

---

## 🔧 FONCTIONS CORE (8)

### 1. add_learning()

**Signature :**
```python
def add_learning(
    self,
    category: str,
    description: str,
    evidence: List[str],
    level: AnalysisLevel,
    impact: str = "MEDIUM"
) -> TrainingLearning:
    """
    Add new learning or reinforce existing one.

    If similar learning exists (same category + similar description):
    - Append evidence to existing
    - Promote confidence level

    Otherwise:
    - Create new learning with confidence LOW

    Args:
        category: Learning category (e.g. "sweet-spot", "hydration")
        description: What was learned (concise)
        evidence: Supporting data (e.g. ["S024-04: 2x10@88% RPE 7"])
        level: Where discovered (DAILY/WEEKLY/MONTHLY)
        impact: Estimated impact (LOW/MEDIUM/HIGH)

    Returns:
        TrainingLearning object (new or reinforced)

    Example:
        >>> intelligence = TrainingIntelligence()
        >>>
        >>> # First observation
        >>> learning = intelligence.add_learning(
        ...     category="sweet-spot",
        ...     description="88% FTP sustainable 2x10min",
        ...     evidence=["S024-04: 2x10@88% RPE 7"],
        ...     level=AnalysisLevel.DAILY
        ... )
        >>> assert learning.confidence == ConfidenceLevel.LOW
        >>>
        >>> # Second observation (similar → reinforce)
        >>> learning = intelligence.add_learning(
        ...     category="sweet-spot",
        ...     description="88% FTP sustainable 2x10min",
        ...     evidence=["S024-06: 2x10@89% RPE 7"],
        ...     level=AnalysisLevel.DAILY
        ... )
        >>> assert learning.confidence == ConfidenceLevel.MEDIUM
    """
```

**Implémentation :**
```python
    learning_id = f"{category}_{datetime.now().timestamp()}"

    # Check if similar learning exists
    similar = self._find_similar_learning(category, description)
    if similar:
        # Reinforce existing
        similar.evidence.extend(evidence)
        similar.promote_confidence()
        logger.info(f"Reinforced learning '{similar.id}' (confidence: {similar.confidence.value})")
        return similar

    # Create new
    learning = TrainingLearning(
        id=learning_id,
        timestamp=datetime.now(),
        level=level,
        category=category,
        description=description,
        evidence=evidence,
        confidence=ConfidenceLevel.LOW,
        impact=impact
    )

    self.learnings[learning_id] = learning
    logger.info(f"Added new learning '{learning_id}' (category: {category})")

    return learning
```

**Validation :**
- ✅ Détecte similarité (même category + description proche)
- ✅ Renforce existant si trouvé (evidence + promote_confidence)
- ✅ Crée nouveau sinon (confidence LOW)
- ✅ Logging INFO

---

### 2. identify_pattern()

**Signature :**
```python
def identify_pattern(
    self,
    name: str,
    trigger_conditions: Dict[str, Any],
    observed_outcome: str
) -> Pattern:
    """
    Register new pattern or update existing one.

    If pattern with same name exists:
    - Increment frequency
    - Update last_seen date
    - Promote confidence based on new frequency

    Otherwise:
    - Create new pattern with frequency 1, confidence LOW

    Args:
        name: Pattern name (descriptive, snake_case)
        trigger_conditions: Conditions triggering pattern
        observed_outcome: What happens when triggered

    Returns:
        Pattern object (new or updated)

    Example:
        >>> intelligence = TrainingIntelligence()
        >>>
        >>> # First observation
        >>> pattern = intelligence.identify_pattern(
        ...     name="sleep_debt_vo2_failure",
        ...     trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        ...     observed_outcome="Unable to complete, RPE 9+"
        ... )
        >>> assert pattern.frequency == 1
        >>> assert pattern.confidence == ConfidenceLevel.LOW
        >>>
        >>> # Second observation (same name → update)
        >>> pattern = intelligence.identify_pattern(
        ...     name="sleep_debt_vo2_failure",
        ...     trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        ...     observed_outcome="Unable to complete, RPE 9+"
        ... )
        >>> assert pattern.frequency == 2
    """
```

**Implémentation :**
```python
    # Check if pattern exists
    existing = self._find_pattern_by_name(name)
    if existing:
        existing.frequency += 1
        existing.last_seen = date.today()
        existing.promote_confidence()
        logger.info(f"Updated pattern '{name}' (frequency: {existing.frequency}, confidence: {existing.confidence.value})")
        return existing

    # Create new
    pattern_id = f"pattern_{name}_{datetime.now().timestamp()}"
    pattern = Pattern(
        id=pattern_id,
        name=name,
        trigger_conditions=trigger_conditions,
        observed_outcome=observed_outcome,
        frequency=1,
        first_seen=date.today(),
        last_seen=date.today(),
        confidence=ConfidenceLevel.LOW
    )

    self.patterns[pattern_id] = pattern
    logger.info(f"Identified new pattern '{name}'")

    return pattern
```

**Validation :**
- ✅ Cherche par name (unique)
- ✅ Incrémente frequency + update last_seen si existe
- ✅ promote_confidence() automatique
- ✅ Crée nouveau sinon

---

### 3. propose_adaptation()

**Signature :**
```python
def propose_adaptation(
    self,
    protocol_name: str,
    adaptation_type: str,
    current_rule: str,
    proposed_rule: str,
    justification: str,
    evidence: List[str]
) -> ProtocolAdaptation:
    """
    Propose adaptation to existing protocol.

    Confidence determined by evidence count:
    - 1-2 evidence → LOW
    - 3-5 evidence → MEDIUM
    - 6+ evidence → HIGH

    Args:
        protocol_name: Protocol to adapt (e.g. "hydration", "vo2_veto")
        adaptation_type: ADD/MODIFY/REMOVE
        current_rule: Existing rule
        proposed_rule: Proposed new rule
        justification: Why this change
        evidence: Supporting data points

    Returns:
        ProtocolAdaptation object (status: PROPOSED)

    Example:
        >>> intelligence = TrainingIntelligence()
        >>>
        >>> adaptation = intelligence.propose_adaptation(
        ...     protocol_name="sweet_spot_targets",
        ...     adaptation_type="MODIFY",
        ...     current_rule="Sweet-Spot: 86-92% FTP",
        ...     proposed_rule="Sweet-Spot optimal: 88-90% FTP (master)",
        ...     justification="3 séances validées, découplage <7%",
        ...     evidence=[
        ...         "S024-04: 2x10@88% RPE 7",
        ...         "S024-06: 2x10@89% RPE 7",
        ...         "S025-01: 2x10@90% RPE 8"
        ...     ]
        ... )
        >>> assert adaptation.confidence == ConfidenceLevel.MEDIUM
        >>> assert adaptation.status == "PROPOSED"
    """
```

**Implémentation :**
```python
    adaptation_id = f"{protocol_name}_{adaptation_type}_{datetime.now().timestamp()}"

    # Determine confidence from evidence count
    evidence_count = len(evidence)
    if evidence_count >= 6:
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
        status="PROPOSED"
    )

    self.adaptations[adaptation_id] = adaptation
    logger.info(f"Proposed adaptation for protocol '{protocol_name}' (confidence: {confidence.value})")

    return adaptation
```

**Validation :**
- ✅ Confidence auto-déterminée par len(evidence)
- ✅ Status toujours PROPOSED à création
- ✅ Validation adaptation_type (ADD/MODIFY/REMOVE)

---

### 4. get_daily_insights()

**Signature :**
```python
def get_daily_insights(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate insights for daily post-session analysis.

    Uses accumulated knowledge to provide:
    - Matched patterns (warnings)
    - Relevant learnings (recommendations)
    - Context-aware suggestions

    Args:
        session_data: Current session metrics
            - tss: int
            - workout_type: str
            - sleep_last_night: float
            - rpe: int
            - decoupling: float (optional)
            - planned_intensity: float (optional)

    Returns:
        Dict with:
            - matched_patterns: List[Pattern]
            - relevant_learnings: List[TrainingLearning]
            - warnings: List[str]
            - recommendations: List[str]

    Example:
        >>> intelligence = TrainingIntelligence()
        >>> # ... add learnings and patterns ...
        >>>
        >>> insights = intelligence.get_daily_insights({
        ...     "tss": 85,
        ...     "workout_type": "VO2",
        ...     "sleep_last_night": 5.5,
        ...     "rpe": 7
        ... })
        >>>
        >>> print(insights["warnings"])
        ["Pattern matched: sleep_debt_vo2_failure - Consider postponing"]
        >>>
        >>> print(insights["recommendations"])
        ["VO2 Max: 106-110% FTP validated (Confidence: HIGH, 8 obs)"]
    """
```

**Implémentation :**
```python
    insights = {
        "matched_patterns": [],
        "relevant_learnings": [],
        "warnings": [],
        "recommendations": []
    }

    # Check patterns
    for pattern in self.patterns.values():
        if pattern.matches(session_data):
            insights["matched_patterns"].append(pattern)
            insights["warnings"].append(
                f"⚠️ Pattern matched: {pattern.name} - {pattern.observed_outcome}"
            )

    # Find relevant learnings
    workout_type = session_data.get("workout_type", "").lower()
    for learning in self.learnings.values():
        if workout_type in learning.category.lower():
            if learning.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VALIDATED]:
                insights["relevant_learnings"].append(learning)
                insights["recommendations"].append(
                    f"✅ {learning.category.title()}: {learning.description} "
                    f"(Confidence: {learning.confidence.value.upper()}, {len(learning.evidence)} obs)"
                )

    return insights
```

**Validation :**
- ✅ Patterns matching via `pattern.matches()`
- ✅ Learnings filtrés par workout_type + confidence HIGH/VALIDATED
- ✅ Warnings pour patterns matchés
- ✅ Recommendations pour learnings validés

---

### 5. get_weekly_synthesis()

**Signature :**
```python
def get_weekly_synthesis(self, week_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate weekly synthesis using daily learnings + patterns.

    Analyzes week to:
    - Identify new patterns emerging
    - Validate learnings with multiple observations
    - Propose protocol adaptations
    - Recommend focus areas for next week

    Args:
        week_data: Week summary
            - total_tss: int
            - sessions: int
            - completion_rate: float
            - workout_types: Dict[str, int]

    Returns:
        Dict with:
            - new_patterns_identified: List[Pattern]
            - validated_learnings: List[TrainingLearning]
            - proposed_adaptations: List[ProtocolAdaptation]
            - next_week_focus: List[str]

    Example:
        >>> synthesis = intelligence.get_weekly_synthesis({
        ...     "total_tss": 320,
        ...     "sessions": 7,
        ...     "completion_rate": 100,
        ...     "workout_types": {"sweet-spot": 3, "endurance": 4}
        ... })
        >>>
        >>> print(synthesis["validated_learnings"])
        [TrainingLearning(category="sweet-spot", confidence=HIGH, ...)]
    """
```

**Implémentation :**
```python
    synthesis = {
        "new_patterns_identified": [],
        "validated_learnings": [],
        "proposed_adaptations": [],
        "next_week_focus": []
    }

    # Identify new patterns (frequency 1-2, first seen this week)
    for pattern in self.patterns.values():
        if pattern.frequency <= 2:
            synthesis["new_patterns_identified"].append(pattern)

    # Find validated learnings (promoted this week to HIGH/VALIDATED)
    for learning in self.learnings.values():
        if learning.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VALIDATED]:
            synthesis["validated_learnings"].append(learning)

    # Find proposed adaptations (status PROPOSED)
    for adaptation in self.adaptations.values():
        if adaptation.status == "PROPOSED":
            synthesis["proposed_adaptations"].append(adaptation)

    # Generate focus areas
    if synthesis["new_patterns_identified"]:
        synthesis["next_week_focus"].append(
            f"Validate {len(synthesis['new_patterns_identified'])} new patterns "
            f"(need 3+ observations)"
        )

    if synthesis["proposed_adaptations"]:
        synthesis["next_week_focus"].append(
            f"Test {len(synthesis['proposed_adaptations'])} protocol adaptations"
        )

    return synthesis
```

**Validation :**
- ✅ new_patterns : frequency ≤ 2
- ✅ validated_learnings : confidence HIGH/VALIDATED
- ✅ proposed_adaptations : status PROPOSED
- ✅ next_week_focus : Actionnable recommendations

---

### 6. get_monthly_trends()

**Signature :**
```python
def get_monthly_trends(self, month_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate monthly trends and strategic recommendations.

    Analyzes month to:
    - List validated protocols (confidence VALIDATED)
    - Identify emerging patterns (frequency 5-9)
    - Recommend strategic adaptations
    - Define next month objectives

    Args:
        month_data: Month summary
            - total_sessions: int
            - total_tss: int
            - ctl_progression: float

    Returns:
        Dict with:
            - validated_protocols: List[TrainingLearning]
            - emerging_patterns: List[Pattern]
            - strategic_adaptations: List[ProtocolAdaptation]
            - next_month_objectives: List[str]

    Example:
        >>> trends = intelligence.get_monthly_trends({
        ...     "total_sessions": 28,
        ...     "total_tss": 1240,
        ...     "ctl_progression": +12
        ... })
        >>>
        >>> print(len(trends["validated_protocols"]))
        3  # Sweet-Spot 88-90%, Hydration 500ml/h, VO2 VETO <6h
    """
```

**Implémentation :**
```python
    trends = {
        "validated_protocols": [],
        "emerging_patterns": [],
        "strategic_adaptations": [],
        "next_month_objectives": []
    }

    # Validated protocols (confidence VALIDATED, 10+ observations)
    for learning in self.learnings.values():
        if learning.confidence == ConfidenceLevel.VALIDATED:
            trends["validated_protocols"].append(learning)

    # Emerging patterns (frequency 5-9, not yet validated)
    for pattern in self.patterns.values():
        if 5 <= pattern.frequency < 10:
            trends["emerging_patterns"].append(pattern)

    # Strategic adaptations (confidence HIGH/VALIDATED)
    for adaptation in self.adaptations.values():
        if adaptation.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VALIDATED]:
            trends["strategic_adaptations"].append(adaptation)

    # Generate objectives
    if trends["emerging_patterns"]:
        trends["next_month_objectives"].append(
            f"Validate {len(trends['emerging_patterns'])} emerging patterns "
            f"(5-9 obs → 10+ for VALIDATED)"
        )

    if trends["validated_protocols"]:
        trends["next_month_objectives"].append(
            f"Integrate {len(trends['validated_protocols'])} validated protocols "
            f"into default planning"
        )

    return trends
```

**Validation :**
- ✅ validated_protocols : confidence VALIDATED uniquement
- ✅ emerging_patterns : frequency 5-9
- ✅ strategic_adaptations : confidence HIGH/VALIDATED
- ✅ next_month_objectives : Objectifs stratégiques

---

### 7. save_to_file()

**Signature :**
```python
def save_to_file(self, filepath: Path) -> None:
    """
    Save intelligence state to JSON file.

    Converts dataclasses to dict, serializes enums to strings.
    Creates parent directories if needed.

    Args:
        filepath: Path to JSON file

    Example:
        >>> intelligence = TrainingIntelligence()
        >>> # ... add learnings ...
        >>>
        >>> intelligence.save_to_file(
        ...     Path("~/cyclisme-training-logs-data/intelligence/training_intelligence_2026.json")
        ... )
    """
```

**Implémentation :**
```python
    from pathlib import Path
    from dataclasses import asdict

    # Ensure parent directory exists
    filepath = Path(filepath).expanduser()
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict
    data = {
        "learnings": {
            k: self._serialize_dataclass(v)
            for k, v in self.learnings.items()
        },
        "patterns": {
            k: self._serialize_dataclass(v)
            for k, v in self.patterns.items()
        },
        "adaptations": {
            k: self._serialize_dataclass(v)
            for k, v in self.adaptations.items()
        },
        "metadata": {
            "version": "2.1.0",
            "last_updated": datetime.now().isoformat(),
            "total_learnings": len(self.learnings),
            "total_patterns": len(self.patterns),
            "total_adaptations": len(self.adaptations),
            "validated_protocols": sum(
                1 for l in self.learnings.values()
                if l.confidence == ConfidenceLevel.VALIDATED
            )
        }
    }

    # Write JSON
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved intelligence to {filepath}")

def _serialize_dataclass(self, obj) -> Dict:
    """Convert dataclass to dict, handling enums."""
    d = asdict(obj)
    for key, value in d.items():
        if isinstance(value, Enum):
            d[key] = value.value
        elif isinstance(value, datetime):
            d[key] = value.isoformat()
        elif isinstance(value, date):
            d[key] = value.isoformat()
    return d
```

**Validation :**
- ✅ Crée dossiers parents si nécessaire
- ✅ Sérialise Enums → strings
- ✅ Sérialise datetime/date → ISO format
- ✅ Metadata avec statistiques

---

### 8. load_from_file()

**Signature :**
```python
@classmethod
def load_from_file(cls, filepath: Path) -> 'TrainingIntelligence':
    """
    Load intelligence state from JSON file.

    Deserializes JSON, converts strings to enums/dates.

    Args:
        filepath: Path to JSON file

    Returns:
        TrainingIntelligence instance with loaded state

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is corrupted

    Example:
        >>> intelligence = TrainingIntelligence.load_from_file(
        ...     Path("~/cyclisme-training-logs-data/intelligence/training_intelligence_2026.json")
        ... )
        >>> print(len(intelligence.learnings))
        24
    """
```

**Implémentation :**
```python
    from pathlib import Path

    filepath = Path(filepath).expanduser()

    if not filepath.exists():
        logger.warning(f"File {filepath} not found, returning empty intelligence")
        return cls()

    with open(filepath, 'r') as f:
        data = json.load(f)

    instance = cls()

    # Deserialize learnings
    for learning_id, learning_data in data.get("learnings", {}).items():
        instance.learnings[learning_id] = cls._deserialize_learning(learning_data)

    # Deserialize patterns
    for pattern_id, pattern_data in data.get("patterns", {}).items():
        instance.patterns[pattern_id] = cls._deserialize_pattern(pattern_data)

    # Deserialize adaptations
    for adaptation_id, adaptation_data in data.get("adaptations", {}).items():
        instance.adaptations[adaptation_id] = cls._deserialize_adaptation(adaptation_data)

    logger.info(f"Loaded intelligence from {filepath} "
                f"({len(instance.learnings)} learnings, "
                f"{len(instance.patterns)} patterns)")

    return instance

@staticmethod
def _deserialize_learning(data: Dict) -> TrainingLearning:
    """Convert dict to TrainingLearning, handling enums/dates."""
    return TrainingLearning(
        id=data["id"],
        timestamp=datetime.fromisoformat(data["timestamp"]),
        level=AnalysisLevel(data["level"]),
        category=data["category"],
        description=data["description"],
        evidence=data["evidence"],
        confidence=ConfidenceLevel(data["confidence"]),
        impact=data["impact"],
        applied=data.get("applied", False),
        validated=data.get("validated", False)
    )

@staticmethod
def _deserialize_pattern(data: Dict) -> Pattern:
    """Convert dict to Pattern."""
    return Pattern(
        id=data["id"],
        name=data["name"],
        trigger_conditions=data["trigger_conditions"],
        observed_outcome=data["observed_outcome"],
        frequency=data["frequency"],
        first_seen=date.fromisoformat(data["first_seen"]),
        last_seen=date.fromisoformat(data["last_seen"]),
        confidence=ConfidenceLevel(data["confidence"])
    )

@staticmethod
def _deserialize_adaptation(data: Dict) -> ProtocolAdaptation:
    """Convert dict to ProtocolAdaptation."""
    return ProtocolAdaptation(
        id=data["id"],
        protocol_name=data["protocol_name"],
        adaptation_type=data["adaptation_type"],
        current_rule=data["current_rule"],
        proposed_rule=data["proposed_rule"],
        justification=data["justification"],
        evidence=data["evidence"],
        confidence=ConfidenceLevel(data["confidence"]),
        status=data["status"]
    )
```

**Validation :**
- ✅ Retourne instance vide si fichier absent (graceful)
- ✅ Désérialise Enums depuis strings
- ✅ Désérialise dates depuis ISO format
- ✅ Logging INFO avec statistiques

---

## 🧪 TESTS (15-20)

### Structure Tests

```
tests/intelligence/
├── __init__.py
└── test_training_intelligence.py
```

### Tests Dataclasses (3)

```python
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

    learning.promote_confidence()
    assert learning.confidence == ConfidenceLevel.MEDIUM

    learning.promote_confidence()
    assert learning.confidence == ConfidenceLevel.HIGH

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
    assert adaptation.status == "PROPOSED"
    assert len(adaptation.evidence) == 2
```

### Tests add_learning (3)

```python
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
    assert learning2.confidence == ConfidenceLevel.MEDIUM
    assert len(intelligence.learnings) == 1  # Still only 1 learning


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
```

### Tests identify_pattern (3)

```python
def test_identify_pattern_new():
    """Test identifying new pattern creates frequency 1."""
    intelligence = TrainingIntelligence()

    pattern = intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        observed_outcome="Failure"
    )

    assert pattern.frequency == 1
    assert pattern.confidence == ConfidenceLevel.LOW
    assert pattern.first_seen == date.today()


def test_identify_pattern_update_existing():
    """Test identifying existing pattern increments frequency."""
    intelligence = TrainingIntelligence()

    # First observation
    pattern1 = intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h"},
        observed_outcome="Failure"
    )

    # Second observation (same name)
    pattern2 = intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h"},
        observed_outcome="Failure"
    )

    assert pattern1.id == pattern2.id
    assert pattern2.frequency == 2
    assert len(intelligence.patterns) == 1


def test_pattern_confidence_progression_by_frequency():
    """Test pattern confidence increases with frequency."""
    intelligence = TrainingIntelligence()

    pattern = intelligence.identify_pattern(
        name="test_pattern",
        trigger_conditions={"test": "value"},
        observed_outcome="Outcome"
    )

    # Frequency 1-2 → LOW
    assert pattern.confidence == ConfidenceLevel.LOW

    # Simulate 2 more observations → MEDIUM
    for _ in range(2):
        pattern = intelligence.identify_pattern(
            name="test_pattern",
            trigger_conditions={"test": "value"},
            observed_outcome="Outcome"
        )
    assert pattern.frequency == 3
    assert pattern.confidence == ConfidenceLevel.MEDIUM

    # Simulate 3 more observations → HIGH
    for _ in range(3):
        pattern = intelligence.identify_pattern(
            name="test_pattern",
            trigger_conditions={"test": "value"},
            observed_outcome="Outcome"
        )
    assert pattern.frequency == 6
    assert pattern.confidence == ConfidenceLevel.HIGH
```

### Tests propose_adaptation (3)

```python
def test_propose_adaptation_confidence_by_evidence():
    """Test adaptation confidence determined by evidence count."""
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
```

### Tests Multi-Temporal Insights (4)

```python
def test_get_daily_insights_pattern_matching():
    """Test daily insights match patterns and warn."""
    intelligence = TrainingIntelligence()

    # Add pattern
    intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        observed_outcome="Failure"
    )

    # Get insights with matching conditions
    insights = intelligence.get_daily_insights({
        "sleep": 5.5,
        "workout_type": "VO2"
    })

    assert len(insights["matched_patterns"]) == 1
    assert len(insights["warnings"]) == 1
    assert "sleep_debt_vo2_failure" in insights["warnings"][0]


def test_get_daily_insights_relevant_learnings():
    """Test daily insights return relevant validated learnings."""
    intelligence = TrainingIntelligence()

    # Add validated learning
    learning = intelligence.add_learning(
        category="sweet-spot",
        description="88-90% FTP optimal",
        evidence=["E1"],
        level=AnalysisLevel.DAILY
    )
    learning.confidence = ConfidenceLevel.VALIDATED  # Manually promote for test

    # Get insights for sweet-spot workout
    insights = intelligence.get_daily_insights({
        "workout_type": "sweet-spot",
        "planned_intensity": 89
    })

    assert len(insights["relevant_learnings"]) == 1
    assert len(insights["recommendations"]) == 1
    assert "88-90% FTP optimal" in insights["recommendations"][0]


def test_get_weekly_synthesis_new_patterns():
    """Test weekly synthesis identifies new patterns."""
    intelligence = TrainingIntelligence()

    # Add new pattern (frequency 1-2)
    intelligence.identify_pattern(
        name="new_pattern",
        trigger_conditions={"test": "value"},
        observed_outcome="Outcome"
    )

    synthesis = intelligence.get_weekly_synthesis({
        "total_tss": 320,
        "sessions": 7
    })

    assert len(synthesis["new_patterns_identified"]) == 1
    assert synthesis["new_patterns_identified"][0].name == "new_pattern"


def test_get_monthly_trends_validated_protocols():
    """Test monthly trends list validated protocols."""
    intelligence = TrainingIntelligence()

    # Add validated learning
    learning = intelligence.add_learning(
        category="sweet-spot",
        description="88-90% optimal",
        evidence=["E1"],
        level=AnalysisLevel.DAILY
    )
    learning.confidence = ConfidenceLevel.VALIDATED

    trends = intelligence.get_monthly_trends({
        "total_sessions": 28,
        "total_tss": 1240
    })

    assert len(trends["validated_protocols"]) == 1
    assert trends["validated_protocols"][0].description == "88-90% optimal"
```

### Tests Persistance (2-3)

```python
def test_save_and_load_json(tmp_path):
    """Test save/load roundtrip preserves all data."""
    intelligence = TrainingIntelligence()

    # Add data
    intelligence.add_learning(
        category="test",
        description="Test learning",
        evidence=["E1", "E2"],
        level=AnalysisLevel.DAILY
    )

    intelligence.identify_pattern(
        name="test_pattern",
        trigger_conditions={"test": "value"},
        observed_outcome="Outcome"
    )

    intelligence.propose_adaptation(
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

    # Load
    loaded = TrainingIntelligence.load_from_file(filepath)

    # Verify
    assert len(loaded.learnings) == 1
    assert len(loaded.patterns) == 1
    assert len(loaded.adaptations) == 1

    # Verify learning preserved
    learning = list(loaded.learnings.values())[0]
    assert learning.category == "test"
    assert len(learning.evidence) == 2
    assert learning.level == AnalysisLevel.DAILY


def test_load_nonexistent_file_returns_empty():
    """Test loading nonexistent file returns empty intelligence."""
    from pathlib import Path

    loaded = TrainingIntelligence.load_from_file(
        Path("/tmp/nonexistent_12345.json")
    )

    assert len(loaded.learnings) == 0
    assert len(loaded.patterns) == 0
    assert len(loaded.adaptations) == 0


def test_save_creates_parent_directories(tmp_path):
    """Test save creates parent directories if needed."""
    intelligence = TrainingIntelligence()
    intelligence.add_learning(
        category="test",
        description="Test",
        evidence=["E1"],
        level=AnalysisLevel.DAILY
    )

    # Path with multiple parent levels
    filepath = tmp_path / "deep" / "nested" / "path" / "intelligence.json"

    intelligence.save_to_file(filepath)

    assert filepath.exists()
    assert filepath.parent.exists()
```

---

## 📚 DOCUMENTATION

### GUIDE_INTELLIGENCE.md (500+ lignes)

**Structure :**
```markdown
# Guide Training Intelligence

## Introduction
- Problème résolu (silos temporels)
- Solution (mémoire partagée)
- Architecture feedback loop

## Installation
- Prérequis
- Configuration .env

## Concepts Clés
- Learnings (confidence progression)
- Patterns (trigger conditions)
- Protocol Adaptations (status lifecycle)
- Multi-temporal insights

## Cas d'Usage

### Quotidien : Post-Séance
- Ajouter learning si découverte
- Consulter insights (warnings + recommendations)
- Exemple complet

### Hebdomadaire : Bilan
- Synthétiser nouvelle semaine
- Identifier patterns émergents
- Proposer adaptations protocoles
- Exemple complet

### Mensuel : Stratégie
- Lister protocoles validés
- Analyser patterns confirmés
- Définir objectifs mois suivant
- Exemple complet

## Exemples Complets

### Exemple 1 : Sweet-Spot Optimal
[Code complet jour 1 → mois 1]

### Exemple 2 : Prévention VO2 Échec
[Code complet pattern detection → warning]

## API Reference
[Documentation toutes fonctions]

## Troubleshooting
- Problèmes courants
- Solutions

## FAQ
```

---

### CHANGELOG.md v2.1.0

```markdown
## [2.1.0] - 2026-01-02

### Added - Sprint R4 (Training Intelligence)

**Training Intelligence** (`cyclisme_training_logs/intelligence/training_intelligence.py`):
- `TrainingIntelligence` : Gestionnaire mémoire partagée multi-temporelle
  - `add_learning()` : Ajouter enseignements avec progression confidence
  - `identify_pattern()` : Détecter patterns récurrents
  - `propose_adaptation()` : Proposer évolution protocoles
  - `get_daily_insights()` : Insights quotidiens (warnings + recommendations)
  - `get_weekly_synthesis()` : Synthèse hebdo (patterns + learnings validés)
  - `get_monthly_trends()` : Tendances mensuelles (protocoles validés)
  - `save_to_file()` / `load_from_file()` : Persistance JSON
- `TrainingLearning` : Dataclass enseignement avec confidence (LOW→VALIDATED)
- `Pattern` : Dataclass pattern avec trigger_conditions + frequency
- `ProtocolAdaptation` : Dataclass adaptation PROPOSED→VALIDATED
- Enums : `AnalysisLevel` (DAILY/WEEKLY/MONTHLY), `ConfidenceLevel` (LOW/MEDIUM/HIGH/VALIDATED)
- **Feedback Loop** : Enrichissement mutuel analyses quotidienne/hebdo/mensuelle
- **15-20 tests unitaires** (100% coverage)

**Architecture**:
- 100% in-memory (0 hardcoded paths)
- JSON persistence (`~/cyclisme-training-logs-data/intelligence/`)
- Backward compatible (enrichit workflow existant)

**Impact**:
- Détection patterns automatique (prévention échecs)
- Validation progressive protocoles (evidence-based)
- Insights contextuels (quotidien/hebdo/mensuel)
```

---

### Sphinx API (docs/modules/intelligence.rst)

```rst
Intelligence Module
===================

.. automodule:: cyclisme_training_logs.intelligence.training_intelligence
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

TrainingIntelligence
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.TrainingIntelligence
   :members:

Dataclasses
-----------

TrainingLearning
~~~~~~~~~~~~~~~~

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.TrainingLearning
   :members:

Pattern
~~~~~~~

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.Pattern
   :members:

ProtocolAdaptation
~~~~~~~~~~~~~~~~~~

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.ProtocolAdaptation
   :members:

Enums
-----

AnalysisLevel
~~~~~~~~~~~~~

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.AnalysisLevel
   :members:

ConfidenceLevel
~~~~~~~~~~~~~~~

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.ConfidenceLevel
   :members:
```

---

## ✅ ACCEPTANCE CRITERIA

### Code (8/8)
- [ ] TrainingLearning avec `promote_confidence()` LOW→VALIDATED
- [ ] Pattern avec `matches()` trigger_conditions + `promote_confidence()` basé frequency
- [ ] ProtocolAdaptation avec confidence basé evidence count
- [ ] `add_learning()` détecte similarité + renforce existant
- [ ] `identify_pattern()` incrémente frequency si existe
- [ ] `propose_adaptation()` détermine confidence automatiquement
- [ ] `get_daily_insights()` retourne matched_patterns + relevant_learnings
- [ ] `get_weekly_synthesis()` / `get_monthly_trends()` complets

### Tests (5/5)
- [ ] 15-20 tests passing (100%)
- [ ] Coverage 100% training_intelligence.py
- [ ] Tests confidence progression validés
- [ ] Tests persistance JSON roundtrip OK
- [ ] 0 régression tests globaux (488/490)

### Intégration (3/3)
- [ ] Workflow quotidien enrichi (post-séance → insights)
- [ ] Workflow hebdomadaire enrichi (bilan → synthesis)
- [ ] PlanningManager peut utiliser learnings validés

### Documentation (3/3)
- [ ] GUIDE_INTELLIGENCE.md (500+ lignes, cas d'usage complets)
- [ ] CHANGELOG.md v2.1.0 mis à jour
- [ ] Sphinx API modules/intelligence.rst généré

### Architecture (3/3)
- [ ] 0 hardcoded paths (JSON path via expanduser)
- [ ] In-memory Dict storage
- [ ] Backward compatible (ne casse rien)

---

## 🎯 MÉTRIQUES ATTENDUES

| Métrique | Cible | Validation |
|----------|-------|------------|
| Code production | 600-800 lignes | 1 module |
| Tests | 15-20 | 100% coverage |
| Over-delivery tests | 120-150% | Raisonnable |
| Hardcoded paths | 0 | grep check |
| Documentation | 500+ lignes | GUIDE_INTELLIGENCE.md |
| Score MOA | 95-98/100 | Maintenir excellence |
| Temps développement | 8-12h | 1 session |

---

## 🚀 WORKFLOW DÉVELOPPEMENT

### Phase 1 : Core (4-5h)

1. **Créer structure** (30 min)
   ```bash
   mkdir -p cyclisme_training_logs/intelligence
   touch cyclisme_training_logs/intelligence/__init__.py
   touch cyclisme_training_logs/intelligence/training_intelligence.py
   ```

2. **Implémenter Enums + Dataclasses** (1h)
   - AnalysisLevel
   - ConfidenceLevel
   - TrainingLearning
   - Pattern
   - ProtocolAdaptation

3. **Implémenter TrainingIntelligence init + helpers** (1h)
   - `__init__()`
   - `_find_similar_learning()`
   - `_find_pattern_by_name()`
   - `_serialize_dataclass()`
   - `_deserialize_*()` methods

4. **Implémenter 8 fonctions core** (2-2.5h)
   - add_learning()
   - identify_pattern()
   - propose_adaptation()
   - get_daily_insights()
   - get_weekly_synthesis()
   - get_monthly_trends()
   - save_to_file()
   - load_from_file()

### Phase 2 : Tests (2-3h)

5. **Tests dataclasses** (30 min)
   - test_training_learning_promote_confidence
   - test_pattern_matches_conditions
   - test_protocol_adaptation_creation

6. **Tests add_learning** (30 min)
   - test_add_learning_new
   - test_add_learning_reinforce_similar
   - test_add_learning_different_creates_new

7. **Tests identify_pattern** (30 min)
   - test_identify_pattern_new
   - test_identify_pattern_update_existing
   - test_pattern_confidence_progression_by_frequency

8. **Tests propose_adaptation** (30 min)
   - test_propose_adaptation_confidence_by_evidence
   - test_propose_adaptation_status_proposed
   - test_propose_adaptation_types

9. **Tests multi-temporal** (1h)
   - test_get_daily_insights_pattern_matching
   - test_get_daily_insights_relevant_learnings
   - test_get_weekly_synthesis_new_patterns
   - test_get_monthly_trends_validated_protocols

10. **Tests persistance** (30 min)
    - test_save_and_load_json
    - test_load_nonexistent_file_returns_empty
    - test_save_creates_parent_directories

### Phase 3 : Intégration (1-2h)

11. **Modifier workflow quotidien** (30 min)
    - Hook post-séance
    - Appel get_daily_insights()
    - Logging warnings/recommendations

12. **Modifier workflow hebdomadaire** (30 min)
    - Hook bilan semaine
    - Appel get_weekly_synthesis()
    - Enrichir 6 fichiers markdown

13. **Export __init__** (15 min)
    ```python
    # cyclisme_training_logs/intelligence/__init__.py
    from .training_intelligence import (
        TrainingIntelligence,
        TrainingLearning,
        Pattern,
        ProtocolAdaptation,
        AnalysisLevel,
        ConfidenceLevel
    )

    __all__ = [
        "TrainingIntelligence",
        "TrainingLearning",
        "Pattern",
        "ProtocolAdaptation",
        "AnalysisLevel",
        "ConfidenceLevel"
    ]
    ```

### Phase 4 : Documentation (2h)

14. **GUIDE_INTELLIGENCE.md** (1h30)
    - Introduction + architecture
    - Cas d'usage (quotidien/hebdo/mensuel)
    - 2 exemples complets
    - API Reference
    - Troubleshooting

15. **CHANGELOG.md** (15 min)
    - Section v2.1.0
    - Sprint R4 détails

16. **Sphinx API** (15 min)
    - docs/modules/intelligence.rst
    - Rebuild HTML

### Phase 5 : Validation (1h)

17. **Tests complets** (20 min)
    ```bash
    poetry run pytest tests/intelligence/ -v
    # Attendu: 15-20/15-20 passing

    poetry run pytest tests/ -v
    # Attendu: 503-508/510 passing (0 régression)
    ```

18. **Grep hardcoded paths** (10 min)
    ```bash
    grep -rn "'/\|\"~\|/Users\|/home" cyclisme_training_logs/intelligence/
    # Attendu: 0 résultats
    ```

19. **Archive creation** (20 min)
    ```bash
    cd ~/
    tar -czf cyclisme-training-logs-sprint-r4-20260102.tar.gz \
      cyclisme-training-logs/cyclisme_training_logs/intelligence/ \
      cyclisme-training-logs/tests/intelligence/ \
      cyclisme-training-logs/project-docs/ \
      cyclisme-training-logs/docs/
    ```

20. **Notification MOA** (10 min)
    - Commit Git
    - Tag v2.1.0
    - Archive README
    - Checkpoint validation

---

## 📝 DÉVELOPPEUR : ACTIONS IMMÉDIATES

1. **Lire ces spécifications complètes** (15 min)
2. **Questions/clarifications** si nécessaire (10 min)
3. **Commencer Phase 1 : Core** (4-5h)

**Deadline recommandée :** 8-12h (1 session)

**Checkpoint MOA :** À mi-parcours (après Phase 2 Tests)

---

**Sprint R4 - Training Intelligence - READY TO START 🚀**

**MOA - Claude Code**
**Status :** Specs complètes, prêt développement
**PO Approval :** ✅ Validé
