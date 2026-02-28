#!/usr/bin/env python3
"""
Outdoor discipline monitoring (Peaks Coaching principles).

Detects discipline failures during outdoor workouts (IF overload >10%)
and recommends switching to indoor for specific zones after repeated failures.

Based on Hunter Allen methodology - outdoor discipline critical for effective training.

Author: Stéphane Jouve
Created: 2026-02-14
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum


class DisciplineStatus(str, Enum):
    """Discipline status for a workout."""

    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"


class EnvironmentRecommendation(str, Enum):
    """Environment recommendation for future workouts."""

    OUTDOOR_OK = "outdoor_ok"
    INDOOR_PREFERRED = "indoor_preferred"
    INDOOR_REQUIRED = "indoor_required"


@dataclass
class DisciplineCheck:
    """Single discipline check result."""

    workout_date: date
    workout_name: str
    intensity_zone: str
    environment: str  # "outdoor" or "indoor"
    if_planned: float
    if_actual: float
    if_deviation_percent: float
    status: DisciplineStatus
    message: str


@dataclass
class DisciplineHistory:
    """Historical discipline tracking for a zone."""

    zone: str
    total_outdoor_workouts: int
    failure_count: int
    last_failure_date: date | None
    consecutive_failures: int
    environment_recommendation: EnvironmentRecommendation
    recommendation_reason: str


@dataclass
class DisciplineReport:
    """Complete discipline analysis report."""

    check: DisciplineCheck
    zone_history: DisciplineHistory | None
    overall_recommendation: EnvironmentRecommendation
    alert_message: str | None
    recovery_period_months: int | None


def calculate_if_deviation(if_actual: float, if_planned: float) -> float:
    """
    Calculate IF deviation percentage.

    Args:
        if_actual: Actual Intensity Factor from workout
        if_planned: Planned Intensity Factor

    Returns:
        Deviation percentage (positive = overload, negative = underload)

    Examples:
        >>> calculate_if_deviation(0.85, 0.75)
        13.33  # 13.33% overload
        >>> calculate_if_deviation(0.70, 0.75)
        -6.67  # 6.67% underload
    """
    if if_planned == 0:
        return 0.0

    deviation = ((if_actual - if_planned) / if_planned) * 100
    return round(deviation, 2)


def check_discipline(
    workout_name: str,
    workout_date: date,
    intensity_zone: str,
    environment: str,
    if_planned: float,
    if_actual: float,
) -> DisciplineCheck:
    """
    Check discipline for a single workout.

    According to Peaks Coaching:
    - IF deviation >10% = discipline failure
    - Outdoor workouts are high risk for discipline failures
    - Indoor workouts provide better control

    Args:
        workout_name: Workout identifier
        workout_date: Date of workout execution
        intensity_zone: Intensity zone (VO2, FTP, Sweet-Spot, Tempo, Endurance, Recovery)
        environment: "outdoor" or "indoor"
        if_planned: Planned Intensity Factor (0.0-1.0)
        if_actual: Actual Intensity Factor from workout

    Returns:
        DisciplineCheck with status and message

    Examples:
        >>> check = check_discipline(
        ...     "VO2-intervals",
        ...     date(2026, 2, 14),
        ...     "VO2",
        ...     "outdoor",
        ...     0.90,
        ...     1.02
        ... )
        >>> check.status
        <DisciplineStatus.FAILURE: 'failure'>
    """
    if_deviation = calculate_if_deviation(if_actual, if_planned)

    # Determine status based on deviation
    if if_deviation > 10.0:
        status = DisciplineStatus.FAILURE
        message = (
            f"Échec discipline: IF réel {if_actual:.2f} vs prévu {if_planned:.2f} "
            f"(surcharge +{if_deviation:.1f}%)"
        )
    elif if_deviation > 5.0:
        status = DisciplineStatus.WARNING
        message = (
            f"Discipline limite: IF réel {if_actual:.2f} vs prévu {if_planned:.2f} "
            f"(dérive +{if_deviation:.1f}%)"
        )
    elif if_deviation < -10.0:
        status = DisciplineStatus.WARNING
        message = (
            f"Sous-intensité: IF réel {if_actual:.2f} vs prévu {if_planned:.2f} "
            f"(déficit {if_deviation:.1f}%)"
        )
    else:
        status = DisciplineStatus.SUCCESS
        message = f"Discipline respectée: IF réel {if_actual:.2f} vs prévu {if_planned:.2f} ({if_deviation:+.1f}%)"

    return DisciplineCheck(
        workout_date=workout_date,
        workout_name=workout_name,
        intensity_zone=intensity_zone,
        environment=environment,
        if_planned=if_planned,
        if_actual=if_actual,
        if_deviation_percent=if_deviation,
        status=status,
        message=message,
    )


def analyze_zone_history(
    zone: str,
    recent_checks: list[DisciplineCheck],
    failure_threshold: int = 2,
) -> DisciplineHistory:
    """
    Analyze historical discipline for a specific zone.

    According to Peaks Coaching methodology:
    - 2+ outdoor failures on a zone → recommend indoor
    - Outdoor reserved for Z1-Z2 only after failures
    - Recovery period: 2-3 months indoor before retry

    Args:
        zone: Intensity zone to analyze
        recent_checks: List of recent DisciplineCheck for this zone
        failure_threshold: Number of failures before recommending indoor (default: 2)

    Returns:
        DisciplineHistory with recommendation

    Examples:
        >>> checks = [
        ...     DisciplineCheck(..., status=DisciplineStatus.FAILURE, ...),
        ...     DisciplineCheck(..., status=DisciplineStatus.FAILURE, ...),
        ... ]
        >>> history = analyze_zone_history("VO2", checks)
        >>> history.environment_recommendation
        <EnvironmentRecommendation.INDOOR_REQUIRED: 'indoor_required'>
    """
    # Filter outdoor checks only
    outdoor_checks = [c for c in recent_checks if c.environment == "outdoor"]

    if not outdoor_checks:
        return DisciplineHistory(
            zone=zone,
            total_outdoor_workouts=0,
            failure_count=0,
            last_failure_date=None,
            consecutive_failures=0,
            environment_recommendation=EnvironmentRecommendation.OUTDOOR_OK,
            recommendation_reason="Aucune séance outdoor récente pour cette zone",
        )

    # Count failures
    failures = [c for c in outdoor_checks if c.status == DisciplineStatus.FAILURE]
    failure_count = len(failures)

    # Find consecutive failures (most recent)
    consecutive_failures = 0
    for check in reversed(outdoor_checks):
        if check.status == DisciplineStatus.FAILURE:
            consecutive_failures += 1
        else:
            break

    # Last failure date
    last_failure_date = failures[-1].workout_date if failures else None

    # Determine recommendation
    if failure_count >= failure_threshold:
        recommendation = EnvironmentRecommendation.INDOOR_REQUIRED
        reason = (
            f"{failure_count} échecs discipline outdoor détectés. "
            f"Recommandation Peaks Coaching: indoor obligatoire pour {zone}. "
            f"Retour outdoor après 2-3 mois discipline indoor validée."
        )
    elif failure_count > 0:
        recommendation = EnvironmentRecommendation.INDOOR_PREFERRED
        reason = (
            f"{failure_count} échec(s) discipline outdoor. "
            f"Indoor préférable pour garantir intensité correcte en {zone}."
        )
    else:
        recommendation = EnvironmentRecommendation.OUTDOOR_OK
        reason = f"Discipline outdoor validée pour {zone}"

    return DisciplineHistory(
        zone=zone,
        total_outdoor_workouts=len(outdoor_checks),
        failure_count=failure_count,
        last_failure_date=last_failure_date,
        consecutive_failures=consecutive_failures,
        environment_recommendation=recommendation,
        recommendation_reason=reason,
    )


def generate_discipline_report(
    current_check: DisciplineCheck,
    zone_history: DisciplineHistory | None = None,
) -> DisciplineReport:
    """
    Generate complete discipline report with recommendations.

    Args:
        current_check: Current workout discipline check
        zone_history: Historical discipline for this zone (optional)

    Returns:
        DisciplineReport with alert message and recommendations

    Examples:
        >>> check = DisciplineCheck(..., status=DisciplineStatus.FAILURE, ...)
        >>> history = DisciplineHistory(..., failure_count=2, ...)
        >>> report = generate_discipline_report(check, history)
        >>> report.alert_message
        '⚠️ ALERTE DISCIPLINE OUTDOOR...'
    """
    # Determine overall recommendation
    if (
        zone_history
        and zone_history.environment_recommendation == EnvironmentRecommendation.INDOOR_REQUIRED
    ):
        overall_recommendation = EnvironmentRecommendation.INDOOR_REQUIRED
        recovery_period_months = 3  # 2-3 months recommended
        alert_message = (
            f"⚠️ ALERTE DISCIPLINE OUTDOOR - {current_check.intensity_zone}\n\n"
            f"Échecs répétés détectés: {zone_history.failure_count}x\n"
            f"Dernier échec: {zone_history.last_failure_date}\n\n"
            f"RECOMMANDATION PEAKS COACHING:\n"
            f"- Indoor OBLIGATOIRE pour zone {current_check.intensity_zone}\n"
            f"- Outdoor réservé Z1-Z2 uniquement\n"
            f"- Retour outdoor après {recovery_period_months} mois discipline indoor validée\n\n"
            f"Dernière séance ({current_check.workout_name}):\n"
            f"{current_check.message}"
        )
    elif current_check.status == DisciplineStatus.FAILURE:
        overall_recommendation = EnvironmentRecommendation.INDOOR_PREFERRED
        recovery_period_months = None
        alert_message = (
            f"⚠️ ÉCHEC DISCIPLINE - {current_check.workout_name}\n\n"
            f"{current_check.message}\n\n"
            f"RECOMMANDATION: Privilégier indoor pour garantir intensité correcte."
        )
    elif current_check.status == DisciplineStatus.WARNING:
        overall_recommendation = EnvironmentRecommendation.INDOOR_PREFERRED
        recovery_period_months = None
        alert_message = (
            f"⚠️ DISCIPLINE LIMITE - {current_check.workout_name}\n\n"
            f"{current_check.message}\n\n"
            f"Surveiller prochaine séance similaire."
        )
    else:
        overall_recommendation = EnvironmentRecommendation.OUTDOOR_OK
        recovery_period_months = None
        alert_message = None

    return DisciplineReport(
        check=current_check,
        zone_history=zone_history,
        overall_recommendation=overall_recommendation,
        alert_message=alert_message,
        recovery_period_months=recovery_period_months,
    )


def format_discipline_report(report: DisciplineReport) -> str:
    """
    Format discipline report as markdown.

    Args:
        report: DisciplineReport from generate_discipline_report()

    Returns:
        Markdown formatted report

    Examples:
        >>> report = DisciplineReport(...)
        >>> print(format_discipline_report(report))
        ## Analyse Discipline Outdoor
        ...
    """
    status_icons = {
        DisciplineStatus.SUCCESS: "✅",
        DisciplineStatus.WARNING: "⚠️",
        DisciplineStatus.FAILURE: "❌",
    }

    recommendation_icons = {
        EnvironmentRecommendation.OUTDOOR_OK: "✅",
        EnvironmentRecommendation.INDOOR_PREFERRED: "⚠️",
        EnvironmentRecommendation.INDOOR_REQUIRED: "🚨",
    }

    icon = status_icons[report.check.status]
    rec_icon = recommendation_icons[report.overall_recommendation]

    md = "## Analyse Discipline Outdoor\n\n"
    md += f"**Séance:** {report.check.workout_name} ({report.check.workout_date})\n"
    md += f"**Zone:** {report.check.intensity_zone}\n"
    md += f"**Environnement:** {report.check.environment}\n\n"

    md += "### Check Discipline\n\n"
    md += f"{icon} **Statut:** {report.check.status.value.upper()}\n"
    md += f"- IF prévu: {report.check.if_planned:.2f}\n"
    md += f"- IF réel: {report.check.if_actual:.2f}\n"
    md += f"- Déviation: {report.check.if_deviation_percent:+.1f}%\n\n"
    md += f"**Message:** {report.check.message}\n\n"

    if report.zone_history:
        md += f"### Historique Zone {report.zone_history.zone}\n\n"
        md += f"- Séances outdoor: {report.zone_history.total_outdoor_workouts}\n"
        md += f"- Échecs: {report.zone_history.failure_count}\n"
        md += f"- Échecs consécutifs: {report.zone_history.consecutive_failures}\n"
        if report.zone_history.last_failure_date:
            md += f"- Dernier échec: {report.zone_history.last_failure_date}\n"
        md += "\n"

    md += "### Recommandation\n\n"
    md += f"{rec_icon} **{report.overall_recommendation.value.replace('_', ' ').upper()}**\n\n"

    if report.alert_message:
        md += f"{report.alert_message}\n\n"
    elif report.zone_history:
        md += f"{report.zone_history.recommendation_reason}\n\n"

    if report.recovery_period_months:
        md += f"**Période récupération recommandée:** {report.recovery_period_months} mois\n\n"

    return md
