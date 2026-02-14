#!/usr/bin/env python3
"""
Peaks Coaching training phase algorithms.

Implements Hunter Allen's methodology for determining training phase
based on current CTL vs FTP target for Masters 50+ athletes.

Based on: "Training and Racing with a Power Meter" (Hunter Allen, Andrew Coggan)

Author: Stéphane Jouve
Created: 2026-02-14
"""

from dataclasses import dataclass
from enum import Enum


class TrainingPhase(str, Enum):
    """Training phase according to Peaks Coaching methodology."""

    RECONSTRUCTION_BASE = "reconstruction_base"
    CONSOLIDATION = "consolidation"
    DEVELOPMENT_FTP = "development_ftp"


@dataclass
class PhaseRecommendation:
    """Training phase recommendation with distribution and parameters."""

    phase: TrainingPhase
    ctl_current: float
    ctl_target: float
    ctl_deficit: float
    weeks_to_rebuild: int
    weekly_tss_load: int
    weekly_tss_recovery: int
    recovery_week_frequency: int
    intensity_distribution: dict[str, float]
    rationale: str


def calculate_ctl_target(ftp_current: int, ftp_target: int, ctl_current: float) -> float:
    """
    Calculate CTL target based on FTP progression goal.

    According to Peaks Coaching empirical data:
    - FTP 220W → CTL minimum 55-65, optimal 70
    - FTP 240W → CTL minimum 65-75, optimal 75
    - FTP 260W → CTL minimum 70-80, optimal 80

    Formula: CTL_target = CTL_current * (FTP_target / FTP_current) * 1.15

    Args:
        ftp_current: Current FTP in watts
        ftp_target: Target FTP in watts
        ctl_current: Current CTL value

    Returns:
        Target CTL value (optimal for target FTP)

    Examples:
        >>> calculate_ctl_target(220, 260, 42)
        70.0  # Optimal CTL for 260W FTP
    """
    # Base CTL calculation from FTP ratio
    ctl_from_ratio = ctl_current * (ftp_target / ftp_current) * 1.15

    # Peaks Coaching optimal thresholds
    ctl_optimal_for_ftp = (ftp_target / 220) * 70

    # Return the higher of the two (more conservative)
    return max(ctl_from_ratio, ctl_optimal_for_ftp)


def determine_training_phase(
    ctl_current: float,
    ftp_current: int,
    ftp_target: int,
    athlete_age: int = 54,
) -> PhaseRecommendation:
    """
    Determine current training phase according to Peaks Coaching methodology.

    Analyzes CTL vs FTP target to determine if athlete should focus on:
    - RECONSTRUCTION_BASE: Build aerobic base (CTL < 85% of target)
    - CONSOLIDATION: Solidify fitness (CTL 85-100% of target)
    - DEVELOPMENT_FTP: Develop FTP capacity (CTL >= target)

    Implements algorithm from Section 11.1 of Peaks Coaching methodology.

    Args:
        ctl_current: Current CTL (Chronic Training Load)
        ftp_current: Current FTP in watts
        ftp_target: Target FTP in watts
        athlete_age: Athlete age (default: 54, Masters 50+)

    Returns:
        PhaseRecommendation with phase, distribution, and parameters

    Examples:
        >>> rec = determine_training_phase(42, 220, 260)
        >>> rec.phase
        <TrainingPhase.RECONSTRUCTION_BASE: 'reconstruction_base'>
        >>> rec.intensity_distribution["Tempo"]
        0.35
    """
    # Calculate CTL target for FTP goal
    ctl_target = calculate_ctl_target(ftp_current, ftp_target, ctl_current)
    ctl_deficit = ctl_target - ctl_current

    # Determine phase based on CTL ratio
    if ctl_current < (0.85 * ctl_target):
        phase = TrainingPhase.RECONSTRUCTION_BASE
        distribution = {
            "Recovery": 0.10,
            "Endurance": 0.25,
            "Tempo": 0.35,  # FOCUS
            "Sweet-Spot": 0.20,  # FOCUS
            "FTP": 0.05,
            "VO2": 0.03,
            "AC_Neuro": 0.02,
        }
        weekly_tss = 350  # Load week
        recovery_week_freq = 3  # Every 3 weeks
        rationale = (
            f"CTL critique ({ctl_current:.1f} < 85% de {ctl_target:.0f}). "
            "Phase reconstruction base prioritaire. Focus Tempo (35%) + Sweet-Spot (20%) "
            "pour développer fitness aérobie. Éviter intensité élevée prématurée."
        )

    elif ctl_current < ctl_target:
        phase = TrainingPhase.CONSOLIDATION
        distribution = {
            "Recovery": 0.10,
            "Endurance": 0.20,
            "Tempo": 0.25,
            "Sweet-Spot": 0.25,  # FOCUS
            "FTP": 0.10,
            "VO2": 0.08,
            "AC_Neuro": 0.02,
        }
        weekly_tss = 380
        recovery_week_freq = 3
        rationale = (
            f"CTL en progression ({ctl_current:.1f} → {ctl_target:.0f}). "
            "Phase consolidation. Sweet-Spot reste prioritaire (25%), "
            "introduction progressive FTP (10%) et VO2 (8%)."
        )

    else:  # CTL >= target
        phase = TrainingPhase.DEVELOPMENT_FTP
        distribution = {
            "Recovery": 0.10,
            "Endurance": 0.20,
            "Tempo": 0.20,
            "Sweet-Spot": 0.20,
            "FTP": 0.15,  # FOCUS
            "VO2": 0.10,
            "AC_Neuro": 0.05,
        }
        weekly_tss = 380
        recovery_week_freq = 4  # Less frequent if CTL solid
        rationale = (
            f"CTL optimal atteint ({ctl_current:.1f} >= {ctl_target:.0f}). "
            "Phase développement FTP. Distribution équilibrée avec focus FTP (15%) "
            "et VO2 (10%). Base aérobie maintenue."
        )

    # Adjust recovery frequency for Masters 50+
    if athlete_age >= 50:
        recovery_week_freq = max(recovery_week_freq - 1, 2)
        # Never >3 weeks load consecutive for Masters 50+
        recovery_week_freq = min(recovery_week_freq, 3)

    # Calculate weeks to rebuild
    weeks_to_rebuild = int(ctl_deficit / 2.5) if ctl_deficit > 0 else 0

    return PhaseRecommendation(
        phase=phase,
        ctl_current=ctl_current,
        ctl_target=ctl_target,
        ctl_deficit=max(ctl_deficit, 0),
        weeks_to_rebuild=weeks_to_rebuild,
        weekly_tss_load=weekly_tss,
        weekly_tss_recovery=250 if weekly_tss >= 350 else 220,
        recovery_week_frequency=recovery_week_freq,
        intensity_distribution=distribution,
        rationale=rationale,
    )


def format_phase_recommendation(recommendation: PhaseRecommendation) -> str:
    """
    Format phase recommendation as markdown for reports.

    Args:
        recommendation: PhaseRecommendation from determine_training_phase()

    Returns:
        Markdown formatted recommendation

    Examples:
        >>> rec = determine_training_phase(42, 220, 260)
        >>> print(format_phase_recommendation(rec))
        ## Phase Entraînement Recommandée: RECONSTRUCTION BASE
        ...
    """
    phase_labels = {
        TrainingPhase.RECONSTRUCTION_BASE: "RECONSTRUCTION BASE",
        TrainingPhase.CONSOLIDATION: "CONSOLIDATION",
        TrainingPhase.DEVELOPMENT_FTP: "DÉVELOPPEMENT FTP",
    }

    md = f"## Phase Entraînement Recommandée: {phase_labels[recommendation.phase]}\n\n"
    md += "### Métriques\n"
    md += f"- **CTL actuel**: {recommendation.ctl_current:.1f}\n"
    md += f"- **CTL cible**: {recommendation.ctl_target:.0f}\n"

    if recommendation.ctl_deficit > 0:
        md += f"- **Déficit**: {recommendation.ctl_deficit:.1f} points\n"
        md += f"- **Durée reconstruction**: {recommendation.weeks_to_rebuild} semaines minimum\n"

    md += "\n### Distribution Intensité Recommandée\n\n"
    for zone, percentage in recommendation.intensity_distribution.items():
        md += f"- **{zone}**: {percentage * 100:.0f}%"
        if percentage >= 0.20:  # Highlight focus zones
            md += " ← FOCUS"
        md += "\n"

    md += "\n### Paramètres Volume\n"
    md += f"- **Semaines charge**: {recommendation.weekly_tss_load} TSS\n"
    md += f"- **Semaines récup**: {recommendation.weekly_tss_recovery} TSS\n"
    md += f"- **Fréquence récup**: Tous les {recommendation.recovery_week_frequency} semaines\n"

    md += "\n### Rationale\n"
    md += f"{recommendation.rationale}\n"

    return md
