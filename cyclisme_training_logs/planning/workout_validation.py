#!/usr/bin/env python3
"""
Workout validation before prescription (Peaks Coaching principles).

Validates workout appropriateness based on athlete state, recovery metrics,
and recent training history according to Section 11.2 of Peaks methodology.

Author: Stéphane Jouve
Created: 2026-02-14
"""

from dataclasses import dataclass
from enum import Enum


class ValidationResult(str, Enum):
    """Validation result status."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class WorkoutCheck:
    """Single validation check result."""

    check_name: str
    result: ValidationResult
    message: str
    severity: str  # "info", "warning", "critical"


@dataclass
class WorkoutValidation:
    """Complete workout validation results."""

    workout_name: str
    intensity_zone: str
    overall_result: ValidationResult
    checks: list[WorkoutCheck]
    safe_to_prescribe: bool
    recommendations: list[str]


def validate_workout(
    workout_name: str,
    intensity_zone: str,  # "VO2", "FTP", "Sweet-Spot", "Tempo", "Endurance", "Recovery"
    duration_minutes: int,
    tss: int,
    athlete_state: dict,
    recent_workouts: list[dict] | None = None,
) -> WorkoutValidation:
    """
    Validate workout before prescription according to Peaks Coaching rules.

    Implements validation checklist from Section 11.2:
    - TSB appropriateness for intensity
    - Sleep sufficiency for high intensity
    - Recent high-intensity workouts (48h rule)
    - Expected decoupling thresholds
    - Workout placement in week
    - Volume coherence with weekly target

    Args:
        workout_name: Workout identifier
        intensity_zone: Primary intensity zone (VO2, FTP, Sweet-Spot, etc.)
        duration_minutes: Workout duration in minutes
        tss: Training Stress Score
        athlete_state: Dict with TSB, sleep_hours, weekly_tss_target, day_of_week
        recent_workouts: List of recent workouts (last 48-72h) with intensity info

    Returns:
        WorkoutValidation with overall result and detailed checks

    Examples:
        >>> athlete = {
        ...     "tsb": 3.0,
        ...     "sleep_hours": 6.5,
        ...     "weekly_tss_target": 350,
        ...     "day_of_week": "Tuesday"
        ... }
        >>> validation = validate_workout(
        ...     "VO2max-intervals",
        ...     "VO2",
        ...     45,
        ...     65,
        ...     athlete
        ... )
        >>> validation.safe_to_prescribe
        False  # TSB too low, sleep insufficient
    """
    checks = []
    recommendations = []
    overall_result = ValidationResult.PASS

    # Check 1: TSB appropriateness for intensity
    tsb = athlete_state.get("tsb", 0)

    if intensity_zone == "VO2":
        if tsb < 5:
            checks.append(
                WorkoutCheck(
                    check_name="TSB VO2",
                    result=ValidationResult.FAIL,
                    message=f"TSB insuffisant pour VO2: {tsb:+.1f} < +5 requis",
                    severity="critical",
                )
            )
            overall_result = ValidationResult.FAIL
            recommendations.append("Remplacer par Tempo ou Sweet-Spot jusqu'à TSB >+5")
        elif tsb < 10:
            checks.append(
                WorkoutCheck(
                    check_name="TSB VO2",
                    result=ValidationResult.WARNING,
                    message=f"TSB limite pour VO2: {tsb:+.1f} (optimal >+10)",
                    severity="warning",
                )
            )
            if overall_result == ValidationResult.PASS:
                overall_result = ValidationResult.WARNING
        else:
            checks.append(
                WorkoutCheck(
                    check_name="TSB VO2",
                    result=ValidationResult.PASS,
                    message=f"TSB optimal pour VO2: {tsb:+.1f}",
                    severity="info",
                )
            )

    elif intensity_zone == "FTP":
        if tsb < -10:
            checks.append(
                WorkoutCheck(
                    check_name="TSB FTP",
                    result=ValidationResult.FAIL,
                    message=f"TSB trop négatif pour FTP: {tsb:+.1f} < -10",
                    severity="critical",
                )
            )
            overall_result = ValidationResult.FAIL
            recommendations.append("Semaine récupération nécessaire (TSS 250-280)")
        elif tsb < 0:
            checks.append(
                WorkoutCheck(
                    check_name="TSB FTP",
                    result=ValidationResult.WARNING,
                    message=f"TSB négatif pour FTP: {tsb:+.1f}",
                    severity="warning",
                )
            )
            if overall_result == ValidationResult.PASS:
                overall_result = ValidationResult.WARNING
        else:
            checks.append(
                WorkoutCheck(
                    check_name="TSB FTP",
                    result=ValidationResult.PASS,
                    message=f"TSB acceptable pour FTP: {tsb:+.1f}",
                    severity="info",
                )
            )

    # Check 2: Sleep sufficiency for high intensity
    sleep_hours = athlete_state.get("sleep_hours")

    if intensity_zone in ["VO2", "AC", "FTP"] and sleep_hours is not None:
        if sleep_hours < 7.0:
            checks.append(
                WorkoutCheck(
                    check_name="Sommeil haute intensité",
                    result=ValidationResult.FAIL,
                    message=f"Sommeil insuffisant: {sleep_hours:.1f}h < 7h requis",
                    severity="critical",
                )
            )
            overall_result = ValidationResult.FAIL
            recommendations.append("Reporter séance haute intensité après récupération sommeil")
        else:
            checks.append(
                WorkoutCheck(
                    check_name="Sommeil haute intensité",
                    result=ValidationResult.PASS,
                    message=f"Sommeil suffisant: {sleep_hours:.1f}h",
                    severity="info",
                )
            )

    # Check 3: Recent high-intensity workouts (48h rule)
    if recent_workouts:
        high_intensity_48h = sum(
            1
            for w in recent_workouts
            if w.get("intensity_zone") in ["VO2", "FTP", "AC"] and w.get("hours_ago", 999) < 48
        )

        if intensity_zone in ["VO2", "AC"] and high_intensity_48h > 0:
            checks.append(
                WorkoutCheck(
                    check_name="Récupération 48h",
                    result=ValidationResult.WARNING,
                    message=f"Intensité élevée détectée <48h ({high_intensity_48h}x)",
                    severity="warning",
                )
            )
            if overall_result == ValidationResult.PASS:
                overall_result = ValidationResult.WARNING
            recommendations.append("Surveiller fatigue accumulée, adapter intensité si nécessaire")

    # Check 4: Expected decoupling thresholds
    if duration_minutes > 60:
        if intensity_zone == "Sweet-Spot":
            expected_decoupling = 5.0
            checks.append(
                WorkoutCheck(
                    check_name="Découplage attendu",
                    result=ValidationResult.PASS,
                    message=f"<{expected_decoupling + 2.5:.1f}% acceptable (optimal <{expected_decoupling:.1f}%)",
                    severity="info",
                )
            )
        elif intensity_zone == "FTP":
            expected_decoupling = 8.0
            checks.append(
                WorkoutCheck(
                    check_name="Découplage attendu",
                    result=ValidationResult.PASS,
                    message=f"<{expected_decoupling + 2:.0f}% acceptable (optimal <{expected_decoupling:.0f}%)",
                    severity="info",
                )
            )

    # Check 5: Workout placement in week
    day_of_week = athlete_state.get("day_of_week", "").lower()

    if intensity_zone == "Recovery" and day_of_week == "wednesday":
        checks.append(
            WorkoutCheck(
                check_name="Placement semaine",
                result=ValidationResult.WARNING,
                message="Récupération milieu semaine inhabituel",
                severity="warning",
            )
        )

    if intensity_zone == "VO2" and day_of_week not in ["tuesday", "thursday"]:
        checks.append(
            WorkoutCheck(
                check_name="Placement semaine",
                result=ValidationResult.WARNING,
                message=f"VO2 généralement placé mardi/jeudi (actuel: {day_of_week})",
                severity="warning",
            )
        )

    # Check 6: Volume coherence with weekly target
    weekly_tss_target = athlete_state.get("weekly_tss_target")

    if weekly_tss_target and tss > (weekly_tss_target * 0.30):
        checks.append(
            WorkoutCheck(
                check_name="Volume cohérence",
                result=ValidationResult.WARNING,
                message=f"Séance importante: {tss} TSS = {(tss / weekly_tss_target) * 100:.0f}% TSS hebdo",
                severity="warning",
            )
        )
        recommendations.append("S'assurer que volume restant semaine est gérable")

    # Check 7: "Junk miles" prevention
    if intensity_zone == "Endurance" and duration_minutes > 90 and tss < 60:
        checks.append(
            WorkoutCheck(
                check_name="Anti junk miles",
                result=ValidationResult.WARNING,
                message=f"Longue durée ({duration_minutes}min) mais TSS faible ({tss})",
                severity="warning",
            )
        )
        recommendations.append(
            "Assurer structure claire: Z2 strict ou inclure blocs Tempo/Sweet-Spot"
        )

    # Determine safe to prescribe
    safe_to_prescribe = overall_result != ValidationResult.FAIL

    return WorkoutValidation(
        workout_name=workout_name,
        intensity_zone=intensity_zone,
        overall_result=overall_result,
        checks=checks,
        safe_to_prescribe=safe_to_prescribe,
        recommendations=recommendations,
    )


def format_validation_report(validation: WorkoutValidation) -> str:
    """
    Format validation results as markdown.

    Args:
        validation: WorkoutValidation from validate_workout()

    Returns:
        Markdown formatted validation report
    """
    result_icons = {
        ValidationResult.PASS: "✅",
        ValidationResult.WARNING: "⚠️",
        ValidationResult.FAIL: "❌",
    }

    icon = result_icons[validation.overall_result]
    md = f"## Validation Séance: {validation.workout_name}\n\n"
    md += f"**Résultat global:** {icon} {validation.overall_result.value.upper()}\n"
    md += f"**Zone intensité:** {validation.intensity_zone}\n"
    md += f"**Prescription sûre:** {'Oui' if validation.safe_to_prescribe else 'Non'}\n\n"

    if validation.checks:
        md += "### Checks de Validation\n\n"
        for check in validation.checks:
            check_icon = result_icons[check.result]
            md += f"- {check_icon} **{check.check_name}:** {check.message}\n"
        md += "\n"

    if validation.recommendations:
        md += "### Recommandations\n\n"
        for rec in validation.recommendations:
            md += f"- {rec}\n"
        md += "\n"

    return md
