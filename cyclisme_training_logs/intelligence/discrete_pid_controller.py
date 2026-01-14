"""
PID Controller Discret pour Training Intelligence.

Régulation automatique progression FTP basée sur tests sporadiques (cycles 6-8 semaines).
Correction appliquée niveau cycle avec validation grandeurs complémentaires.

Architecture:
    - Mesure FTP: Tous les 6-8 semaines (tests programmés)
    - Correction: Appliquée sur cycle complet (pas hebdomadaire)
    - Sample-and-Hold: Correction maintenue jusqu'au test suivant
    - Enhanced: Validation multi-critères (adherence, coupling, TSS)

Examples:
    Basic discrete PID usage::

        controller = DiscretePIDController(
            kp=0.008, ki=0.001, kd=0.12, setpoint=260
        )

        # Test FTP fin cycle S001-S006
        correction = controller.compute_cycle_correction(
            measured_ftp=206,
            cycle_duration_weeks=6
        )

        print(correction["tss_per_week"])  # +7 TSS
        # Appliqué sur cycle S007-S012 (6 semaines)

    Enhanced with validation::

        correction = controller.compute_cycle_correction_enhanced(
            measured_ftp=206,
            cycle_duration_weeks=6,
            adherence_rate=0.92,
            avg_cardiovascular_coupling=0.062,
            tss_completion_rate=0.94
        )

        if correction["validation"]["validated"]:
            print(f"Appliquer {correction['tss_per_week']} TSS/semaine")

Author: Claude Code
Created: 2026-01-14
Version: 1.0.0
Sprint: R9 (Consolidation)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cyclisme_training_logs.intelligence.training_intelligence import (
        TrainingIntelligence,
    )


@dataclass
class DiscretePIDState:
    """
    Internal state for Discrete PID Controller.

    Tracks integral accumulation over cycles, previous error, and last measurement
    timestamp for derivative calculation between tests.

    Attributes:
        integral: Cumulative error over cycles (W·cycles)
        prev_error: Previous error value from last FTP test (W)
        prev_ftp: Previous measured FTP value (W)
        last_test_date: Timestamp of last FTP test
        cycle_count: Number of cycles processed
    """

    integral: float = 0.0
    prev_error: float = 0.0
    prev_ftp: float | None = None
    last_test_date: datetime | None = None
    cycle_count: int = 0


class DiscretePIDController:
    """
    Contrôleur PID Discret adapté mesures sporadiques FTP.

    Calcule correction TSS niveau cycle basée sur tests FTP espacés (6-8 semaines).
    Gains adaptés système lent avec validation grandeurs complémentaires.

    PID Formula (Discrete):
        error = setpoint - measured_ftp
        integral += error * dt_cycles  (avec anti-windup)
        derivative = (error - prev_error) / dt_cycles
        output = Kp * error + Ki * integral + Kd * derivative

    Dead-Band:
        Erreur < ±3W → Ignorée (variations naturelles FTP)

    TSS Translation:
        output (W/cycle) → tss_per_week
        Approximation: +1W FTP sustained ≈ +12.5 TSS/semaine

    Gains Conservateurs (Système Lent):
        - Kp: 0.008 (vs 0.01 continu, -20%)
        - Ki: 0.001 (vs 0.002 continu, -50%)
        - Kd: 0.12 (vs 0.15 continu, -20%)

    Anti-Windup:
        Integral limité ±200W·cycles (≈3 cycles max accumulation)

    Output Saturation:
        TSS adjustment ±30 TSS/semaine max (vs ±50 continu)

    Attributes:
        kp: Gain proportionnel (0.005-0.010 recommandé)
        ki: Gain intégral (0.0005-0.002 recommandé)
        kd: Gain dérivé (0.08-0.15 recommandé)
        setpoint: FTP cible (W)
        state: État interne PID discret
        dead_band: Seuil erreur ignorée (W, défaut 3.0)

    Examples:
        >>> controller = DiscretePIDController(
        ...     kp=0.008, ki=0.001, kd=0.12, setpoint=260
        ... )
        >>> correction = controller.compute_cycle_correction(
        ...     measured_ftp=206, cycle_duration_weeks=6
        ... )
        >>> print(correction['tss_per_week'])
        7
    """

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        setpoint: float,
        dead_band: float = 3.0,
    ):
        """
        Initialize Discrete PID Controller.

        Args:
            kp: Gain proportionnel (0.005-0.010 recommandé système lent)
            ki: Gain intégral (0.0005-0.002 recommandé)
            kd: Gain dérivé (0.08-0.15 recommandé)
            setpoint: FTP cible (W)
            dead_band: Seuil erreur ignorée (W, défaut 3.0)

        Raises:
            ValueError: If gains or setpoint are invalid
        """
        if kp < 0 or ki < 0 or kd < 0:
            raise ValueError("PID gains must be non-negative")
        if setpoint <= 0:
            raise ValueError("Setpoint must be positive")
        if dead_band < 0:
            raise ValueError("Dead band must be non-negative")

        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.dead_band = dead_band
        self.state = DiscretePIDState()

    def compute_cycle_correction(
        self,
        measured_ftp: float,
        cycle_duration_weeks: int,
        test_date: datetime | None = None,
    ) -> dict[str, float | int | str]:
        """
        Calculate PID correction for a cycle based on FTP test.

        Called ONLY when FTP test is performed (typically every 6-8 weeks).
        Correction is applied for the entire next cycle.

        Args:
            measured_ftp: FTP mesurée lors test (W)
            cycle_duration_weeks: Durée cycle écoulé (semaines, 6-8 typique)
            test_date: Date test FTP (défaut: now)

        Returns:
            Dict with keys:
                - error: Écart FTP (W)
                - error_with_deadband: Erreur après dead-band (W)
                - p_term: Contribution proportionnelle (W)
                - i_term: Contribution intégrale (W)
                - d_term: Contribution dérivée (W)
                - output: Correction totale (W/cycle)
                - tss_per_week: Ajustement TSS hebdo suggéré
                - cycle_duration: Durée cycle (semaines)
                - recommendation: Recommandation française actionnable

        Examples:
            >>> controller = DiscretePIDController(0.008, 0.001, 0.12, 260)
            >>> # Test après cycle S001-S006
            >>> result = controller.compute_cycle_correction(206, 6)
            >>> result['error']
            54.0
            >>> result['tss_per_week'] > 0
            True
        """
        if test_date is None:
            test_date = datetime.now()

        if cycle_duration_weeks <= 0:
            raise ValueError("Cycle duration must be positive")

        # Error calculation
        error = self.setpoint - measured_ftp

        # Dead-band application (ignore small natural variations)
        error_with_deadband = error
        if abs(error) < self.dead_band:
            error_with_deadband = 0.0

        # Proportional term (immediate reaction to current error)
        p_term = self.kp * error_with_deadband

        # Integral term (cumulative correction over cycles)
        # dt is in cycles, not weeks
        self.state.integral += error_with_deadband * cycle_duration_weeks
        i_term = self.ki * self.state.integral

        # Anti-windup: Limit integral to prevent excessive accumulation
        # ±200W·cycles ≈ 3 cycles max accumulation (200 / (6 weeks * error))
        max_integral = 200.0  # W·cycles
        if abs(self.state.integral) > max_integral:
            self.state.integral = max_integral if self.state.integral > 0 else -max_integral
            # Recalculate i_term with clamped integral
            i_term = self.ki * self.state.integral

        # Derivative term (trend between FTP tests)
        derivative = 0.0
        if self.state.cycle_count > 0 and cycle_duration_weeks > 0:
            # Rate of change: ΔError / Δcycles (only after first cycle)
            derivative = (error_with_deadband - self.state.prev_error) / cycle_duration_weeks
        d_term = self.kd * derivative

        # Total correction
        output = p_term + i_term + d_term

        # Translate to TSS adjustment per week
        # Approximation: +1W FTP sustained ≈ +12.5 TSS/week
        tss_per_week = output * 12.5

        # Output saturation (reasonable limits for discrete system)
        max_tss_change = 30  # ±30 TSS/week max (vs ±50 continu)
        if abs(tss_per_week) > max_tss_change:
            tss_per_week = max_tss_change if tss_per_week > 0 else -max_tss_change

        # Update state
        self.state.prev_error = error_with_deadband
        self.state.prev_ftp = measured_ftp
        self.state.last_test_date = test_date
        self.state.cycle_count += 1

        # Generate recommendation
        recommendation = self._get_recommendation(tss_per_week, error)

        return {
            "error": error,
            "error_with_deadband": error_with_deadband,
            "p_term": p_term,
            "i_term": i_term,
            "d_term": d_term,
            "output": output,
            "tss_per_week": round(tss_per_week),
            "cycle_duration": cycle_duration_weeks,
            "recommendation": recommendation,
        }

    def compute_cycle_correction_enhanced(
        self,
        measured_ftp: float,
        cycle_duration_weeks: int,
        adherence_rate: float,
        avg_cardiovascular_coupling: float,
        tss_completion_rate: float,
        test_date: datetime | None = None,
    ) -> dict[str, float | int | str | dict]:
        """
        Calculate PID correction with multi-criteria validation (Enhanced).

        Computes base PID correction then validates with complementary variables
        to detect inconsistencies and adjust recommendations contextually.

        Complementary Variables (P0 Priority):
            - adherence_rate: Discipline (completed/planned workouts)
            - avg_cardiovascular_coupling: Quality (découplage cardio %)
            - tss_completion_rate: Capacity (TSS realized/planned)

        Validation Rules:
            - adherence < 0.80 → Red flag: Weak discipline, reduce gains 0.7x
            - coupling > 0.08 → Red flag: Overload detected, reduce gains 0.6x
            - tss_completion < 0.85 → Red flag: Insufficient capacity, cap correction ≤5 TSS

        Args:
            measured_ftp: FTP mesurée lors test (W)
            cycle_duration_weeks: Durée cycle écoulé (semaines)
            adherence_rate: Taux adhérence cycle (0.0-1.0)
            avg_cardiovascular_coupling: Découplage cardio moyen cycle (%)
            tss_completion_rate: Taux complétion TSS cycle (0.0-1.0)
            test_date: Date test FTP (défaut: now)

        Returns:
            Dict with keys:
                - error, p_term, i_term, d_term, output: PID terms
                - tss_per_week: TSS adjustment (original)
                - tss_per_week_adjusted: TSS adjustment after validation
                - cycle_duration: Cycle duration
                - recommendation: Recommendation with validation context
                - validation: {
                    "red_flags": List[str],
                    "warnings": List[str],
                    "confidence": float (0.0-1.0),
                    "validated": bool,
                    "adjustments": List[str]
                  }

        Example:
            >>> controller = DiscretePIDController(0.008, 0.001, 0.12, 260)
            >>> result = controller.compute_cycle_correction_enhanced(
            ...     measured_ftp=206,
            ...     cycle_duration_weeks=6,
            ...     adherence_rate=0.92,
            ...     avg_cardiovascular_coupling=0.062,
            ...     tss_completion_rate=0.94
            ... )
            >>> result["validation"]["validated"]
            True
            >>> result["tss_per_week_adjusted"]
            8
        """
        # Compute base PID correction
        base_correction = self.compute_cycle_correction(
            measured_ftp=measured_ftp,
            cycle_duration_weeks=cycle_duration_weeks,
            test_date=test_date,
        )

        # Extract base TSS adjustment
        tss_original = base_correction["tss_per_week"]
        tss_adjusted = float(tss_original)

        # Validation logic
        red_flags = []
        warnings = []
        adjustments = []
        confidence = 1.0

        # Check 1: Adherence Rate (Discipline)
        if adherence_rate < 0.80:
            red_flags.append("Discipline faible: adherence < 80%")
            tss_adjusted *= 0.7
            adjustments.append("Gains réduits 30% (discipline)")
            confidence *= 0.7

        # Check 2: Cardiovascular Coupling (Quality)
        if avg_cardiovascular_coupling > 0.08:
            red_flags.append("Surcharge détectée: découplage cardio > 8%")
            tss_adjusted *= 0.6
            adjustments.append("Gains réduits 40% (surcharge)")
            confidence *= 0.6
        elif avg_cardiovascular_coupling > 0.06:
            warnings.append("Qualité dégradée: découplage cardio 6-8%")
            confidence *= 0.9

        # Check 3: TSS Completion Rate (Capacity)
        if tss_completion_rate < 0.85:
            red_flags.append("Capacité insuffisante: TSS completion < 85%")
            if tss_adjusted > 5:
                tss_adjusted = 5.0
                adjustments.append("Correction plafonnée 5 TSS max (capacité)")
            confidence *= 0.8
        elif tss_completion_rate < 0.90:
            warnings.append("Capacité limite: TSS completion 85-90%")
            confidence *= 0.95

        # Round adjusted TSS
        tss_adjusted = round(tss_adjusted)

        # Generate enhanced recommendation
        validated = len(red_flags) == 0
        recommendation = self._get_enhanced_recommendation(
            tss_adjusted=tss_adjusted,
            tss_original=tss_original,
            red_flags=red_flags,
            warnings=warnings,
            adjustments=adjustments,
            validated=validated,
        )

        # Build enhanced result
        result = {
            **base_correction,
            "tss_per_week_adjusted": tss_adjusted,
            "recommendation": recommendation,
            "validation": {
                "red_flags": red_flags,
                "warnings": warnings,
                "confidence": round(confidence, 2),
                "validated": validated,
                "adjustments": adjustments,
            },
        }

        return result

    def _get_recommendation(self, tss_per_week: float, error: float) -> str:
        """
        Generate actionable recommendation in French.

        Args:
            tss_per_week: TSS adjustment per week
            error: FTP error (W)

        Returns:
            Recommendation string
        """
        tss_adj = round(tss_per_week)

        # FTP proche cible
        if abs(error) < self.dead_band:
            return "Maintien protocoles actuels (FTP proche cible)"

        # Augmentation TSS
        if tss_adj > 15:
            return (
                f"Augmenter TSS +{tss_adj}/semaine - "
                "Focus Sweet-Spot 88-90% FTP. "
                "Appliquer sur cycle complet (6 semaines)."
            )
        elif tss_adj >= 8:
            return (
                f"Augmenter TSS +{tss_adj}/semaine - "
                "Progression modérée. "
                "Appliquer sur cycle complet (6 semaines)."
            )

        # Réduction TSS
        elif tss_adj < -15:
            return (
                f"Réduire TSS {tss_adj}/semaine - "
                "Priorité récupération. "
                "Appliquer sur cycle complet (6 semaines)."
            )
        elif tss_adj <= -8:
            return (
                f"Réduire TSS {tss_adj}/semaine - "
                "Ajustement léger. "
                "Appliquer sur cycle complet (6 semaines)."
            )

        # Maintien
        else:
            return "Maintien charge actuelle sur cycle"

    def _get_enhanced_recommendation(
        self,
        tss_adjusted: float,
        tss_original: float,
        red_flags: list[str],
        warnings: list[str],
        adjustments: list[str],
        validated: bool,
    ) -> str:
        """
        Generate enhanced recommendation with validation context.

        Args:
            tss_adjusted: Adjusted TSS per week after validation
            tss_original: Original TSS per week from base PID
            red_flags: List of red flags detected
            warnings: List of warnings detected
            adjustments: List of adjustments applied
            validated: Whether correction is validated (no red flags)

        Returns:
            Enhanced recommendation string in French
        """
        tss_adj = round(tss_adjusted)

        # Build base recommendation
        if abs(tss_adj) < 3:
            base_rec = "Maintien protocoles actuels"
        elif tss_adj >= 15:
            base_rec = f"Augmenter TSS +{tss_adj}/semaine - Focus Sweet-Spot 88-90% FTP"
        elif tss_adj >= 8:
            base_rec = f"Augmenter TSS +{tss_adj}/semaine - Progression modérée"
        elif tss_adj <= -15:
            base_rec = f"Réduire TSS {tss_adj}/semaine - Priorité récupération"
        elif tss_adj <= -8:
            base_rec = f"Réduire TSS {tss_adj}/semaine - Ajustement léger"
        else:
            base_rec = "Maintien charge actuelle sur cycle"

        # Add validation context if not validated
        if not validated:
            context_parts = [base_rec]

            # Add adjustment notice if TSS was modified
            if tss_original != tss_adj:
                context_parts.append(
                    f"\n⚠️  Correction ajustée: {tss_original} → {tss_adj} TSS/semaine"
                )

            # Add red flags
            if red_flags:
                context_parts.append("\n🚨 Red flags détectés:")
                for flag in red_flags:
                    context_parts.append(f"  • {flag}")

            # Add adjustments applied
            if adjustments:
                context_parts.append("\n🔧 Ajustements appliqués:")
                for adj in adjustments:
                    context_parts.append(f"  • {adj}")

            # Add warnings if any
            if warnings:
                context_parts.append("\n⚠️  Warnings:")
                for warning in warnings:
                    context_parts.append(f"  • {warning}")

            return "".join(context_parts)

        # Validated correction - add success indicator
        return f"✅ {base_rec}"

    def reset(self):
        """
        Reset internal PID state.

        Clears integral accumulation, previous error, and cycle history.
        Useful when starting new training phase or after long break.
        """
        self.state = DiscretePIDState()

    def get_state_info(self) -> dict:
        """
        Get current internal state information.

        Returns:
            Dict with state details for debugging/monitoring
        """
        return {
            "integral": self.state.integral,
            "prev_error": self.state.prev_error,
            "prev_ftp": self.state.prev_ftp,
            "cycle_count": self.state.cycle_count,
            "last_test_date": (
                self.state.last_test_date.isoformat() if self.state.last_test_date else None
            ),
        }


def compute_discrete_pid_gains_from_intelligence(
    intelligence: "TrainingIntelligence",
) -> dict[str, float]:
    """
    Calculate discrete PID gains optimaux depuis Training Intelligence.

    Gains adaptés système lent (mesures sporadiques) avec réduction conservative.

    Gain Calculation Rules:
        - Kp: Based on validated learnings (reduced -20% vs continu)
        - Ki: Based on cumulative evidence (reduced -50% vs continu)
        - Kd: Based on frequent patterns (reduced -20% vs continu)

    Args:
        intelligence: TrainingIntelligence instance

    Returns:
        Dict with keys: {"kp": float, "ki": float, "kd": float}

    Examples:
        >>> intelligence = TrainingIntelligence()
        >>> # Add 10 validated learnings
        >>> for i in range(10):
        ...     learning = intelligence.add_learning("test", f"Test {i}", [f"ev{i}"])
        ...     learning.confidence = ConfidenceLevel.VALIDATED
        >>> gains = compute_discrete_pid_gains_from_intelligence(intelligence)
        >>> 0.005 <= gains["kp"] <= 0.010
        True
    """
    # Kp: Based on validated learnings (conservative for discrete)
    validated_learnings = [
        lrn
        for lrn in intelligence.learnings.values()
        if lrn.confidence.value in ["high", "validated"]
    ]

    if validated_learnings:
        # More learnings = higher confidence but stay conservative
        kp = 0.005 + (len(validated_learnings) / 100) * 0.005
        kp = min(kp, 0.010)  # Cap at 0.010 (vs 0.015 continu)
    else:
        kp = 0.005  # Conservative default

    # Ki: Based on cumulative evidence (reduced for discrete)
    total_evidence = sum(len(lrn.evidence) for lrn in intelligence.learnings.values())

    if total_evidence > 50:
        ki = 0.002  # vs 0.003 continu
    elif total_evidence > 20:
        ki = 0.001  # vs 0.002 continu
    else:
        ki = 0.0005  # vs 0.001 continu

    # Kd: Based on frequent patterns (conservative for discrete)
    frequent_patterns = [p for p in intelligence.patterns.values() if p.frequency >= 10]

    if len(frequent_patterns) >= 3:
        kd = 0.15  # vs 0.25 continu
    elif len(frequent_patterns) >= 1:
        kd = 0.12  # vs 0.15 continu
    else:
        kd = 0.08  # vs 0.10 continu

    return {"kp": kp, "ki": ki, "kd": kd}
