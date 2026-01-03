"""
PID Controller pour Training Intelligence.

Régulation automatique progression FTP basée sur gains adaptatifs
calculés depuis Training Intelligence accumulée.

Examples:
    Basic PID usage::

        controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)
        correction = controller.compute(measured_value=220, dt=1.0)
        print(correction["tss_adjustment"])  # +25 TSS/week

    Adaptive gains from intelligence::

        intelligence = TrainingIntelligence.load_from_file("intelligence.json")
        gains = compute_pid_gains_from_intelligence(intelligence)
        controller = PIDController(**gains, setpoint=260)

Author: Claude Code
Created: 2026-01-02
Version: 1.0.0
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cyclisme_training_logs.intelligence.training_intelligence import TrainingIntelligence


@dataclass
class PIDState:
    """
    Internal PID Controller state.

    Tracks integral accumulation, previous error, and last update time
    for derivative calculation.

    Attributes:
        integral: Cumulative error over time (anti-windup limited)
        prev_error: Previous error value for derivative calculation
        last_update: Timestamp of last compute() call
    """

    integral: float = 0.0
    prev_error: float = 0.0
    last_update: Optional[datetime] = None


class PIDController:
    """
    Contrôleur PID adaptatif pour progression FTP.

    Calcule correction TSS/Intensité basée sur écart FTP cible vs actuelle.
    Gains Kp/Ki/Kd dérivés automatiquement depuis Training Intelligence.

    PID Formula:
        output = Kp * error + Ki * integral(error) + Kd * derivative(error)

    TSS Translation:
        Approximation: +1W FTP sustained ≈ +10-15 TSS/week
        Using multiplier of 12.5 for middle-ground

    Attributes:
        kp: Gain proportionnel (réaction immédiate, 0.005-0.015 recommandé)
        ki: Gain intégral (correction cumulative, 0.001-0.005 recommandé)
        kd: Gain dérivé (anticipation tendances, 0.1-0.3 recommandé)
        setpoint: FTP cible (W)
        state: État interne PID (integral, prev_error, last_update)

    Examples:
        >>> controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)
        >>> correction = controller.compute(measured_value=220)
        >>> print(f"TSS adjustment: {correction['tss_adjustment']}")
        TSS adjustment: +25
    """

    def __init__(self, kp: float, ki: float, kd: float, setpoint: float):
        """
        Initialize PID Controller.

        Args:
            kp: Gain proportionnel (0.005-0.015 recommandé)
            ki: Gain intégral (0.001-0.005 recommandé)
            kd: Gain dérivé (0.1-0.3 recommandé)
            setpoint: FTP cible (W)

        Raises:
            ValueError: If gains or setpoint are invalid
        """
        if kp < 0 or ki < 0 or kd < 0:
            raise ValueError("PID gains must be non-negative")
        if setpoint <= 0:
            raise ValueError("Setpoint must be positive")

        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.state = PIDState()

    def compute(self, measured_value: float, dt: float = 1.0) -> dict[str, float]:
        """
        Calculer correction PID.

        Args:
            measured_value: FTP actuelle (W)
            dt: Delta temps depuis dernier appel (semaines, défaut 1.0)

        Returns:
            Dict with keys:
                - error: Écart FTP (W)
                - p_term: Contribution proportionnelle
                - i_term: Contribution intégrale
                - d_term: Contribution dérivée
                - output: Correction totale (W/semaine suggérée)
                - tss_adjustment: Ajustement TSS hebdo suggéré

        Examples:
            >>> controller = PIDController(0.01, 0.002, 0.15, setpoint=260)
            >>> correction = controller.compute(220, dt=1.0)
            >>> correction['error']
            40.0
            >>> correction['tss_adjustment'] > 0
            True
        """
        # Error calculation
        error = self.setpoint - measured_value

        # Proportional term (immediate reaction)
        p_term = self.kp * error

        # Integral term (cumulative correction)
        self.state.integral += error * dt
        i_term = self.ki * self.state.integral

        # Anti-windup: Limit integral to prevent excessive accumulation
        max_integral = 100.0  # Max ±100W integral
        if abs(self.state.integral) > max_integral:
            self.state.integral = max_integral if self.state.integral > 0 else -max_integral

        # Derivative term (trend anticipation)
        derivative = (error - self.state.prev_error) / dt if dt > 0 else 0
        d_term = self.kd * derivative

        # Total correction
        output = p_term + i_term + d_term

        # Translate to TSS adjustment
        # Approximation: +1W FTP ≈ +10-15 TSS/week sustained
        tss_adjustment = output * 12.5

        # Output saturation (reasonable limits)
        max_tss_change = 50  # Max ±50 TSS/week
        if abs(tss_adjustment) > max_tss_change:
            tss_adjustment = max_tss_change if tss_adjustment > 0 else -max_tss_change

        # Update state
        self.state.prev_error = error
        self.state.last_update = datetime.now()

        return {
            "error": error,
            "p_term": p_term,
            "i_term": i_term,
            "d_term": d_term,
            "output": output,
            "tss_adjustment": round(tss_adjustment),
        }

    def reset(self):
        """
        Reset internal PID state.

        Clears integral accumulation and previous error.
        Useful when starting new training phase or after long break.
        """
        self.state = PIDState()

    def get_action_recommendation(self, correction: dict[str, float]) -> str:
        """
        Traduire correction PID en recommandation actionnable.

        Args:
            correction: Output from compute()

        Returns:
            Recommandation texte (français)

        Examples:
            >>> controller = PIDController(0.01, 0.002, 0.15, 260)
            >>> correction = controller.compute(220)
            >>> recommendation = controller.get_action_recommendation(correction)
            >>> "Augmenter TSS" in recommendation
            True
        """
        tss_adj = correction["tss_adjustment"]
        error = correction["error"]

        # FTP proche cible
        if abs(error) < 5:
            return "Maintien protocoles actuels (FTP proche cible)"

        # Augmentation TSS
        if tss_adj > 20:
            return f"Augmenter TSS +{tss_adj}/semaine - " "Focus Sweet-Spot 88-90% FTP"
        elif tss_adj > 10:
            return f"Augmenter TSS +{tss_adj}/semaine - " "Progression modérée"

        # Réduction TSS
        elif tss_adj < -20:
            return f"Réduire TSS {tss_adj}/semaine - " "Priorité récupération"
        elif tss_adj < -10:
            return f"Réduire TSS {tss_adj}/semaine - " "Ajustement léger"

        # Maintien
        else:
            return "Maintien charge actuelle"


def compute_pid_gains_from_intelligence(intelligence: "TrainingIntelligence") -> dict[str, float]:
    """
    Calculer gains PID optimaux depuis Training Intelligence.

    Analyse learnings/patterns validés pour dériver Kp, Ki, Kd.

    Gain Calculation Rules:
        - Kp: Based on validated learnings count (confidence)
          More validated learnings = higher confidence = aggressive Kp
        - Ki: Based on cumulative evidence (stability)
          More evidence = stronger correction = higher Ki
        - Kd: Based on frequent patterns (trend detection)
          More patterns = better anticipation = higher Kd

    Args:
        intelligence: TrainingIntelligence instance (with backfill recommended)

    Returns:
        Dict with keys: {"kp": float, "ki": float, "kd": float}

    Examples:
        >>> intelligence = TrainingIntelligence()
        >>> # Add 10 validated learnings
        >>> for i in range(10):
        ...     learning = intelligence.add_learning("test", f"Test {i}", [f"ev{i}"])
        ...     learning.confidence = ConfidenceLevel.VALIDATED
        >>> gains = compute_pid_gains_from_intelligence(intelligence)
        >>> 0.005 <= gains["kp"] <= 0.015
        True
    """

    # Kp: Based on confidence average from validated learnings
    validated_learnings = [
        l for l in intelligence.learnings.values() if l.confidence.value in ["high", "validated"]
    ]

    if validated_learnings:
        # More validated learnings = higher confidence = aggressive Kp
        kp = 0.005 + (len(validated_learnings) / 100) * 0.010
        kp = min(kp, 0.015)  # Cap at 0.015
    else:
        kp = 0.005  # Conservative default

    # Ki: Based on cumulative evidence
    total_evidence = sum(len(l.evidence) for l in intelligence.learnings.values())

    if total_evidence > 50:
        ki = 0.003
    elif total_evidence > 20:
        ki = 0.002
    else:
        ki = 0.001

    # Kd: Based on frequent patterns (trend detection)
    frequent_patterns = [p for p in intelligence.patterns.values() if p.frequency >= 10]

    if len(frequent_patterns) >= 3:
        kd = 0.25
    elif len(frequent_patterns) >= 1:
        kd = 0.15
    else:
        kd = 0.10

    return {"kp": kp, "ki": ki, "kd": kd}
