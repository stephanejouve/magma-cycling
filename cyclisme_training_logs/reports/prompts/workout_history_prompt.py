"""Workout History AI Prompt Builder.

Constructs AI prompts for workout_history report generation.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""

from typing import Any


def build_workout_history_prompt(week_data: dict[str, Any]) -> str:
    """Build AI prompt for workout_history report generation.

    Constructs comprehensive prompt including:
    - System instructions (role, style, constraints)
    - Week context (TSS, activities, wellness)
    - Training intelligence (learnings, patterns)
    - Output format specification
    - Example report structure (few-shot learning)

    Args:
        week_data: Dictionary with all week data
            - week_number: str (e.g., "S076")
            - start_date: str (ISO format: "2026-01-13")
            - end_date: str (ISO format: "2026-01-19")
            - tss_planned: int (Planned TSS for week)
            - tss_realized: int (Actual TSS realized)
            - activities: list[dict] (Intervals.icu activities)
            - wellness_data: dict (HRV, sleep, etc.)
            - learnings: list[dict] (Training intelligence)
            - metrics_evolution: dict (start vs end metrics)

    Returns:
        Complete AI prompt string

    Raises:
        ValueError: If required data missing

    Examples:
        >>> week_data = {"week_number": "S076", "activities": [...]}
        >>> prompt = build_workout_history_prompt(week_data)
        >>> "expert cycling coach" in prompt
        True
    """
    # Validate required data
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

    # Build activities summary
    activities_summary = _format_activities(activities)

    # Build wellness summary
    wellness_summary = _format_wellness(wellness_data)

    # Build learnings summary
    learnings_summary = _format_learnings(learnings)

    # Build metrics evolution summary
    metrics_summary = _format_metrics_evolution(metrics_evolution)

    # Construct full prompt
    prompt = f"""You are an expert cycling coach analyzing training data to create a comprehensive workout history report.

## Your Role

You are writing a **factual, data-driven** workout history report in **French** for week {week_number} ({start_date} to {end_date}). Your goal is to provide a detailed chronological account of all training sessions with precise metrics and observations.

## Critical Constraints

1. **NO HALLUCINATIONS**: Use ONLY the data provided below. Do not invent metrics, sessions, or details.
2. **Factual Tone**: Be professional, technical, and objective. No speculation.
3. **Verifiable Metrics**: Every number must match the source data exactly.
4. **Chronological Order**: Sessions must be presented in date order.
5. **French Language**: All text in French, technical terms in French cycling vocabulary.
6. **Word Limit**: Maximum 2000 words total.

## Week Context

**Semaine:** {week_number}
**Dates:** {start_date} au {end_date}
**TSS Planifié:** {tss_planned}
**TSS Réalisé:** {tss_realized} ({_calculate_tss_percentage(tss_planned, tss_realized)}%)

## Training Sessions Data

{activities_summary}

## Wellness Metrics

{wellness_summary}

## Training Intelligence Learnings

{learnings_summary}

## Metrics Evolution (Start vs End)

{metrics_summary}

## Required Report Structure

Generate a markdown report with the following sections:

### 1. # Workout History {week_number}

Main title with week number.

### 2. ## Contexte Semaine

Brief overview (3-4 sentences):
- Week dates and TSS (planned vs realized)
- Training phase/objectives
- Overall wellness trends
- Key context (weather, travel, life constraints if relevant)

### 3. ## Chronologie Complète

Detailed session-by-session chronology in DATE ORDER. For each session:

**Format:**
```
### [Day] [Date] - [Session Name]
**TSS:** X | **IF:** 0.XX | **Durée:** XXmin
**Objectif:** [Session objective if known]

[2-3 paragraphs describing]:
- Session details (intervals, zones, structure)
- Key metrics (power, HR, RPE)
- Wellness pre-session (HRV, sleep, readiness)
- Observations (feelings, adaptations, difficulties)
- Discoveries or insights from this session
```

**Example:**
```
### Lundi 13 Janvier - Z2 Base Indoor
**TSS:** 85 | **IF:** 0.72 | **Durée:** 90min
**Objectif:** Valider protocole Z2 indoor prolongé

Première validation du protocole Z2 indoor sur 90 minutes. Maintien stable à 72% IF (180W NP) avec fréquence cardiaque moyenne de 135 bpm. Aucune dérive cardiaque observée sur la durée, confirmant l'adaptation au format indoor prolongé.

Wellness pré-séance: HRV 58, Readiness 8.1/10, qualité sommeil 7.5/10. Conditions optimales pour validation protocole.

**Découverte majeure:** Protocole validé - capacité confirmée à maintenir 90min Z2 indoor sans dégradation.
```

### 4. ## Métriques Évolution

Table showing metrics evolution:

| Métrique | Début Semaine | Fin Semaine | Évolution |
|----------|---------------|-------------|-----------|
| HRV | XX | XX | +/-X% |
| CTL | XX | XX | +/-X |
| ATL | XX | XX | +/-X |
| TSB | XX | XX | +/-X |

Brief analysis (2-3 sentences) of trends and their significance.

### 5. ## Enseignements Majeurs

3-5 bullet points of key learnings from the week:
- Protocol validations
- Performance discoveries
- Adaptation observations
- Behavioral insights
- Future applications

**Format:**
```
- **[Learning Title]:** [2-3 sentence description with specific metrics/evidence]
```

### 6. ## Recommandations

3-5 actionable recommendations for next week:
- Training adjustments
- Protocol refinements
- Monitoring points
- Recovery strategies

---

**Rapport généré avec [Claude Code](https://claude.com/claude-code) - Sprint R10 MVP**

## Quality Checklist

Before finalizing, verify:
- [ ] All sessions in chronological order
- [ ] All TSS values match source data exactly
- [ ] Week number {week_number} appears in title
- [ ] All required sections present
- [ ] All text in French
- [ ] No invented metrics or sessions
- [ ] Word count ≤ 2000 words
- [ ] Professional, factual tone throughout

## Now Generate the Report

Using the data provided above, generate the complete workout history report following the structure and guidelines exactly.
"""

    return prompt


def _format_activities(activities: list[dict[str, Any]]) -> str:
    """Format activities list for prompt.

    Args:
        activities: List of activity dictionaries from Intervals.icu

    Returns:
        Formatted activities summary string
    """
    if not activities:
        return "Aucune activité enregistrée cette semaine."

    summary_lines = []
    for i, activity in enumerate(activities, 1):
        name = activity.get("name", "Session sans nom")
        date = activity.get("start_date", "Date inconnue")
        activity_type = activity.get("type", "Ride")
        tss = activity.get("tss", 0)
        duration = activity.get("moving_time", 0) // 60  # Convert to minutes
        if_val = activity.get("if_", 0.0)
        np = activity.get("np", 0)
        avg_hr = activity.get("avg_hr", 0)
        indoor = activity.get("indoor", False)

        summary_lines.append(
            f"""**Session {i}: {name}**
- Date: {date}
- Type: {activity_type} ({'Indoor' if indoor else 'Outdoor'})
- TSS: {tss}
- Durée: {duration} minutes
- IF: {if_val:.2f}
- NP: {np}W
- FC moyenne: {avg_hr} bpm
"""
        )

    return "\n".join(summary_lines)


def _format_wellness(wellness_data: dict[str, Any]) -> str:
    """Format wellness data for prompt.

    Args:
        wellness_data: Dictionary with wellness metrics

    Returns:
        Formatted wellness summary string
    """
    hrv_avg = wellness_data.get("hrv_avg", "N/A")
    hrv_trend = wellness_data.get("hrv_trend", "stable")
    sleep_avg = wellness_data.get("sleep_quality_avg", "N/A")
    fatigue_avg = wellness_data.get("fatigue_score_avg", "N/A")
    readiness_avg = wellness_data.get("readiness_avg", "N/A")

    return f"""- **HRV moyenne:** {hrv_avg} (tendance: {hrv_trend})
- **Qualité sommeil moyenne:** {sleep_avg}/10
- **Score fatigue moyen:** {fatigue_avg}/10
- **Readiness moyenne:** {readiness_avg}/10
"""


def _format_learnings(learnings: list[dict[str, Any]]) -> str:
    """Format training intelligence learnings for prompt.

    Args:
        learnings: List of learning dictionaries

    Returns:
        Formatted learnings summary string
    """
    if not learnings:
        return "Aucun apprentissage spécifique enregistré."

    summary_lines = []
    for i, learning in enumerate(learnings, 1):
        learning_type = learning.get("type", "general")
        title = learning.get("title", "Apprentissage")
        description = learning.get("description", "")
        confidence = learning.get("confidence", "medium")

        summary_lines.append(
            f"""**Learning {i}: {title}**
- Type: {learning_type}
- Description: {description}
- Confiance: {confidence}
"""
        )

    return "\n".join(summary_lines)


def _format_metrics_evolution(metrics_evolution: dict[str, Any]) -> str:
    """Format metrics evolution for prompt.

    Args:
        metrics_evolution: Dictionary with start/end metrics

    Returns:
        Formatted metrics evolution string
    """
    start_metrics = metrics_evolution.get("start", {})
    end_metrics = metrics_evolution.get("end", {})

    if not start_metrics or not end_metrics:
        return "Données d'évolution non disponibles."

    return f"""**Début de semaine:**
- CTL: {start_metrics.get('ctl', 'N/A')}
- ATL: {start_metrics.get('atl', 'N/A')}
- TSB: {start_metrics.get('tsb', 'N/A')}
- HRV: {start_metrics.get('hrv', 'N/A')}

**Fin de semaine:**
- CTL: {end_metrics.get('ctl', 'N/A')}
- ATL: {end_metrics.get('atl', 'N/A')}
- TSB: {end_metrics.get('tsb', 'N/A')}
- HRV: {end_metrics.get('hrv', 'N/A')}
"""


def _calculate_tss_percentage(tss_planned: int, tss_realized: int) -> int:
    """Calculate TSS realization percentage.

    Args:
        tss_planned: Planned TSS
        tss_realized: Realized TSS

    Returns:
        Percentage (rounded to nearest integer)
    """
    if tss_planned == 0:
        return 0
    return round((tss_realized / tss_planned) * 100)
