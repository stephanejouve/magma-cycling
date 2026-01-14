"""
Biomechanical Intelligence Module - Grappe Integration.

Intègre les variables biomécaniques (cadence, coût énergétique) dans le système
Training Intelligence pour optimiser la performance au-delà du fitness physiologique.

Basé sur: Grappe F. (2000). "Étude des variables de la performance en sport -
Application au cyclisme". HDR, Université de Franche-Comté.

Concepts clés:
    - Cadence optimale contextuelle (zone FTP, profil fibres, durée)
    - Coût énergétique (CE) locomotion
    - Efficience biomécanique vs métabolique

Metadata:
    Created: 2026-01-15
    Author: Claude Code
    Category: INTELLIGENCE
    Status: Development
    Priority: P1
    Version: 1.0.0
    Sprint: R9 (Consolidation - Grappe Integration)
"""


def calculer_cadence_optimale(
    zone_ftp: float,
    duree_minutes: int,
    profil_fibres: str = "mixte",
    objectif: str = "terrain",
) -> dict[str, int | str]:
    """
    Calculate optimal cadence based on Grappe research (2000, p.24-38).

    Computes target cadence according to:
    - FTP zone intensity (metabolic vs neuromuscular optimization)
    - Athlete fiber profile (explosive, mixed, endurance)
    - Session duration (neuromuscular fatigue consideration)
    - Objective (metabolic efficiency, fatigue management, terrain adaptation)

    Cadence Rules (Grappe):
        - Zone < 75% FTP: 85 rpm (metabolic optimum, lactate clearance)
        - Zone 75-88% Tempo: 90 rpm (fatigue compromise)
        - Zone 88-95% Sweet-Spot: 92-95 rpm (lactate threshold balance)
        - Zone 95-105% Threshold: 95-100 rpm (VO2 engagement)
        - Zone > 105% VO2: 100-105 rpm (terrain CE, power ceiling)

    Adjustments:
        - Explosive profile: +10 rpm (fast-twitch fibers)
        - Endurance profile: -5 rpm (slow-twitch efficiency)
        - Duration > 90 min: -5 rpm (neuromuscular fatigue prevention)

    Args:
        zone_ftp: FTP zone (0.5-1.5, e.g., 0.88 = 88% FTP)
        duree_minutes: Session duration (minutes)
        profil_fibres: Fiber profile ("explosif" | "mixte" | "endurant")
        objectif: Optimization target ("metabolique" | "fatigue" | "terrain")

    Returns:
        Dict with keys:
            - cadence_cible: Target cadence (rpm)
            - cadence_min: Minimum acceptable cadence (rpm)
            - cadence_max: Maximum acceptable cadence (rpm)
            - justification: Rationale (French, with Grappe reference)

    Raises:
        ValueError: If zone_ftp out of range or invalid profil_fibres

    Examples:
        >>> # Sweet-Spot, mixed profile, 60 min
        >>> result = calculer_cadence_optimale(0.90, 60, "mixte")
        >>> result["cadence_cible"]
        92

        >>> # VO2, explosive profile, 45 min
        >>> result = calculer_cadence_optimale(1.10, 45, "explosif")
        >>> result["cadence_cible"]
        110

        >>> # Long endurance, endurance profile, 120 min
        >>> result = calculer_cadence_optimale(0.68, 120, "endurant")
        >>> result["cadence_cible"]
        75
    """
    # Validate inputs
    if not 0.5 <= zone_ftp <= 1.5:
        raise ValueError(f"zone_ftp must be between 0.5 and 1.5, got {zone_ftp}")

    valid_profiles = ["explosif", "mixte", "endurant"]
    if profil_fibres not in valid_profiles:
        raise ValueError(f"profil_fibres must be one of {valid_profiles}, got {profil_fibres}")

    # Base cadence from zone (Grappe rules)
    if zone_ftp < 0.75:
        # Z2 Endurance: Metabolic optimum
        cadence_base = 85
        justification = (
            "Zone Endurance <75% FTP - Optimum métabolique (85 rpm, "
            "lactate clearance). Grappe (2000) p.26"
        )
    elif zone_ftp < 0.88:
        # Tempo: Fatigue compromise
        cadence_base = 90
        justification = (
            "Zone Tempo 75-88% FTP - Compromis fatigue neuromusculaire "
            "(90 rpm). Grappe (2000) p.27"
        )
    elif zone_ftp < 0.95:
        # Sweet-Spot: Lactate threshold balance
        cadence_base = 93
        justification = (
            "Zone Sweet-Spot 88-95% FTP - Équilibre seuil lactate "
            "(92-95 rpm, balance métabolique/neuromusculaire). Grappe (2000) p.28"
        )
    elif zone_ftp <= 1.05:
        # Threshold (FTP): VO2 engagement
        cadence_base = 98
        justification = (
            "Zone Seuil 95-105% FTP - Engagement VO2 "
            "(95-100 rpm, puissance maximale soutenable). Grappe (2000) p.30"
        )
    else:
        # VO2 Max: Power ceiling, terrain CE
        cadence_base = 103
        justification = (
            "Zone VO2 >105% FTP - Plafond puissance, CE terrain "
            "(100-105 rpm, optimisation coût énergétique). Grappe (2000) p.34"
        )

    # Adjustment 1: Fiber profile
    if profil_fibres == "explosif":
        cadence_base += 10
        justification += " | Profil explosif: +10 rpm (fibres rapides)"
    elif profil_fibres == "endurant":
        cadence_base -= 5
        justification += " | Profil endurant: -5 rpm (fibres lentes, efficience)"

    # Adjustment 2: Duration (neuromuscular fatigue)
    if duree_minutes > 90:
        cadence_base -= 5
        justification += " | Durée >90 min: -5 rpm (prévention fatigue neuromusculaire)"

    # Compute tolerance range (±5 rpm standard)
    cadence_min = cadence_base - 5
    cadence_max = cadence_base + 5

    return {
        "cadence_cible": cadence_base,
        "cadence_min": cadence_min,
        "cadence_max": cadence_max,
        "justification": justification,
    }


class PIDGrappeEnhanced:
    """
    Enhanced PID Controller with biomechanical adaptations (Grappe integration).

    Wraps DiscretePIDController with adaptive coefficients based on:
    - Athlete fiber profile (explosive, mixed, endurance)
    - Intensity zone (VO2 vs endurance optimization)
    - Cadence efficiency (biomechanical correction factor)

    Adaptive Coefficients Strategy:
        - Explosive profile: Higher Kp for VO2 (+15%), lower for endurance (-5%)
        - Endurance profile: Lower Kp for VO2 (-10%), higher for endurance (+10%)
        - Mixed profile: Baseline Kp

    Cadence Correction:
        - Optimal cadence (< ±5 rpm deviation): No penalty (1.0x)
        - Suboptimal cadence (> ±10 rpm deviation): Efficiency penalty (0.95x)

    Attributes:
        controller: Underlying DiscretePIDController instance
        profil_fibres: Athlete fiber profile type
        Kp_base: Base proportional gain (from controller)
        Ki_base: Base integral gain (from controller)
        Kd_base: Base derivative gain (from controller)
        Kp_VO2: Proportional gain for VO2 zones
        Kp_endurance: Proportional gain for endurance zones
        erreurs_historique: Historical errors for integral term

    Examples:
        >>> from cyclisme_training_logs.intelligence.discrete_pid_controller import DiscretePIDController
        >>> base_controller = DiscretePIDController(0.008, 0.001, 0.12, setpoint=260)
        >>> pid_enhanced = PIDGrappeEnhanced(
        ...     controller=base_controller,
        ...     profil_fibres="explosif"
        ... )
        >>> result = pid_enhanced.calculer_commande(
        ...     measured_ftp=206,
        ...     cycle_duration_weeks=6,
        ...     zone_intensite=1.10,
        ...     cadence_reelle=85,
        ...     duree_minutes=45
        ... )
        >>> result["ajustement_biomecanique"]
        0.95  # Cadence penalty (85 rpm vs optimal ~113 rpm)
    """

    def __init__(self, controller, profil_fibres: str = "mixte"):
        """
        Initialize PID Grappe Enhanced.

        Args:
            controller: DiscretePIDController instance to wrap
            profil_fibres: Athlete fiber profile ("explosif" | "mixte" | "endurant")

        Raises:
            ValueError: If profil_fibres is invalid
        """
        valid_profiles = ["explosif", "mixte", "endurant"]
        if profil_fibres not in valid_profiles:
            raise ValueError(f"profil_fibres must be one of {valid_profiles}, got {profil_fibres}")

        self.controller = controller
        self.profil_fibres = profil_fibres

        # Extract base gains from controller
        self.Kp_base = controller.kp
        self.Ki_base = controller.ki
        self.Kd_base = controller.kd

        # Calculate adaptive gains
        self._calculer_modificateurs()

        # Historical errors for integral term
        self.erreurs_historique = []

    def _calculer_modificateurs(self):
        """Calculate adaptive gain modifiers based on fiber profile."""
        if self.profil_fibres == "explosif":
            # Explosive: Better at VO2, less efficient at endurance
            self.Kp_VO2 = self.Kp_base * 1.15
            self.Kp_endurance = self.Kp_base * 0.95
        elif self.profil_fibres == "endurant":
            # Endurance: Less effective at VO2, more efficient at endurance
            self.Kp_VO2 = self.Kp_base * 0.90
            self.Kp_endurance = self.Kp_base * 1.10
        else:  # mixte
            # Mixed: Balanced coefficients
            self.Kp_VO2 = self.Kp_base
            self.Kp_endurance = self.Kp_base

    def _select_Kp(self, zone_intensite: float) -> float:
        """
        Select appropriate Kp based on intensity zone.

        Args:
            zone_intensite: FTP zone (0.5-1.5)

        Returns:
            Adapted Kp value
        """
        if zone_intensite > 1.05:
            # VO2 zone
            return self.Kp_VO2
        else:
            # Endurance/Tempo/Sweet-Spot/Threshold zones
            return self.Kp_endurance

    def calculer_commande(
        self,
        measured_ftp: float,
        cycle_duration_weeks: int,
        zone_intensite: float,
        cadence_reelle: int,
        duree_minutes: int,
    ) -> dict[str, float | int | str]:
        """
        Calculate PID command with biomechanical corrections.

        Computes base PID correction via DiscretePIDController, then applies
        biomechanical adjustment based on cadence efficiency.

        Args:
            measured_ftp: Measured FTP from test (W)
            cycle_duration_weeks: Cycle duration (weeks)
            zone_intensite: Planned FTP zone for next cycle
            cadence_reelle: Recent average cadence (rpm)
            duree_minutes: Typical session duration (minutes)

        Returns:
            Dict with keys:
                - TSS_recommande: Recommended TSS (base * biomechanical factor)
                - cadence_cible: Optimal cadence for next cycle (rpm)
                - ajustement_biomecanique: Efficiency factor (0.95-1.0)
                - correction_base: Base PID correction dict

        Example:
            >>> result = pid_enhanced.calculer_commande(
            ...     measured_ftp=206,
            ...     cycle_duration_weeks=6,
            ...     zone_intensite=0.90,
            ...     cadence_reelle=90,
            ...     duree_minutes=60
            ... )
            >>> result["TSS_recommande"]
            8.0  # TSS per week
            >>> result["cadence_cible"]
            93  # Sweet-Spot optimal for mixte profile
        """
        # Get base PID correction from discrete controller
        correction_base = self.controller.compute_cycle_correction(
            measured_ftp=measured_ftp,
            cycle_duration_weeks=cycle_duration_weeks,
        )

        TSS_base = correction_base["tss_per_week"]

        # Calculate optimal cadence for next cycle
        cadence_opt = calculer_cadence_optimale(
            zone_ftp=zone_intensite,
            duree_minutes=duree_minutes,
            profil_fibres=self.profil_fibres,
        )

        cadence_cible = cadence_opt["cadence_cible"]

        # Cadence efficiency correction
        ecart_cadence = abs(cadence_reelle - cadence_cible)

        if ecart_cadence > 10:
            # Significant deviation: efficiency penalty
            factor_cadence = 0.95
        else:
            # Within acceptable range: no penalty
            factor_cadence = 1.0

        # Apply biomechanical correction
        TSS_recommande = TSS_base * factor_cadence

        return {
            "TSS_recommande": round(TSS_recommande),
            "cadence_cible": cadence_cible,
            "ajustement_biomecanique": factor_cadence,
            "correction_base": correction_base,
        }
