"""Bilan Final AI Prompt Builder.

Constructs AI prompts for bilan_final report generation.

Author: Claude Code (Sprint R10 MVP - Day 3)
Created: 2026-01-18
"""

from typing import Any

from cyclisme_training_logs.reports.prompts.workout_history_prompt import (
    _calculate_tss_percentage,
    _format_activities,
    _format_learnings,
    _format_metrics_evolution,
    _format_wellness,
)


def build_bilan_final_prompt(week_data: dict[str, Any]) -> str:
    """Build AI prompt for bilan_final report generation.

    Constructs synthesis-focused prompt including:
    - System instructions (synthesis role, strategic focus)
    - Week context and activities (raw data)
    - Metrics evolution
    - Output format specification

    Args:
        week_data: Dictionary with all week data (same structure as workout_history)
            - week_number: str (e.g., "S076")
            - start_date: str (ISO format)
            - end_date: str (ISO format)
            - tss_planned: int
            - tss_realized: int
            - activities: list[dict] (activity details)
            - wellness_data: dict (HRV, sleep, etc.)
            - learnings: list[dict] (training intelligence)
            - metrics_evolution: dict (start/end metrics)

    Returns:
        Complete AI prompt string

    Raises:
        ValueError: If required data missing

    Examples:
        >>> week_data = {"week_number": "S076", "activities": [...]}
        >>> prompt = build_bilan_final_prompt(week_data)
        >>> "strategic cycling coach" in prompt.lower()
        True
    """
    # Validate required data (same as workout_history)
    required_fields = [
        "week_number",
        "start_date",
        "end_date",
        "tss_planned",
        "tss_realized",
        "activities",
        "wellness_data",
        "learnings",
        "metrics_evolution",
    ]
    for field in required_fields:
        if field not in week_data:
            raise ValueError(f"Missing required field: {field}")

    # Extract data
    week_number = week_data["week_number"]
    start_date = week_data["start_date"]
    end_date = week_data["end_date"]
    tss_planned = week_data["tss_planned"]
    tss_realized = week_data["tss_realized"]
    activities = week_data["activities"]
    wellness_data = week_data["wellness_data"]
    learnings = week_data["learnings"]
    metrics_evolution = week_data["metrics_evolution"]

    # Calculate TSS percentage
    tss_percentage = _calculate_tss_percentage(tss_planned, tss_realized)

    # Format activities (use workout_history formatter)
    activities_formatted = _format_activities(activities)

    # Format wellness
    wellness_formatted = _format_wellness(wellness_data)

    # Format learnings
    learnings_formatted = _format_learnings(learnings)

    # Format metrics evolution (start vs end)
    metrics_formatted = _format_metrics_evolution(metrics_evolution)

    # Construct full prompt
    prompt = f"""You are a strategic cycling coach synthesizing weekly training outcomes into a comprehensive final assessment.

## Your Role

You are writing a **strategic, synthesis-focused** final assessment report in **French** for week {week_number} ({start_date} to {end_date}). Your goal is to extract high-level insights, validate protocols, and provide actionable recommendations for future training.

## Critical Constraints

1. **SYNTHESIS FOCUS**: Extract high-level patterns, NOT session-by-session details
2. **STRATEGIC TONE**: Focus on learnings, protocols, and future applications
3. **DATA-DRIVEN**: All claims must be supported by activity data and learnings provided
4. **MAX 3-4 DISCOVERIES**: Limit major discoveries to the most impactful findings
5. **CONCISE CONCLUSION**: 2-3 sentences maximum for conclusion
6. **French Language**: All text in French, professional cycling vocabulary
7. **Word Limit**: Maximum 1500 words total

## Week Context: {week_number}

**Dates:** {start_date} to {end_date}
**TSS Planned:** {tss_planned} | **TSS Realized:** {tss_realized} ({tss_percentage}%)

### Activities Summary

{activities_formatted}

### Wellness Data

{wellness_formatted}

### Training Intelligence Learnings

{learnings_formatted}

### Metrics Evolution (Start → End)

{metrics_formatted}

## Required Report Structure

Generate a markdown report with the following sections:

### 1. # Bilan Final {week_number}

Main title with week number.

### 2. ## Semaine en Chiffres

Synthesize the week's key metrics and outcomes:
- TSS planned vs realized with percentage
- Total sessions completed
- Key intensity markers (IF ranges, durations)
- Overall execution assessment

**Format:**
```
**Charge d'entraînement:**
- TSS: {tss_realized}/{tss_planned} ({tss_percentage}%)
- Séances: [X] complétées
- Focus principal: [Type d'entraînement observé]

[2-3 sentences synthesizing the week's training load and execution patterns]
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

Using the activities, learnings, and metrics data provided above, generate the complete bilan_final report following the structure and guidelines exactly. Focus on synthesis and strategic insights, not session-by-session details.
"""

    return prompt
