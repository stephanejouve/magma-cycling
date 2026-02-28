#!/usr/bin/env python3
"""
Alert message templates (Peaks Coaching methodology).

Standardized message templates for common training alerts:
- CTL too low for FTP target
- Intensity distribution mismatch
- Test execution quality issues

Based on Hunter Allen / Peaks Coaching Group communication standards.

Author: Stéphane Jouve
Created: 2026-02-14
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class CTLAlertData:
    """Data for CTL critical alert message."""

    ctl_current: float
    ctl_required: float
    ctl_deficit: float
    ctl_drop: float  # Points dropped
    drop_weeks: int  # Over how many weeks
    ftp_target: int
    athlete_age: int
    weeks_phase1: int
    ctl_intermediate: float  # First milestone
    tss_weekly: int
    recovery_frequency: int
    total_weeks: int


@dataclass
class DistributionAlertData:
    """Data for intensity distribution alert message."""

    current_distribution: dict[str, float]  # Zone -> percentage
    issue_description: str
    quote_hunter_allen: str


@dataclass
class TestQualityAlertData:
    """Data for test execution quality alert."""

    test_type: str  # "1min", "5min", "20min", etc.
    power_result: int  # Watts
    issue_description: str
    retest_date_recommendation: date


def format_ctl_alert(data: CTLAlertData) -> str:
    """
    Format CTL critical alert message.

    Based on Section 12.1 of Peaks Coaching methodology.
    Used when CTL is too low for FTP target.

    Args:
        data: CTLAlertData with all required fields

    Returns:
        Formatted alert message

    Examples:
        >>> data = CTLAlertData(
        ...     ctl_current=41.8,
        ...     ctl_required=70,
        ...     ctl_deficit=28.2,
        ...     ctl_drop=15,
        ...     drop_weeks=4,
        ...     ftp_target=260,
        ...     athlete_age=54,
        ...     weeks_phase1=11,
        ...     ctl_intermediate=55,
        ...     tss_weekly=350,
        ...     recovery_frequency=2,
        ...     total_weeks=16
        ... )
        >>> print(format_ctl_alert(data))
        ⚠️ ALERTE CTL CRITIQUE
        ...
    """
    message = "⚠️ ALERTE CTL CRITIQUE\n\n"
    message += f"CTL actuel : {data.ctl_current:.1f}\n"
    message += f"CTL requis FTP {data.ftp_target}W : {data.ctl_required:.0f}\n"
    message += f"Déficit : {data.ctl_deficit:.1f} points\n\n"

    message += "ANALYSE :\n"
    message += (
        f"Baisse CTL de {data.ctl_drop:.1f} points détectée sur {data.drop_weeks} semaines.\n"
    )
    message += f'À {data.athlete_age} ans, récupération CTL lente (Hunter Allen : "long fight for months").\n\n'

    message += "PLAN RECONSTRUCTION :\n"
    message += (
        f"Phase 1 ({data.weeks_phase1} semaines) : "
        f"{data.ctl_current:.1f} → {data.ctl_intermediate:.0f}\n"
    )
    message += f"  - Volume : {data.tss_weekly} TSS/semaine\n"
    message += "  - Focus : Tempo (35%) + Sweet-Spot (20%)\n"
    message += f"  - Récup : Tous les {data.recovery_frequency} semaines\n\n"

    message += f"Délai réaliste objectif FTP {data.ftp_target}W : {data.total_weeks} semaines\n"

    return message


def format_distribution_alert(data: DistributionAlertData) -> str:
    """
    Format intensity distribution alert message.

    Based on Section 12.2 of Peaks Coaching methodology.
    Used when current distribution doesn't match Traditional Method.

    Args:
        data: DistributionAlertData with current distribution and issue

    Returns:
        Formatted alert message

    Examples:
        >>> data = DistributionAlertData(
        ...     current_distribution={"VO2": 0.25, "FTP": 0.30, "Tempo": 0.15},
        ...     issue_description="Trop d'intensité haute (VO2+FTP 55%), pas assez Tempo",
        ...     quote_hunter_allen="Traditional method with emphasis on Tempo and Sweet-Spot..."
        ... )
        >>> print(format_distribution_alert(data))
        📊 RÉVISION DISTRIBUTION INTENSITÉ
        ...
    """
    message = "📊 RÉVISION DISTRIBUTION INTENSITÉ\n\n"

    message += "Distribution actuelle détectée :\n"
    for zone, percentage in sorted(data.current_distribution.items(), key=lambda x: -x[1]):
        message += f"- {zone}: {percentage * 100:.0f}%\n"
    message += "\n"

    message += "PROBLÈME :\n"
    message += f"{data.issue_description}\n\n"

    message += "Distribution recommandée (Hunter Allen - Méthode Traditionnelle) :\n"
    message += "- Tempo (76-91% FTP) : 35%\n"
    message += "- Sweet-Spot (88-93% FTP) : Intégré dans 35% ci-dessus\n"
    message += "- Endurance (56-75% FTP) : 25%\n"
    message += "- FTP (94-105%) : 15%\n"
    message += "- VO2 (106-120%) : 10%\n"
    message += "- AC/Neuro (>120%) : 5%\n\n"

    message += "JUSTIFICATION :\n"
    message += f'"{data.quote_hunter_allen}"\n'

    return message


def format_test_quality_alert(data: TestQualityAlertData) -> str:
    """
    Format test execution quality alert message.

    Based on Section 12.3 of Peaks Coaching methodology.
    Used when test execution doesn't follow correct protocol.

    Args:
        data: TestQualityAlertData with test result and issues

    Returns:
        Formatted alert message

    Examples:
        >>> data = TestQualityAlertData(
        ...     test_type="1min",
        ...     power_result=425,
        ...     issue_description="plateau dernières 30s (pas assez fort au début)",
        ...     retest_date_recommendation=date(2026, 2, 21)
        ... )
        >>> print(format_test_quality_alert(data))
        ❌ ANALYSE TEST 1 MINUTE
        ...
    """
    test_titles = {
        "1min": "TEST 1 MINUTE",
        "5min": "TEST 5 MINUTES (VO2max)",
        "20min": "TEST FTP 20 MINUTES",
    }

    title = test_titles.get(data.test_type, f"TEST {data.test_type.upper()}")

    message = f"❌ ANALYSE {title}\n\n"
    message += f"Résultat : {data.power_result}W moyens\n\n"

    message += "PROBLÈME DÉTECTÉ :\n"
    message += f"Courbe puissance montre {data.issue_description}\n\n"

    if data.test_type == "1min":
        message += "PROTOCOLE CORRECT (Hunter Allen) :\n"
        message += "1. Échauffement 20min maximum (pas plus !)\n"
        message += "2. Explosion maximale 0-30s (sprint out-saddle)\n"
        message += "3. Tenir coûte que coûte 30-60s\n"
        message += "4. Attendre dégradation puissance continue\n\n"

        message += "VALIDATION QUALITÉ :\n"
        message += "✓ Pic puissance immédiat\n"
        message += "✓ Dégradation continue jusqu'à fin\n"
        message += "✗ Plateau dernières 30s = pas assez fort début\n\n"

    elif data.test_type == "5min":
        message += "PROTOCOLE CORRECT (Hunter Allen) :\n"
        message += "1. Échauffement progressif + openers\n"
        message += "2. Départ contrôlé à 110% FTP estimé\n"
        message += "3. Maintenir effort maximal soutenable\n"
        message += "4. Dérive puissance <5% acceptable\n\n"

        message += "VALIDATION QUALITÉ :\n"
        message += "✓ Puissance stable premières 3 minutes\n"
        message += "✓ Dérive progressive fin acceptable\n"
        message += "✗ Chute brutale >10% = départ trop rapide\n\n"

    elif data.test_type == "20min":
        message += "PROTOCOLE CORRECT (Hunter Allen) :\n"
        message += "1. Échauffement 15-20min + openers\n"
        message += "2. Départ contrôlé (pas trop rapide !)\n"
        message += "3. Effort maximal soutenable 20min\n"
        message += "4. FTP = 95% de puissance moyenne 20min\n\n"

        message += "VALIDATION QUALITÉ :\n"
        message += "✓ Dérive Pa:Hr <5%\n"
        message += "✓ Variabilité <5% (IV proche 1.00)\n"
        message += "✗ Dérive >5% ou IV >1.05 = pacing incorrect\n\n"

    message += f"Retest recommandé : {data.retest_date_recommendation.strftime('%d/%m/%Y')}\n"

    return message


def generate_ctl_drop_alert(
    ctl_current: float,
    ctl_previous: float,
    weeks_between: int,
    ftp_current: int,
    ftp_target: int,
    athlete_age: int,
    ctl_minimum_for_ftp: float,
) -> str | None:
    """
    Generate CTL drop alert if drop exceeds thresholds.

    According to Peaks Coaching:
    - Masters 50+: CTL drop >10 points in 4 weeks is critical
    - CTL < minimum for FTP is critical

    Args:
        ctl_current: Current CTL value
        ctl_previous: CTL value N weeks ago
        weeks_between: Number of weeks between measurements
        ftp_current: Current FTP (watts)
        ftp_target: Target FTP (watts)
        athlete_age: Athlete age
        ctl_minimum_for_ftp: Minimum CTL required for FTP target

    Returns:
        Formatted alert message if alert triggered, None otherwise

    Examples:
        >>> alert = generate_ctl_drop_alert(
        ...     ctl_current=41.8,
        ...     ctl_previous=56.8,
        ...     weeks_between=4,
        ...     ftp_current=220,
        ...     ftp_target=260,
        ...     athlete_age=54,
        ...     ctl_minimum_for_ftp=70
        ... )
        >>> alert is not None
        True
    """
    ctl_drop = ctl_previous - ctl_current

    # Check if alert should be triggered
    alert_triggered = False

    # Alert 1: Significant CTL drop (>10 points for Masters 50+)
    if athlete_age >= 50 and ctl_drop > 10:
        alert_triggered = True

    # Alert 2: CTL below minimum for FTP target
    if ctl_current < ctl_minimum_for_ftp:
        alert_triggered = True

    if not alert_triggered:
        return None

    # Calculate reconstruction plan
    ctl_deficit = max(ctl_minimum_for_ftp - ctl_current, 0)
    weeks_phase1 = int(ctl_deficit / 2.5)  # ~2.5 CTL points per week
    ctl_intermediate = min(ctl_current + (weeks_phase1 * 2.5), ctl_minimum_for_ftp)
    total_weeks = int((ctl_minimum_for_ftp - ctl_current) / 2.5)

    # Masters 50+ recovery frequency
    recovery_frequency = 2 if athlete_age >= 50 else 3

    data = CTLAlertData(
        ctl_current=ctl_current,
        ctl_required=ctl_minimum_for_ftp,
        ctl_deficit=ctl_deficit,
        ctl_drop=ctl_drop,
        drop_weeks=weeks_between,
        ftp_target=ftp_target,
        athlete_age=athlete_age,
        weeks_phase1=weeks_phase1,
        ctl_intermediate=ctl_intermediate,
        tss_weekly=350,  # Load week for RECONSTRUCTION phase
        recovery_frequency=recovery_frequency,
        total_weeks=total_weeks,
    )

    return format_ctl_alert(data)


def generate_distribution_alert(
    current_distribution: dict[str, float],
    phase: str,  # "RECONSTRUCTION_BASE", "CONSOLIDATION", "DEVELOPMENT_FTP"
) -> str | None:
    """
    Generate distribution alert if current doesn't match phase target.

    Args:
        current_distribution: Current distribution (zone -> percentage)
        phase: Current training phase

    Returns:
        Formatted alert message if mismatch detected, None otherwise

    Examples:
        >>> dist = {"VO2": 0.20, "FTP": 0.25, "Tempo": 0.10, "Endurance": 0.25}
        >>> alert = generate_distribution_alert(dist, "RECONSTRUCTION_BASE")
        >>> alert is not None
        True  # Too much VO2/FTP, not enough Tempo
    """
    # Target distributions by phase
    targets = {
        "RECONSTRUCTION_BASE": {"Tempo": 0.35, "Sweet-Spot": 0.20, "Endurance": 0.25},
        "CONSOLIDATION": {"Sweet-Spot": 0.25, "Tempo": 0.25, "FTP": 0.10},
        "DEVELOPMENT_FTP": {"FTP": 0.15, "VO2": 0.10, "Sweet-Spot": 0.20},
    }

    if phase not in targets:
        return None

    target = targets[phase]

    # Check for significant deviations (>10% absolute difference)
    issues = []
    for zone, target_pct in target.items():
        actual_pct = current_distribution.get(zone, 0.0)
        diff = actual_pct - target_pct

        if abs(diff) > 0.10:  # >10% absolute difference
            if diff > 0:
                issues.append(
                    f"Trop de {zone} ({actual_pct * 100:.0f}% vs {target_pct * 100:.0f}% cible)"
                )
            else:
                issues.append(
                    f"Pas assez de {zone} ({actual_pct * 100:.0f}% vs {target_pct * 100:.0f}% cible)"
                )

    if not issues:
        return None

    # Generate issue description
    issue_description = ". ".join(issues) + "."

    # Select appropriate Hunter Allen quote
    quotes = {
        "RECONSTRUCTION_BASE": (
            "For Masters athletes, building aerobic base with Tempo and Sweet-Spot "
            "is the most time-efficient approach. These zones provide the biggest "
            "bang for your buck when time is limited."
        ),
        "CONSOLIDATION": (
            "Sweet-Spot training at 88-93% FTP is the optimal intensity for building "
            "fitness without excessive fatigue. It's hard enough to create adaptation "
            "but sustainable enough to accumulate significant volume."
        ),
        "DEVELOPMENT_FTP": (
            "Once aerobic base is solid, strategic FTP and VO2max work can push "
            "your threshold higher. But this only works if CTL foundation is in place."
        ),
    }

    data = DistributionAlertData(
        current_distribution=current_distribution,
        issue_description=issue_description,
        quote_hunter_allen=quotes[phase],
    )

    return format_distribution_alert(data)


def generate_test_quality_alert_1min(
    power_avg: int,
    power_30s_first: int,
    power_30s_second: int,
    retest_weeks: int = 1,
) -> str | None:
    """
    Generate test quality alert for 1-minute test.

    According to Hunter Allen protocol:
    - First 30s should be MAXIMUM (sprint all-out)
    - Second 30s will naturally drop (fatigue)
    - Power plateau in last 30s = didn't go hard enough at start

    Args:
        power_avg: Average power for full minute
        power_30s_first: Average power first 30 seconds
        power_30s_second: Average power last 30 seconds
        retest_weeks: Weeks before retest recommended

    Returns:
        Formatted alert if test execution problematic, None otherwise

    Examples:
        >>> alert = generate_test_quality_alert_1min(
        ...     power_avg=425,
        ...     power_30s_first=430,
        ...     power_30s_second=420
        ... )
        >>> alert is not None
        True  # Power too stable, should have more drop
    """
    # Calculate drop from first to second half
    power_drop_percent = ((power_30s_first - power_30s_second) / power_30s_first) * 100

    # Expected drop: 15-25% (fatigue accumulation)
    if power_drop_percent < 10:
        issue = (
            f"plateau dernières 30s ({power_30s_second}W vs {power_30s_first}W premières 30s). "
            f"Chute seulement {power_drop_percent:.0f}% (attendu 15-25%). "
            f"Protocole correct = explosion maximale début, puis tenir coûte que coûte."
        )
    elif power_drop_percent > 35:
        issue = (
            f"chute excessive 30s → 30s ({power_30s_first}W → {power_30s_second}W = {power_drop_percent:.0f}%). "
            f"Possible échauffement excessif (>20min) ou fatigue préalable."
        )
    else:
        # Test executed correctly
        return None

    retest_date = date.today() + timedelta(weeks=retest_weeks)

    data = TestQualityAlertData(
        test_type="1min",
        power_result=power_avg,
        issue_description=issue,
        retest_date_recommendation=retest_date,
    )

    return format_test_quality_alert(data)
