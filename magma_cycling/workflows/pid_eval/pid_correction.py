"""PID correction evaluation mixin for PID evaluation."""

from typing import Any

from magma_cycling.intelligence.discrete_pid_controller import (
    DiscretePIDController,
    compute_discrete_pid_gains_from_intelligence,
)


class PIDCorrectionMixin:
    """Run discrete PID controller with enhanced validation."""

    def evaluate_pid_correction(
        self,
        measured_ftp: float,
        cycle_duration_weeks: int,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate PID correction with enhanced validation.

        Args:
            measured_ftp: FTP measured (W)
            cycle_duration_weeks: Cycle duration (weeks)
            metrics: Cycle metrics dict

        Returns:
            PID correction result dict
        """
        print(f"\n{'=' * 60}")
        print("🎛️  PID Correction Evaluation")
        print(f"{'=' * 60}")

        # Calculate adaptive gains from intelligence
        gains = compute_discrete_pid_gains_from_intelligence(self.intelligence)
        print("\nAdaptive PID Gains:")
        print(f"   Kp: {gains['kp']:.4f}")
        print(f"   Ki: {gains['ki']:.4f}")
        print(f"   Kd: {gains['kd']:.4f}")

        # Get FTP setpoint from athlete profile (fallback to measured)
        try:
            from magma_cycling.config import AthleteProfile

            setpoint = AthleteProfile.from_env().ftp
        except Exception:
            setpoint = measured_ftp

        # Create PID controller
        controller = DiscretePIDController(
            kp=gains["kp"],
            ki=gains["ki"],
            kd=gains["kd"],
            setpoint=setpoint,
        )

        # Compute enhanced correction
        result = controller.compute_cycle_correction_enhanced(
            measured_ftp=measured_ftp,
            cycle_duration_weeks=cycle_duration_weeks,
            adherence_rate=metrics["adherence_rate"],
            avg_cardiovascular_coupling=metrics["avg_cardiovascular_coupling"],
            tss_completion_rate=metrics["tss_completion_rate"],
        )

        print("\n📊 PID Results:")
        print(f"   FTP Error: {result['error']:.1f}W")
        print(f"   TSS Adjustment: {result['tss_per_week_adjusted']} TSS/week")
        print(f"   Validated: {'✅' if result['validation']['validated'] else '⚠️ '}")
        print(f"   Confidence: {result['validation']['confidence']}")

        if result["validation"]["red_flags"]:
            print("\n🚨 Red Flags:")
            for flag in result["validation"]["red_flags"]:
                print(f"   • {flag}")

        print("\n💡 Recommendation:")
        print(f"   {result['recommendation']}")

        return result
