"""PIDMixin — Continuous and discrete PID corrections for FTP progression."""

from typing import Any


class PIDMixin:
    """PID correction methods (continuous and discrete)."""

    def get_pid_correction(
        self, current_ftp: float, target_ftp: float, dt: float = 1.0
    ) -> dict[str, Any]:
        """Get correction PID automatique pour progression FTP.

        Calcule gains PID adaptatifs depuis intelligence accumulee,
        puis compute correction TSS recommandee.

        Args:
            current_ftp: FTP actuelle (W)
            target_ftp: FTP cible (W)
            dt: Delta temps depuis derniere correction (semaines, defaut 1.0)

        Returns:
            Dict with keys:
                - correction: Dict from PIDController.compute()
                - recommendation: str action suggeree (francais)
                - gains: {"kp": float, "ki": float, "kd": float}

        Example:
            >>> intelligence = TrainingIntelligence.load_from_file(Path("intelligence.json"))
            >>> result = intelligence.get_pid_correction(
            ...     current_ftp=220,
            ...     target_ftp=260,
            ...     dt=1.0
            ... )
            >>> print(result["recommendation"])
            Augmenter TSS +25/semaine - Focus Sweet-Spot 88-90% FTP
        """
        from magma_cycling.intelligence.pid_controller import (
            PIDController,
            compute_pid_gains_from_intelligence,
        )

        # Calculate gains from current intelligence
        gains = compute_pid_gains_from_intelligence(self)

        # Initialize PID controller
        pid = PIDController(kp=gains["kp"], ki=gains["ki"], kd=gains["kd"], setpoint=target_ftp)

        # Compute correction
        correction = pid.compute(current_ftp, dt)
        recommendation = pid.get_action_recommendation(correction)

        return {"correction": correction, "recommendation": recommendation, "gains": gains}

    def get_discrete_pid_correction(
        self,
        measured_ftp: float,
        target_ftp: float,
        cycle_duration_weeks: int = 6,
    ) -> dict[str, Any]:
        """Get correction PID Discret pour progression FTP (mesures sporadiques).

        Calcule gains PID adaptatifs depuis intelligence accumulee,
        puis compute correction TSS recommandee niveau cycle.

        Architecture:
            - Appele UNIQUEMENT lors test FTP valide (tous les 6-8 semaines)
            - Correction appliquee sur cycle complet (sample-and-hold)
            - Gains conservateurs adaptes systeme lent

        Args:
            measured_ftp: FTP mesuree lors test (W)
            target_ftp: FTP cible (W)
            cycle_duration_weeks: Duree cycle ecoule (semaines, 6-8 typique)

        Returns:
            Dict with keys:
                - correction: Dict from DiscretePIDController.compute_cycle_correction()
                - recommendation: str action suggeree (francais)
                - gains: {"kp": float, "ki": float, "kd": float}

        Example:
            >>> intelligence = TrainingIntelligence.load_from_file(Path("intelligence.json"))
            >>> result = intelligence.get_discrete_pid_correction(
            ...     measured_ftp=206,
            ...     target_ftp=260,
            ...     cycle_duration_weeks=6
            ... )
            >>> print(result["correction"]["tss_per_week"])
            8
            >>> print(result["recommendation"])
            Augmenter TSS +8/semaine - Progression moderee. Appliquer sur cycle complet (6 semaines).
        """
        from magma_cycling.intelligence.discrete_pid_controller import (
            DiscretePIDController,
            compute_discrete_pid_gains_from_intelligence,
        )

        # Calculate gains from current intelligence (conservative for discrete)
        gains = compute_discrete_pid_gains_from_intelligence(self)

        # Initialize Discrete PID controller
        pid = DiscretePIDController(
            kp=gains["kp"],
            ki=gains["ki"],
            kd=gains["kd"],
            setpoint=target_ftp,
            dead_band=3.0,  # Ignore +/-3W natural variations
        )

        # Compute cycle correction
        correction = pid.compute_cycle_correction(
            measured_ftp=measured_ftp,
            cycle_duration_weeks=cycle_duration_weeks,
        )

        # Recommendation already in correction dict
        recommendation = correction["recommendation"]

        return {"correction": correction, "recommendation": recommendation, "gains": gains}
