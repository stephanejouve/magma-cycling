#!/usr/bin/env python3
"""
PID + Peaks Coaching Integration pour Training Intelligence.

Sprint R10 - Day 3
Gère l'arbitrage entre corrections PID et contraintes Peaks Coaching selon
l'architecture hiérarchique validée.

Architecture:
    Niveau 1 (Stratégique): Peaks Coaching - Override si CTL critique
    Niveau 2 (Tactique): PID Discret - Optimisation fine si CTL ≥50
    Niveau 3 (Opérationnel): Daily compensation + Training Intelligence

Author: Claude Code + Stéphane Jouve
Created: 2026-02-15
Version: 1.0.0
Sprint: R10 - PID Calibration
"""

from dataclasses import dataclass
from enum import Enum

from magma_cycling.intelligence.discrete_pid_controller import DiscretePIDController
from magma_cycling.planning.peaks_phases import (
    PhaseRecommendation,
    determine_training_phase,
)


class ControlMode(Enum):
    """Control mode for training load adjustment."""

    PEAKS_OVERRIDE = "peaks_override"  # CTL critical, Peaks takes control
    PID_CONSTRAINED = "pid_constrained"  # PID active with Peaks constraints
    PID_AUTONOMOUS = "pid_autonomous"  # PID fully autonomous (future)


@dataclass
class IntegratedRecommendation:
    """
    Integrated recommendation combining PID and Peaks inputs.

    Attributes:
        mode: Active control mode (PEAKS_OVERRIDE or PID_CONSTRAINED)
        tss_per_week: Recommended TSS per week
        ctl_projection_6weeks: Estimated CTL after 6 weeks
        phase: Peaks Coaching training phase
        rationale: Explanation of recommendation
        pid_suggestion: PID absolute suggestion (peaks_base + pid_delta)
        peaks_suggestion: Peaks recommendation (for reference)
        override_active: Whether Peaks override is active
        warnings: List of warnings
        confidence: Recommendation confidence level (low/medium/high)
        pid_delta: Raw PID delta before adding to Peaks base
    """

    mode: ControlMode
    tss_per_week: int
    ctl_projection_6weeks: float
    phase: str
    rationale: str
    pid_suggestion: int | None
    peaks_suggestion: int | None
    override_active: bool
    warnings: list[str]
    confidence: str = "medium"
    pid_delta: int | None = None


def compute_integrated_correction(
    ctl_current: float,
    ftp_current: int,
    ftp_target: int,
    athlete_age: int = 54,
    pid_controller: DiscretePIDController | None = None,
    adherence_rate: float = 0.85,
    avg_cardiovascular_coupling: float = 0.065,
    tss_completion_rate: float = 0.90,
) -> IntegratedRecommendation:
    """
    Compute integrated training load correction using PID + Peaks hierarchy.

    Override Rules (Architecture Sprint R10):
        - CTL < 50: PEAKS_OVERRIDE (reconstruction urgente)
        - CTL 50-85% optimal: PID_CONSTRAINED (PID + contraintes Peaks)
        - CTL ≥ optimal: PID_AUTONOMOUS (future, PID seul)

    Args:
        ctl_current: Current CTL value
        ftp_current: Current FTP (W)
        ftp_target: Target FTP (W)
        athlete_age: Athlete age (default 54, Masters 50+)
        pid_controller: Optional PID controller (if None, uses theoretical gains)
        adherence_rate: Training adherence (0.0-1.0)
        avg_cardiovascular_coupling: Average decoupling (%)
        tss_completion_rate: TSS completion rate (0.0-1.0)

    Returns:
        IntegratedRecommendation with final TSS/week recommendation

    Examples:
        >>> # CTL critical scenario (42.4 < 50)
        >>> rec = compute_integrated_correction(
        ...     ctl_current=42.4,
        ...     ftp_current=223,
        ...     ftp_target=230
        ... )
        >>> rec.mode == ControlMode.PEAKS_OVERRIDE
        True
        >>> rec.tss_per_week >= 350  # Peaks reconstruction
        True
        >>> rec.override_active
        True
    """
    warnings = []

    # Determine Peaks Coaching training phase
    phase_rec: PhaseRecommendation = determine_training_phase(
        ctl_current=ctl_current,
        ftp_current=ftp_current,
        ftp_target=ftp_target,
        athlete_age=athlete_age,
    )

    peaks_tss_suggestion = phase_rec.weekly_tss_load
    peaks_phase = phase_rec.phase.value

    # Calculate PID delta if controller provided
    # PID output is a DELTA (+/-N TSS/week), NOT an absolute target.
    # Absolute = peaks_base + pid_delta.
    pid_delta = None
    pid_tss_absolute = None
    pid_confidence = "low"

    if pid_controller:
        try:
            pid_correction = pid_controller.compute_cycle_correction_enhanced(
                measured_ftp=ftp_current,
                cycle_duration_weeks=6,
                adherence_rate=adherence_rate,
                avg_cardiovascular_coupling=avg_cardiovascular_coupling,
                tss_completion_rate=tss_completion_rate,
            )
            pid_delta = pid_correction["tss_per_week_adjusted"]
            pid_tss_absolute = peaks_tss_suggestion + pid_delta

            # Guard rails: clamp to [150, 450] (Masters 50+)
            if pid_tss_absolute < 150:
                warnings.append(f"PID output aberrant ({pid_tss_absolute} TSS) — fallback Peaks")
                pid_tss_absolute = peaks_tss_suggestion
                pid_confidence = "low"
            elif pid_tss_absolute > 450:
                warnings.append(f"PID output trop élevé ({pid_tss_absolute} TSS) — plafonné 400")
                pid_tss_absolute = 400
                pid_confidence = "medium"
            else:
                # Determine confidence based on PID validation
                validation = pid_correction.get("validation", {})
                if validation.get("validated", False):
                    pid_confidence = "high"
                elif validation.get("confidence", 0) >= 0.7:
                    pid_confidence = "medium"
                else:
                    pid_confidence = "low"

            # Add PID validation warnings
            validation = pid_correction.get("validation", {})
            if not validation.get("validated", True):
                warnings.extend(validation.get("red_flags", []))

        except Exception as e:
            warnings.append(f"PID calculation failed: {e}")
            pid_tss_absolute = None
            pid_delta = None

    # Reactivation rule: PID takes over when within ±15% of Peaks target
    peaks_low = int(peaks_tss_suggestion * 0.85)
    peaks_high = int(peaks_tss_suggestion * 1.15)
    pid_in_range = pid_tss_absolute is not None and peaks_low <= pid_tss_absolute <= peaks_high

    # Decision logic: CTL-based override rules
    if ctl_current < 50:
        if pid_in_range and pid_confidence != "low":
            # PID recalibré dans la plage → PID actif avec Peaks constraint
            mode = ControlMode.PID_CONSTRAINED
            tss_final = pid_tss_absolute
            override_active = False

            rationale = (
                f"🎛️ PID RECALIBRÉ (CTL {ctl_current:.1f}, Peaks Override levé)\n"
                f"→ Peaks base: {peaks_tss_suggestion} TSS/semaine\n"
                f"→ PID delta: {pid_delta:+d} TSS/semaine\n"
                f"→ PID absolu: {pid_tss_absolute} TSS/semaine (dans plage [{peaks_low}-{peaks_high}])\n"
                f"→ Phase: {peaks_phase.upper()}\n"
            )
        else:
            # PID hors plage ou non disponible → Peaks Override
            mode = ControlMode.PEAKS_OVERRIDE
            tss_final = peaks_tss_suggestion
            override_active = True

            rationale = (
                f"🚨 CTL CRITIQUE ({ctl_current:.1f} < 50)\n"
                f"→ PEAKS COACHING OVERRIDE actif\n"
                f"→ Phase: {peaks_phase.upper()}\n"
                f"→ Peaks recommande: {peaks_tss_suggestion} TSS/semaine\n"
            )

            if pid_tss_absolute is not None and pid_confidence != "low":
                rationale += (
                    f"→ PID: {pid_tss_absolute} TSS/semaine "
                    f"(hors plage [{peaks_low}-{peaks_high}], ignoré)\n"
                )
            elif pid_delta is not None:
                rationale += (
                    f"→ PID delta: {pid_delta:+d} TSS → "
                    f"confiance {pid_confidence} (insuffisante)\n"
                )

    elif ctl_current < (phase_rec.ctl_target * 0.85):
        # CTL SOUS-OPTIMAL (50-85% target): PID active with Peaks constraints
        mode = ControlMode.PID_CONSTRAINED
        override_active = True

        if pid_tss_absolute and pid_tss_absolute >= peaks_tss_suggestion:
            tss_final = pid_tss_absolute
            rationale = (
                f"✅ PID ACTIF (CTL {ctl_current:.1f} ≥ 50)\n"
                f"→ Peaks base: {peaks_tss_suggestion} TSS/semaine\n"
                f"→ PID delta: {pid_delta:+d} → absolu: {pid_tss_absolute} TSS/semaine\n"
                f"→ PID dépasse Peaks → Appliqué"
            )
        else:
            tss_final = peaks_tss_suggestion
            rationale = (
                f"⚖️  PID + PEAKS CONSTRAINT\n"
                f"→ PID absolu: {pid_tss_absolute or 'N/A'} TSS/semaine\n"
                f"→ Peaks minimum: {peaks_tss_suggestion} TSS/semaine\n"
                f"→ Peaks minimum appliqué"
            )

    else:
        # CTL OPTIMAL (≥85% target): PID autonomous
        mode = ControlMode.PID_CONSTRAINED  # Still constrained for safety
        override_active = False
        tss_final = pid_tss_absolute or peaks_tss_suggestion

        rationale = (
            f"✅ CTL OPTIMAL ({ctl_current:.1f} ≥ 85% target)\n"
            f"→ PID autonome recommandé\n"
            f"→ Suggestion: {tss_final} TSS/semaine"
        )

    # Determine final confidence
    confidence = pid_confidence if pid_tss_absolute else "low"
    if override_active and mode == ControlMode.PEAKS_OVERRIDE:
        confidence = "medium"  # Peaks Override is a known-good fallback

    # Project CTL gain over 6 weeks
    tss_increase = tss_final - (ctl_current * 7)
    ctl_gain_per_week = tss_increase / 7 * 0.14
    ctl_projection = ctl_current + (ctl_gain_per_week * 6)

    # Add warnings for critical states
    if adherence_rate < 0.80:
        warnings.append(
            f"⚠️  Adherence faible ({adherence_rate:.0%}) - "
            f"Risque non-réalisation {tss_final} TSS/semaine"
        )

    if avg_cardiovascular_coupling > 0.08:
        warnings.append(
            f"⚠️  Découplage élevé ({avg_cardiovascular_coupling:.1%}) - "
            "Risque surcharge si volume augmenté"
        )

    return IntegratedRecommendation(
        mode=mode,
        tss_per_week=tss_final,
        ctl_projection_6weeks=ctl_projection,
        phase=peaks_phase,
        rationale=rationale,
        pid_suggestion=pid_tss_absolute,
        peaks_suggestion=peaks_tss_suggestion,
        override_active=override_active,
        warnings=warnings,
        confidence=confidence,
        pid_delta=pid_delta,
    )


def format_integrated_recommendation(rec: IntegratedRecommendation) -> str:
    """
    Format integrated recommendation for display/email.

    Args:
        rec: IntegratedRecommendation to format

    Returns:
        Formatted markdown string

    Examples:
        >>> rec = IntegratedRecommendation(
        ...     mode=ControlMode.PEAKS_OVERRIDE,
        ...     tss_per_week=350,
        ...     ctl_projection_6weeks=54.5,
        ...     phase="reconstruction_base",
        ...     rationale="CTL critique",
        ...     pid_suggestion=2,
        ...     peaks_suggestion=350,
        ...     override_active=True,
        ...     warnings=[]
        ... )
        >>> formatted = format_integrated_recommendation(rec)
        >>> "PEAKS OVERRIDE" in formatted
        True
    """
    output = []

    # Header with mode and confidence
    confidence_label = {"low": "faible", "medium": "moyenne", "high": "haute"}.get(
        rec.confidence, rec.confidence
    )

    if rec.override_active:
        if rec.mode == ControlMode.PEAKS_OVERRIDE:
            output.append("## 🚨 PEAKS COACHING OVERRIDE ACTIF")
        else:
            output.append("## ⚖️  PID + PEAKS CONSTRAINT")
    else:
        output.append("## 🎛️ PID ACTIF")

    output.append("")

    # Recommendation details
    output.append(f"**TSS recommandé**: {rec.tss_per_week} TSS/semaine")
    output.append(f"**Confiance**: {confidence_label}")
    if rec.pid_delta is not None:
        source = "PID actif" if not rec.override_active else "Peaks Override"
        output.append(f"**Source**: {source}")
    output.append(f"**Phase**: {rec.phase.replace('_', ' ').title()}")
    output.append(f"**CTL projeté (6 sem)**: {rec.ctl_projection_6weeks:.1f}")
    output.append("")

    # Rationale
    output.append("**Rationale**:")
    output.append("```")
    output.append(rec.rationale)
    output.append("```")
    output.append("")

    # Comparison table if both suggestions available
    if rec.pid_suggestion and rec.peaks_suggestion:
        output.append("**Comparaison PID vs Peaks**:")
        output.append("")
        output.append("| Source | TSS/semaine | Delta | Appliqué |")
        output.append("|--------|-------------|-------|----------|")
        delta_str = f"{rec.pid_delta:+d}" if rec.pid_delta is not None else "—"
        output.append(
            f"| PID    | {rec.pid_suggestion:>11} | {delta_str:>5} | "
            f"{'✅' if rec.tss_per_week == rec.pid_suggestion else '❌'} |"
        )
        output.append(
            f"| Peaks  | {rec.peaks_suggestion:>11} |   —   | "
            f"{'✅' if rec.tss_per_week == rec.peaks_suggestion else '❌'} |"
        )
        output.append("")

    # Warnings
    if rec.warnings:
        output.append("**⚠️  Warnings**:")
        for warning in rec.warnings:
            output.append(f"- {warning}")
        output.append("")

    return "\n".join(output)


def get_weekly_tss_target(
    ctl_current: float,
    ftp_current: int,
    week_type: str = "charge",
    ftp_target: int | None = None,
) -> int:
    """
    Get weekly TSS target based on current CTL and phase.

    Quick helper for weekly planning without full integration.

    Args:
        ctl_current: Current CTL
        ftp_current: Current FTP (W)
        week_type: "charge" or "recovery"
        ftp_target: Target FTP (W). If None, loads from AthleteProfile.from_env()

    Returns:
        TSS target for the week

    Examples:
        >>> get_weekly_tss_target(42.4, 223, "charge", ftp_target=230)
        350
        >>> get_weekly_tss_target(42.4, 223, "recovery", ftp_target=230)
        250
    """
    # Load ftp_target from config if not provided
    if ftp_target is None:
        from magma_cycling.config.athlete_profile import AthleteProfile

        profile = AthleteProfile.from_env()
        ftp_target = profile.ftp_target

    # Determine phase
    phase_rec = determine_training_phase(
        ctl_current=ctl_current, ftp_current=ftp_current, ftp_target=ftp_target
    )

    if week_type == "recovery":
        return phase_rec.weekly_tss_recovery
    else:
        return phase_rec.weekly_tss_load
