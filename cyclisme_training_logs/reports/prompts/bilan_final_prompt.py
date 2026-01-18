"""Bilan Final AI Prompt Builder.

Constructs AI prompts for bilan_final report generation.

Author: Claude Code (Sprint R10 MVP - Day 3)
Created: 2026-01-18
"""

from typing import Any


def build_bilan_final_prompt(week_data: dict[str, Any]) -> str:
    """Build AI prompt for bilan_final report generation.

    Constructs synthesis-focused prompt including:
    - System instructions (synthesis role, strategic focus)
    - Week objectives vs realized
    - Workout history summary (input)
    - Protocol adaptations
    - Output format specification

    Args:
        week_data: Dictionary with all week data
            - week_number: str (e.g., "S076")
            - objectives: list[str] (planned objectives)
            - workout_history_summary: str (from workout_history report)
            - metrics_final: dict (final comparison metrics)
            - protocol_adaptations: list[dict] (protocol changes)
            - key_sessions: list[dict] (critical sessions)
            - behavioral_learnings: list[dict] (behavioral insights)

    Returns:
        Complete AI prompt string

    Raises:
        ValueError: If required data missing

    Examples:
        >>> week_data = {"week_number": "S076", "objectives": [...]}
        >>> prompt = build_bilan_final_prompt(week_data)
        >>> "strategic cycling coach" in prompt.lower()
        True
    """
    # Validate required data
    required_fields = [
        "week_number",
        "objectives",
        "workout_history_summary",
        "metrics_final",
    ]
    for field in required_fields:
        if field not in week_data:
            raise ValueError(f"Missing required field: {field}")

    # Extract data
    week_number = week_data["week_number"]
    objectives = week_data["objectives"]
    workout_history_summary = week_data["workout_history_summary"]
    metrics_final = week_data["metrics_final"]
    protocol_adaptations = week_data.get("protocol_adaptations", [])
    key_sessions = week_data.get("key_sessions", [])
    behavioral_learnings = week_data.get("behavioral_learnings", [])

    # Format objectives
    objectives_formatted = _format_objectives(objectives)

    # Format metrics
    metrics_formatted = _format_metrics_final(metrics_final)

    # Format protocol adaptations
    protocols_formatted = _format_protocol_adaptations(protocol_adaptations)

    # Format key sessions
    sessions_formatted = _format_key_sessions(key_sessions)

    # Format behavioral learnings
    behavioral_formatted = _format_behavioral_learnings(behavioral_learnings)

    # Construct full prompt
    prompt = f"""You are a strategic cycling coach synthesizing weekly training outcomes into a comprehensive final assessment.

## Your Role

You are writing a **strategic, synthesis-focused** final assessment report in **French** for week {week_number}. Your goal is to extract high-level insights, validate protocols, and provide actionable recommendations for future training.

## Critical Constraints

1. **SYNTHESIS FOCUS**: Extract high-level patterns, NOT session-by-session details
2. **STRATEGIC TONE**: Focus on learnings, protocols, and future applications
3. **REFERENCE WORKOUT HISTORY**: All claims must be supported by workout_history data
4. **MAX 3-4 DISCOVERIES**: Limit major discoveries to the most impactful findings
5. **CONCISE CONCLUSION**: 2-3 sentences maximum for conclusion
6. **French Language**: All text in French, professional cycling vocabulary
7. **Word Limit**: Maximum 1500 words total

## Week Context: {week_number}

### Planned Objectives

{objectives_formatted}

### Workout History Summary (Reference Source)

{workout_history_summary}

### Final Metrics Comparison

{metrics_formatted}

### Protocol Adaptations (if any)

{protocols_formatted}

### Key Sessions Identified

{sessions_formatted}

### Behavioral Learnings

{behavioral_formatted}

## Required Report Structure

Generate a markdown report with the following sections:

### 1. # Bilan Final {week_number}

Main title with week number.

### 2. ## Objectifs vs Réalisé

Compare planned objectives to actual outcomes:
- What was planned (brief)
- What was achieved (with evidence from workout_history)
- TSS planned vs realized (percentage)
- Overall objective achievement assessment

**Format:**
```
**Objectifs planifiés:**
1. [Objective 1] ✅/❌
2. [Objective 2] ✅/❌
3. [Objective 3] ✅/❌

**TSS:** XXX/YYY (ZZ%) - [Commentary on achievement]

[2-3 sentences synthesizing objective achievement with specific evidence]
```

### 3. ## Métriques Finales

Present final metrics in table format:

| Métrique | Début Semaine | Fin Semaine | Évolution |
|----------|---------------|-------------|-----------|
| HRV | XX | XX | +/-X% ✅/❌ |
| CTL | XX | XX | +/-X ✅/❌ |
| ATL | XX | XX | +/-X ✅/❌ |
| TSB | XX | XX | +/-X ✅/❌ |

Brief analysis (2-3 sentences) on trends and their strategic significance.

### 4. ## Découvertes Majeures

**MAXIMUM 3-4 discoveries** - The most impactful findings only:

For each discovery:
```
### [Discovery Number]. [Discovery Title]
[2-3 sentences describing the discovery with specific metrics/evidence from workout_history]
```

**Criteria for major discoveries:**
- Protocol validations (e.g., "Z2 indoor 90min protocol validated")
- Performance breakthroughs (e.g., "SST capacity confirmed at 88% IF")
- Adaptation confirmations (e.g., "Recovery capacity optimal despite intensity")
- Strategic insights (e.g., "Indoor vs outdoor tolerance differential identified")

### 5. ## Séances Clés

Analyze 2-3 critical sessions (successes or learning opportunities):

**Format:**
```
**Session 1 - [Name] ([Date]):**
[1-2 sentences on why this session was critical and what it revealed]

**Session 2 - [Name] ([Date]):**
[1-2 sentences on strategic importance]
```

### 6. ## Protocoles Établis/Validés

List protocols that were established or validated this week:

**Format:**
```
1. **[Protocol Name]:** [Brief description with key parameters]
2. **[Protocol Name]:** [Brief description]
```

### 7. ## Ajustements Recommandés

3-5 actionable recommendations for next training cycle:

**Format:**
```
1. **[Recommendation Area]:** [Specific adjustment with rationale]
2. **[Recommendation Area]:** [Specific adjustment]
```

### 8. ## Enseignements Comportementaux

Behavioral insights observed during the week:
- Discipline patterns
- Recovery management
- Mental adaptations
- Consistency factors

**Format:**
```
- **[Behavioral Aspect]:** [Observation with implications]
- **[Behavioral Aspect]:** [Observation]
```

### 9. ## Conclusion

**EXACTLY 2-3 sentences** synthesizing:
- Overall week assessment
- Key validation or achievement
- Strategic direction for next phase

---

**Rapport généré avec [Claude Code](https://claude.com/claude-code) - Sprint R10 MVP**

## Quality Checklist

Before finalizing, verify:
- [ ] Week number {week_number} in title
- [ ] All objectives assessed (✅/❌)
- [ ] Maximum 3-4 major discoveries (not more!)
- [ ] All claims reference workout_history data
- [ ] Metrics table present and complete
- [ ] Conclusion is 2-3 sentences (not longer!)
- [ ] All text in French
- [ ] Strategic/synthesis tone throughout (not session details)
- [ ] Word count ≤ 1500 words

## Now Generate the Report

Using the workout_history summary and data provided above, generate the complete bilan_final report following the structure and guidelines exactly. Focus on synthesis and strategic insights, not session-by-session details.
"""

    return prompt


def _format_objectives(objectives: list[str]) -> str:
    """Format objectives list for prompt.

    Args:
        objectives: List of planned objectives

    Returns:
        Formatted objectives string
    """
    if not objectives:
        return "Aucun objectif spécifique défini."

    formatted = []
    for i, objective in enumerate(objectives, 1):
        formatted.append(f"{i}. {objective}")

    return "\n".join(formatted)


def _format_metrics_final(metrics_final: dict[str, Any]) -> str:
    """Format final metrics for prompt.

    Args:
        metrics_final: Dictionary with final metrics

    Returns:
        Formatted metrics string
    """
    if not metrics_final:
        return "Métriques finales non disponibles."

    # Extract start and end metrics if structured that way
    if "start" in metrics_final and "end" in metrics_final:
        start = metrics_final["start"]
        end = metrics_final["end"]

        return f"""**Début de semaine:**
- CTL: {start.get('ctl', 'N/A')}
- ATL: {start.get('atl', 'N/A')}
- TSB: {start.get('tsb', 'N/A')}
- HRV: {start.get('hrv', 'N/A')}

**Fin de semaine:**
- CTL: {end.get('ctl', 'N/A')}
- ATL: {end.get('atl', 'N/A')}
- TSB: {end.get('tsb', 'N/A')}
- HRV: {end.get('hrv', 'N/A')}
"""
    else:
        # Flat structure
        lines = []
        for key, value in metrics_final.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)


def _format_protocol_adaptations(adaptations: list[dict[str, Any]]) -> str:
    """Format protocol adaptations for prompt.

    Args:
        adaptations: List of protocol adaptation dicts

    Returns:
        Formatted adaptations string
    """
    if not adaptations:
        return "Aucune adaptation de protocole identifiée."

    formatted = []
    for i, adaptation in enumerate(adaptations, 1):
        title = adaptation.get("title", "Adaptation")
        description = adaptation.get("description", "")
        formatted.append(
            f"""**Adaptation {i}: {title}**
- Description: {description}
"""
        )

    return "\n".join(formatted)


def _format_key_sessions(sessions: list[dict[str, Any]]) -> str:
    """Format key sessions for prompt.

    Args:
        sessions: List of key session dicts

    Returns:
        Formatted sessions string
    """
    if not sessions:
        return "Séances clés à extraire du workout_history summary."

    formatted = []
    for i, session in enumerate(sessions, 1):
        name = session.get("name", "Session")
        date = session.get("date", "")
        significance = session.get("significance", "")
        formatted.append(
            f"""**Session {i}: {name}** ({date})
- Importance: {significance}
"""
        )

    return "\n".join(formatted)


def _format_behavioral_learnings(learnings: list[dict[str, Any]]) -> str:
    """Format behavioral learnings for prompt.

    Args:
        learnings: List of behavioral learning dicts

    Returns:
        Formatted learnings string
    """
    if not learnings:
        return "Enseignements comportementaux à extraire du workout_history summary."

    formatted = []
    for i, learning in enumerate(learnings, 1):
        aspect = learning.get("aspect", "Comportement")
        observation = learning.get("observation", "")
        formatted.append(
            f"""**Learning {i}: {aspect}**
- Observation: {observation}
"""
        )

    return "\n".join(formatted)
