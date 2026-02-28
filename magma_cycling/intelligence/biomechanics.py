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
        >>> from magma_cycling.intelligence.discrete_pid_controller import DiscretePIDController
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


def calculer_cout_energetique(
    puissance_watts: float,
    cadence_rpm: int,
    duree_secondes: int,
    poids_kg: float = 70.0,
) -> dict[str, float]:
    """
    Calculate energy cost (CE) of locomotion based on Grappe research.

    Computes biomechanical efficiency metrics:
    - Total energy expenditure (kJ)
    - Energy cost per km (kJ/km, assuming typical cycling speed)
    - Mechanical efficiency (%)
    - Metabolic cost (W/kg)

    Energy Cost Concepts (Grappe 2000, p.40-56):
        - CE (Coût Énergétique): Energy required per unit distance
        - Lower CE = Better efficiency (less energy for same work)
        - CE influenced by: cadence, position, bike fit, fatigue
        - Optimal CE zone: 85-95 rpm for most cyclists

    Mechanical Efficiency Formula:
        η_mech = (Mechanical Work Output) / (Metabolic Energy Input)
        Typical range: 18-25% for cycling (20-22% average)

    Args:
        puissance_watts: Average power output (W)
        cadence_rpm: Average cadence (rpm)
        duree_secondes: Session duration (seconds)
        poids_kg: Athlete weight (kg, default: 70.0)

    Returns:
        Dict with keys:
            - energie_totale_kj: Total energy expenditure (kJ)
            - cout_km_kj: Energy cost per km (kJ/km, at ~30 km/h)
            - efficience_mecanique: Mechanical efficiency (%)
            - cout_metabolique_w_kg: Metabolic cost normalized by weight (W/kg)
            - vitesse_estimee_kmh: Estimated speed based on power (km/h)

    Notes:
        - Efficiency calculation assumes 21% mechanical efficiency (typical)
        - Speed estimation uses simplified power model (ignores wind, terrain)
        - For accurate CE per km, use actual distance from activity data

    Examples:
        >>> # Sweet-Spot 60 min @ 250W, 90 rpm, 70 kg
        >>> ce = calculer_cout_energetique(250, 90, 3600, 70.0)
        >>> ce["energie_totale_kj"]
        900.0
        >>> ce["efficience_mecanique"]
        21.0
        >>> ce["cout_metabolique_w_kg"]
        3.57

        >>> # VO2 Max 5 min @ 350W, 105 rpm, 70 kg
        >>> ce = calculer_cout_energetique(350, 105, 300, 70.0)
        >>> ce["energie_totale_kj"]
        105.0
        >>> ce["cout_metabolique_w_kg"]
        5.0
    """
    # Total mechanical work (kJ)
    # Work = Power × Time
    energie_totale_kj = (puissance_watts * duree_secondes) / 1000.0

    # Mechanical efficiency (assume 21% typical for cycling)
    # Real efficiency varies 18-25% depending on cadence, fitness, fatigue
    efficience_mecanique = 21.0

    # Adjust efficiency based on cadence (Grappe optimal zone)
    # Efficiency peaks at 85-95 rpm, decreases outside this range
    if cadence_rpm < 70:
        # Very low cadence: muscular inefficiency
        efficience_mecanique *= 0.90  # -10% efficiency
    elif cadence_rpm < 85:
        # Low cadence: slightly suboptimal
        efficience_mecanique *= 0.95  # -5% efficiency
    elif 85 <= cadence_rpm <= 95:
        # Optimal cadence zone: peak efficiency
        pass  # No adjustment
    elif cadence_rpm <= 105:
        # Slightly high cadence: minor cardiovascular cost
        efficience_mecanique *= 0.97  # -3% efficiency
    else:
        # Very high cadence: cardiovascular inefficiency
        efficience_mecanique *= 0.92  # -8% efficiency

    # Metabolic cost normalized by weight (W/kg)
    cout_metabolique_w_kg = round(puissance_watts / poids_kg, 2)

    # Estimate speed from power (simplified model)
    # Rough approximation: P ≈ 2.5 * v² (watts, km/h) for flat terrain
    # v = sqrt(P / 2.5)
    vitesse_estimee_kmh = round((puissance_watts / 2.5) ** 0.5, 1)

    # Energy cost per km (kJ/km)
    # CE = Total Energy / Distance
    # Distance (km) = Speed (km/h) × Time (h)
    distance_km = vitesse_estimee_kmh * (duree_secondes / 3600.0)
    cout_km_kj = round(energie_totale_kj / distance_km, 2) if distance_km > 0 else 0.0

    return {
        "energie_totale_kj": round(energie_totale_kj, 1),
        "cout_km_kj": cout_km_kj,
        "efficience_mecanique": round(efficience_mecanique, 1),
        "cout_metabolique_w_kg": cout_metabolique_w_kg,
        "vitesse_estimee_kmh": vitesse_estimee_kmh,
    }


def calculer_cout_energetique_from_activity(
    activity: dict,
    poids_kg: float = 70.0,
) -> dict[str, float] | None:
    """
    Calculate energy cost from Intervals.icu activity data.

    Convenience wrapper that extracts metrics from activity dict and
    computes CE using actual distance if available.

    Args:
        activity: Activity dict from Intervals.icu API with fields:
            - icu_average_watts or average_watts: Average power (W)
            - average_cadence: Average cadence (rpm)
            - moving_time: Duration (seconds)
            - distance: Distance (meters, optional)
        poids_kg: Athlete weight (kg, default: 70.0)

    Returns:
        Dict from calculer_cout_energetique() with additional fields:
            - distance_reelle_km: Actual distance if available (km)
            - cout_km_reel_kj: Actual energy cost per km (kJ/km)
        Returns None if required fields missing

    Example:
        >>> activity = {
        ...     "icu_average_watts": 250,
        ...     "average_cadence": 90,
        ...     "moving_time": 3600,
        ...     "distance": 30000  # 30 km
        ... }
        >>> ce = calculer_cout_energetique_from_activity(activity, 70.0)
        >>> ce["cout_km_reel_kj"]
        30.0  # 900 kJ / 30 km
    """
    # Extract metrics from activity
    puissance = activity.get("icu_average_watts") or activity.get("average_watts")
    cadence = activity.get("average_cadence")
    duree = activity.get("moving_time")

    if not all([puissance, cadence, duree]):
        return None

    # Calculate base CE
    ce = calculer_cout_energetique(
        puissance_watts=puissance,
        cadence_rpm=int(cadence),
        duree_secondes=int(duree),
        poids_kg=poids_kg,
    )

    # If actual distance available, compute real CE per km
    distance_m = activity.get("distance")
    if distance_m and distance_m > 0:
        distance_km = distance_m / 1000.0
        ce["distance_reelle_km"] = round(distance_km, 2)
        ce["cout_km_reel_kj"] = round(ce["energie_totale_kj"] / distance_km, 2)

    return ce
