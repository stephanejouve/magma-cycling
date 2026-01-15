"""
Integration tests for Biomechanics Module (Grappe Integration).

Tests complete workflows combining multiple biomechanics components:
- PIDGrappeEnhanced + DiscretePIDController
- biomechanics_intervals + calculer_cadence_optimale
- AthleteProfile + biomechanics recommendations
- Full workflow: Intervals.icu API → Grappe recommendations → PID Enhanced
"""

import pytest

from cyclisme_training_logs.config.athlete_profile import AthleteProfile
from cyclisme_training_logs.intelligence.biomechanics import (
    PIDGrappeEnhanced,
    calculer_cadence_optimale,
    calculer_cout_energetique_from_activity,
)
from cyclisme_training_logs.intelligence.biomechanics_intervals import (
    extract_biomechanical_metrics,
    get_cadence_recommendation_from_activities,
)
from cyclisme_training_logs.intelligence.discrete_pid_controller import (
    DiscretePIDController,
)


class TestPIDGrappeIntegration:
    """Integration tests for PIDGrappeEnhanced + DiscretePIDController."""

    def test_full_pid_workflow_explosif_athlete(self):
        """Test complete PID workflow for explosive athlete."""
        # Setup: Explosive athlete, current FTP 206W, target 260W
        base_controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)
        pid_enhanced = PIDGrappeEnhanced(controller=base_controller, profil_fibres="explosif")

        # Scenario: VO2 workout, athlete using 85 rpm (too low for explosif at VO2)
        result = pid_enhanced.calculer_commande(
            measured_ftp=206,
            cycle_duration_weeks=6,
            zone_intensite=1.10,  # VO2
            cadence_reelle=85,  # Too low
            duree_minutes=45,
        )

        # Assertions
        assert result["cadence_cible"] == 113  # VO2 103 + explosif 10
        assert result["ajustement_biomecanique"] == 0.95  # Penalty for low cadence
        assert "TSS_recommande" in result
        assert "correction_base" in result

        # Verify base PID calculated correction
        base_correction = result["correction_base"]
        assert base_correction["error"] == 54  # 260 - 206
        # Recommendation should start with expected action
        assert (
            base_correction["recommendation"].startswith("Augmenter TSS")
            or base_correction["recommendation"].startswith("Maintien TSS")
            or base_correction["recommendation"].startswith("Réduire TSS")
        )

    def test_full_pid_workflow_endurant_athlete(self):
        """Test complete PID workflow for endurance athlete."""
        base_controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)
        pid_enhanced = PIDGrappeEnhanced(controller=base_controller, profil_fibres="endurant")

        # Scenario: Long endurance ride, athlete using 78 rpm (good for endurant)
        result = pid_enhanced.calculer_commande(
            measured_ftp=206,
            cycle_duration_weeks=6,
            zone_intensite=0.68,  # Endurance
            cadence_reelle=78,  # Good for endurant + long
            duree_minutes=150,
        )

        # Assertions
        assert result["cadence_cible"] == 75  # 85 - 5 endurant - 5 duration
        assert result["ajustement_biomecanique"] == 1.0  # Within tolerance (±5 rpm)
        assert result["TSS_recommande"] > 0

    def test_adaptive_gains_explosif_vs_endurant(self):
        """Test adaptive gains differ between explosive and endurance profiles."""
        base_controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

        pid_explosif = PIDGrappeEnhanced(controller=base_controller, profil_fibres="explosif")
        pid_endurant = PIDGrappeEnhanced(controller=base_controller, profil_fibres="endurant")

        # VO2 zone: explosif should have higher Kp
        assert pid_explosif.Kp_VO2 == pytest.approx(0.008 * 1.15)
        assert pid_endurant.Kp_VO2 == pytest.approx(0.008 * 0.90)

        # Endurance zone: endurant should have higher Kp
        assert pid_explosif.Kp_endurance == pytest.approx(0.008 * 0.95)
        assert pid_endurant.Kp_endurance == pytest.approx(0.008 * 1.10)


class TestIntervalsAPIIntegration:
    """Integration tests for Intervals.icu API + biomechanics."""

    def test_workflow_extract_metrics_to_recommendation(self):
        """Test workflow: Extract metrics → Get cadence recommendation."""
        # Mock recent activities from Intervals.icu
        activities = [
            {
                "average_cadence": 85,
                "moving_time": 3600,
                "icu_intensity": 88,
                "icu_training_load": 60,
            },
            {
                "average_cadence": 87,
                "moving_time": 2700,
                "icu_intensity": 90,
                "icu_training_load": 50,
            },
            {
                "average_cadence": 90,
                "moving_time": 5400,
                "icu_intensity": 70,
                "icu_training_load": 80,
            },
        ]

        # Step 1: Extract metrics
        metrics = extract_biomechanical_metrics(activities)

        assert metrics["activity_count"] == 3
        assert 85 <= metrics["avg_cadence"] <= 90
        assert 0.70 <= metrics["avg_intensity"] <= 0.90

        # Step 2: Get recommendation for next cycle (Sweet-Spot)
        recommendation = get_cadence_recommendation_from_activities(
            activities=activities,
            next_cycle_zone_ftp=0.90,  # Sweet-Spot
            next_cycle_duration_min=60,
            profil_fibres="mixte",
        )

        assert recommendation["cadence_optimale"] == 93  # Sweet-Spot mixte
        assert "cadence_actuelle" in recommendation
        assert "correction_necessaire" in recommendation
        assert recommendation["recent_metrics"] == metrics

    def test_workflow_with_energy_cost_calculation(self):
        """Test workflow: Activity → Metrics → CE calculation."""
        activity = {
            "icu_average_watts": 250,
            "average_cadence": 90,
            "moving_time": 3600,
            "distance": 30000,  # 30 km
        }

        # Calculate CE from activity
        ce = calculer_cout_energetique_from_activity(activity, poids_kg=70.0)

        assert ce is not None
        assert ce["energie_totale_kj"] == 900.0  # 250W × 3600s / 1000
        assert ce["efficience_mecanique"] == 21.0  # Optimal cadence
        assert ce["distance_reelle_km"] == 30.0
        assert ce["cout_km_reel_kj"] == 30.0  # 900 / 30

    def test_workflow_multiple_activities_trend_analysis(self):
        """Test analyzing cadence trends across multiple activities."""
        # Simulated 4-week training block
        activities_week1 = [
            {
                "average_cadence": 82,
                "moving_time": 3600,
                "icu_intensity": 88,
                "icu_training_load": 50,
            },
            {
                "average_cadence": 80,
                "moving_time": 3600,
                "icu_intensity": 90,
                "icu_training_load": 55,
            },
        ]
        activities_week2 = [
            {
                "average_cadence": 85,
                "moving_time": 3600,
                "icu_intensity": 88,
                "icu_training_load": 50,
            },
            {
                "average_cadence": 83,
                "moving_time": 3600,
                "icu_intensity": 90,
                "icu_training_load": 55,
            },
        ]
        activities_week3 = [
            {
                "average_cadence": 88,
                "moving_time": 3600,
                "icu_intensity": 88,
                "icu_training_load": 50,
            },
            {
                "average_cadence": 87,
                "moving_time": 3600,
                "icu_intensity": 90,
                "icu_training_load": 55,
            },
        ]
        activities_week4 = [
            {
                "average_cadence": 91,
                "moving_time": 3600,
                "icu_intensity": 88,
                "icu_training_load": 50,
            },
            {
                "average_cadence": 90,
                "moving_time": 3600,
                "icu_intensity": 90,
                "icu_training_load": 55,
            },
        ]

        # Extract metrics for each week
        metrics_w1 = extract_biomechanical_metrics(activities_week1)
        metrics_w2 = extract_biomechanical_metrics(activities_week2)
        metrics_w3 = extract_biomechanical_metrics(activities_week3)
        metrics_w4 = extract_biomechanical_metrics(activities_week4)

        # Verify progression trend
        assert metrics_w1["avg_cadence"] < metrics_w2["avg_cadence"]
        assert metrics_w2["avg_cadence"] < metrics_w3["avg_cadence"]
        assert metrics_w3["avg_cadence"] < metrics_w4["avg_cadence"]

        # Week 4: Close to optimal for Sweet-Spot
        recommendation_w4 = get_cadence_recommendation_from_activities(
            activities_week4, 0.90, 60, "mixte"
        )
        assert recommendation_w4["correction_necessaire"] is False  # Within ±5 rpm


class TestAthleteProfileIntegration:
    """Integration tests for AthleteProfile + biomechanics."""

    def test_athlete_profile_with_cadence_recommendation(self):
        """Test using AthleteProfile fiber profile for recommendations."""
        # Explosive athlete profile
        profile_explosif = AthleteProfile(
            age=28,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=320,
            weight=68.0,
            profil_fibres="explosif",
            cadence_offset=5,  # Prefers 5 rpm higher
        )

        # Calculate optimal cadence for VO2 workout
        cadence_opt = calculer_cadence_optimale(
            zone_ftp=1.10,
            duree_minutes=45,
            profil_fibres=profile_explosif.profil_fibres,
        )

        # Optimal cadence for explosif at VO2: 103 + 10 = 113 rpm
        assert cadence_opt["cadence_cible"] == 113

        # Apply athlete's personal offset
        cadence_with_offset = cadence_opt["cadence_cible"] + profile_explosif.cadence_offset
        assert cadence_with_offset == 118  # 113 + 5

    def test_athlete_profile_with_pid_enhanced(self):
        """Test using AthleteProfile with PIDGrappeEnhanced."""
        # Endurance athlete profile
        profile = AthleteProfile(
            age=42,
            category="master",
            recovery_capacity="exceptional",
            sleep_dependent=True,
            ftp=250,
            weight=73.0,
            profil_fibres="endurant",
            cadence_offset=-3,  # Prefers 3 rpm lower
        )

        # Create PID controller with athlete profile
        base_controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)
        pid_enhanced = PIDGrappeEnhanced(
            controller=base_controller, profil_fibres=profile.profil_fibres
        )

        # Calculate recommendation for endurance ride
        result = pid_enhanced.calculer_commande(
            measured_ftp=profile.ftp,
            cycle_duration_weeks=6,
            zone_intensite=0.68,
            cadence_reelle=77,  # Using athlete's preferred lower cadence
            duree_minutes=120,
        )

        # Verify endurant profile adjustments
        assert result["cadence_cible"] == 75  # 85 - 5 endurant - 5 duration

        # Apply personal offset
        cadence_personnalisee = result["cadence_cible"] + profile.cadence_offset
        assert cadence_personnalisee == 72  # 75 - 3


class TestFullWorkflowIntegration:
    """End-to-end integration tests for complete workflows."""

    def test_complete_workflow_cycle_planning(self):
        """Test complete workflow: Profile → Activities → Recommendation → PID."""
        # Step 1: Athlete profile
        profile = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="good",
            sleep_dependent=False,
            ftp=280,
            weight=70.0,
            profil_fibres="mixte",
            cadence_offset=0,
        )

        # Step 2: Recent activities from Intervals.icu
        activities = [
            {
                "icu_average_watts": 240,
                "average_cadence": 88,
                "moving_time": 3600,
                "icu_intensity": 85,
                "icu_training_load": 55,
            },
            {
                "icu_average_watts": 250,
                "average_cadence": 90,
                "moving_time": 3600,
                "icu_intensity": 88,
                "icu_training_load": 60,
            },
        ]

        # Step 3: Extract metrics
        metrics = extract_biomechanical_metrics(activities)
        assert metrics["avg_cadence"] == 89  # Weighted average

        # Step 4: Get cadence recommendation for next cycle
        recommendation = get_cadence_recommendation_from_activities(
            activities=activities,
            next_cycle_zone_ftp=0.90,  # Sweet-Spot
            next_cycle_duration_min=60,
            profil_fibres=profile.profil_fibres,
        )

        assert recommendation["cadence_optimale"] == 93
        assert recommendation["cadence_actuelle"] == 89
        assert recommendation["correction_necessaire"] is False  # Within ±5 rpm

        # Step 5: PID recommendation with biomechanics
        base_controller = DiscretePIDController(
            kp=0.008, ki=0.001, kd=0.12, setpoint=300  # Target progression
        )
        pid_enhanced = PIDGrappeEnhanced(
            controller=base_controller, profil_fibres=profile.profil_fibres
        )

        result = pid_enhanced.calculer_commande(
            measured_ftp=profile.ftp,
            cycle_duration_weeks=6,
            zone_intensite=0.90,
            cadence_reelle=metrics["avg_cadence"],
            duree_minutes=60,
        )

        # Step 6: Verify complete result
        assert "TSS_recommande" in result
        assert result["cadence_cible"] == 93
        assert result["ajustement_biomecanique"] == 1.0  # Good cadence
        assert "correction_base" in result

    def test_complete_workflow_with_energy_cost(self):
        """Test workflow with CE calculation for efficiency tracking."""
        # Athlete completes Sweet-Spot workout
        activity = {
            "icu_average_watts": 250,
            "average_cadence": 93,  # Optimal for Sweet-Spot
            "moving_time": 3600,
            "distance": 30000,
            "icu_intensity": 90,
            "icu_training_load": 65,
        }

        profile = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=280,
            weight=70.0,
            profil_fibres="mixte",
        )

        # Calculate CE
        ce = calculer_cout_energetique_from_activity(activity, poids_kg=profile.weight)

        assert ce is not None
        assert ce["energie_totale_kj"] == 900.0
        assert ce["efficience_mecanique"] == 21.0  # Optimal cadence (93 rpm)
        assert ce["cout_km_reel_kj"] == 30.0

        # Compare with suboptimal cadence scenario
        activity_suboptimal = {**activity, "average_cadence": 75}  # Too low
        ce_suboptimal = calculer_cout_energetique_from_activity(
            activity_suboptimal, poids_kg=profile.weight
        )

        # Suboptimal cadence should have lower efficiency
        assert ce_suboptimal["efficience_mecanique"] < ce["efficience_mecanique"]

    def test_multi_cycle_progression_tracking(self):
        """Test tracking progression across multiple training cycles."""
        profile = AthleteProfile(
            age=35,
            category="senior",
            recovery_capacity="normal",
            sleep_dependent=False,
            ftp=220,
            weight=70.0,
            profil_fibres="mixte",
        )

        # Initialize PID controller
        base_controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)
        pid_enhanced = PIDGrappeEnhanced(
            controller=base_controller, profil_fibres=profile.profil_fibres
        )

        # Simulate 3 training cycles with progression
        cycle_results = []

        # Cycle 1: FTP 220W, cadence 85 rpm
        result1 = pid_enhanced.calculer_commande(
            measured_ftp=220,
            cycle_duration_weeks=6,
            zone_intensite=0.88,
            cadence_reelle=85,
            duree_minutes=60,
        )
        cycle_results.append(result1)

        # Cycle 2: FTP 235W, cadence 88 rpm (improved)
        result2 = pid_enhanced.calculer_commande(
            measured_ftp=235,
            cycle_duration_weeks=6,
            zone_intensite=0.88,
            cadence_reelle=88,
            duree_minutes=60,
        )
        cycle_results.append(result2)

        # Cycle 3: FTP 248W, cadence 90 rpm (closer to optimal)
        result3 = pid_enhanced.calculer_commande(
            measured_ftp=248,
            cycle_duration_weeks=6,
            zone_intensite=0.88,
            cadence_reelle=90,
            duree_minutes=60,
        )
        cycle_results.append(result3)

        # Verify progression
        assert result2["correction_base"]["error"] < result1["correction_base"]["error"]
        assert result3["correction_base"]["error"] < result2["correction_base"]["error"]

        # Verify cadence improvements
        assert result1["ajustement_biomecanique"] == 1.0  # 85 rpm OK for Tempo
        assert result2["ajustement_biomecanique"] == 1.0  # 88 rpm OK
        assert result3["ajustement_biomecanique"] == 1.0  # 90 rpm optimal
