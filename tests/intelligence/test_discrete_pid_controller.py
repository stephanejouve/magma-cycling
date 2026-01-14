"""
Tests for Discrete PID Controller module.

Tests discrete PID control logic adapted to sporadic FTP measurements,
cycle-level corrections, and enhanced validation with complementary variables.
"""

import pytest

from cyclisme_training_logs.intelligence.discrete_pid_controller import (
    DiscretePIDController,
    compute_discrete_pid_gains_from_intelligence,
)
from cyclisme_training_logs.intelligence.training_intelligence import (
    AnalysisLevel,
    ConfidenceLevel,
    TrainingIntelligence,
)

# ============================================================================
# BASIC DISCRETE PID TESTS
# ============================================================================


def test_discrete_pid_initialization():
    """Test DiscretePIDController initialization with valid parameters."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260, dead_band=3.0)

    assert controller.kp == 0.008
    assert controller.ki == 0.001
    assert controller.kd == 0.12
    assert controller.setpoint == 260
    assert controller.dead_band == 3.0
    assert controller.state.integral == 0.0
    assert controller.state.cycle_count == 0


def test_discrete_pid_invalid_gains():
    """Test DiscretePIDController raises on invalid gains."""
    with pytest.raises(ValueError, match="gains must be non-negative"):
        DiscretePIDController(kp=-0.008, ki=0.001, kd=0.12, setpoint=260)

    with pytest.raises(ValueError, match="Setpoint must be positive"):
        DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=0)

    with pytest.raises(ValueError, match="Dead band must be non-negative"):
        DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260, dead_band=-1.0)


def test_discrete_pid_positive_error():
    """Test discrete PID correction with FTP below target."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # Test FTP 54W below target after 6-week cycle
    correction = controller.compute_cycle_correction(measured_ftp=206, cycle_duration_weeks=6)

    # Verify error
    assert correction["error"] == 54.0
    assert correction["cycle_duration"] == 6

    # Verify positive correction (need to increase)
    assert correction["p_term"] > 0  # Proportional positive
    assert correction["i_term"] > 0  # Integral positive
    assert correction["output"] > 0  # Total positive
    assert correction["tss_per_week"] > 0  # Should increase TSS


def test_discrete_pid_negative_error():
    """Test discrete PID correction with FTP above target."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # FTP 15W above target
    correction = controller.compute_cycle_correction(measured_ftp=275, cycle_duration_weeks=6)

    # Verify error
    assert correction["error"] == -15.0

    # Verify negative correction (need to decrease)
    assert correction["p_term"] < 0
    assert correction["output"] < 0
    assert correction["tss_per_week"] < 0  # Should decrease TSS


def test_discrete_pid_dead_band():
    """Test dead-band ignores small FTP variations."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260, dead_band=3.0)

    # FTP within dead-band (258W, error=2W < 3W dead-band)
    correction = controller.compute_cycle_correction(measured_ftp=258, cycle_duration_weeks=6)

    # Error detected but zeroed by dead-band
    assert correction["error"] == 2.0
    assert correction["error_with_deadband"] == 0.0
    assert correction["p_term"] == 0.0  # No proportional correction
    assert abs(correction["tss_per_week"]) < 2  # Minimal correction


def test_discrete_pid_integral_accumulation():
    """Test integral accumulates over cycles."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # Cycle 1: Error 54W over 6 weeks
    correction1 = controller.compute_cycle_correction(measured_ftp=206, cycle_duration_weeks=6)
    integral1 = controller.state.integral

    assert integral1 > 0  # Integral accumulating
    assert correction1["i_term"] > 0

    # Cycle 2: Error 30W over 6 weeks (smaller error, should accumulate before saturation)
    correction2 = controller.compute_cycle_correction(measured_ftp=230, cycle_duration_weeks=6)
    integral2 = controller.state.integral

    # Integral should continue accumulating (or be saturated at 200)
    assert integral2 >= integral1  # Can be equal if saturated
    assert correction2["i_term"] >= 0


def test_discrete_pid_anti_windup():
    """Test anti-windup limits integral accumulation."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # Simulate 10 cycles with constant large error
    for _ in range(10):
        controller.compute_cycle_correction(measured_ftp=200, cycle_duration_weeks=6)

    # Integral should be saturated at ±200W·cycles
    assert abs(controller.state.integral) <= 200.0


def test_discrete_pid_derivative_term():
    """Test derivative term captures trend between FTP tests."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # Cycle 1: Error 54W
    correction1 = controller.compute_cycle_correction(measured_ftp=206, cycle_duration_weeks=6)
    assert correction1["d_term"] == 0.0  # No previous error (cycle_count=0)

    # Cycle 2: Error decreased to 48W (improving)
    correction2 = controller.compute_cycle_correction(measured_ftp=212, cycle_duration_weeks=6)

    # Derivative should be negative (error decreasing = good trend)
    assert correction2["d_term"] < 0


def test_discrete_pid_output_saturation():
    """Test TSS adjustment saturates at ±30 TSS/week."""
    controller = DiscretePIDController(kp=0.1, ki=0.05, kd=0.5, setpoint=260)  # High gains

    # Extreme error (100W below)
    correction = controller.compute_cycle_correction(measured_ftp=160, cycle_duration_weeks=6)

    # TSS adjustment should be capped at ±30
    assert abs(correction["tss_per_week"]) <= 30


def test_discrete_pid_reset():
    """Test reset clears internal state."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # Build up some state
    for _ in range(3):
        controller.compute_cycle_correction(measured_ftp=206, cycle_duration_weeks=6)

    assert controller.state.integral != 0.0
    assert controller.state.prev_error != 0.0
    assert controller.state.cycle_count == 3

    # Reset
    controller.reset()

    assert controller.state.integral == 0.0
    assert controller.state.prev_error == 0.0
    assert controller.state.prev_ftp is None
    assert controller.state.cycle_count == 0


# ============================================================================
# RECOMMENDATION TESTS
# ============================================================================


def test_discrete_pid_recommendation_increase():
    """Test recommendation for TSS increase."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    correction = controller.compute_cycle_correction(measured_ftp=206, cycle_duration_weeks=6)
    recommendation = correction["recommendation"]

    assert "Augmenter TSS" in recommendation
    assert "cycle complet" in recommendation


def test_discrete_pid_recommendation_decrease():
    """Test recommendation for TSS decrease."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # Very high FTP (50W above target), need to reduce load
    correction = controller.compute_cycle_correction(measured_ftp=310, cycle_duration_weeks=6)
    recommendation = correction["recommendation"]

    assert "Réduire TSS" in recommendation


def test_discrete_pid_recommendation_maintain():
    """Test recommendation when FTP near target (within dead-band)."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # FTP within dead-band
    correction = controller.compute_cycle_correction(measured_ftp=258, cycle_duration_weeks=6)
    recommendation = correction["recommendation"]

    assert "Maintien" in recommendation


# ============================================================================
# CONVERGENCE SIMULATION TESTS
# ============================================================================


def test_discrete_pid_convergence_5_cycles():
    """Test PID convergence over 5 cycles (30 weeks)."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    current_ftp = 200.0
    errors = []

    # Simulate 5 cycles
    for _cycle in range(5):
        correction = controller.compute_cycle_correction(
            measured_ftp=current_ftp, cycle_duration_weeks=6
        )
        errors.append(correction["error"])

        # Simulate FTP progression (realistic training response)
        # Assume training effect improves FTP
        current_ftp += correction["output"] * 3.0  # Conservative factor

    # Validations
    # 1. Error should decrease (convergence happening)
    assert errors[-1] < errors[0], "Error should decrease over cycles"

    # 2. FTP should improve significantly
    assert current_ftp > 200.0, f"FTP should improve from 200W, got {current_ftp}W"

    # 3. Realistic expectation: At least 9W improvement over 5 cycles (conservative gains)
    assert current_ftp >= 209.0, "FTP should improve at least 9W after 5 cycles"


def test_discrete_pid_stability_near_target():
    """Test PID stability when FTP near target."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # Start near target
    ftp_values = [258, 262, 259, 261, 260, 258]
    outputs = []

    for ftp in ftp_values:
        correction = controller.compute_cycle_correction(measured_ftp=ftp, cycle_duration_weeks=6)
        outputs.append(correction["tss_per_week"])

    # Validations
    # 1. Corrections should be small (within dead-band or minimal)
    for output in outputs:
        assert abs(output) <= 10, f"Correction too large near target: {output} TSS"

    # 2. Average correction near zero (no systematic bias)
    mean_correction = sum(outputs) / len(outputs)
    assert abs(mean_correction) < 3.0, f"Systematic bias: {mean_correction}"


# ============================================================================
# GAINS COMPUTATION TESTS
# ============================================================================


def test_compute_discrete_gains_empty_intelligence():
    """Test gain calculation with empty intelligence."""
    intelligence = TrainingIntelligence()

    gains = compute_discrete_pid_gains_from_intelligence(intelligence)

    # Should return conservative default gains (discrete)
    assert gains["kp"] == 0.005
    assert gains["ki"] == 0.0005
    assert gains["kd"] == 0.08


def test_compute_discrete_gains_validated_learnings():
    """Test gain calculation with validated learnings."""
    intelligence = TrainingIntelligence()

    # Add 10 validated learnings
    for i in range(10):
        learning = intelligence.add_learning(
            category=f"test_{i}",
            description=f"Test learning {i}",
            evidence=[f"evidence_{i}"],
            level=AnalysisLevel.WEEKLY,
        )
        learning.confidence = ConfidenceLevel.VALIDATED

    gains = compute_discrete_pid_gains_from_intelligence(intelligence)

    # Kp should be higher with validated learnings (but capped at 0.010)
    assert 0.005 < gains["kp"] <= 0.010
    assert gains["ki"] >= 0.0005
    assert gains["kd"] >= 0.08


def test_compute_discrete_gains_high_evidence():
    """Test Ki increases with cumulative evidence (discrete version)."""
    intelligence = TrainingIntelligence()

    # Add learnings with many evidence items
    for i in range(10):
        evidence = [f"evidence_{i}_{j}" for j in range(6)]  # 6 each = 60 total
        intelligence.add_learning(
            category=f"test_{i}",
            description=f"Test {i}",
            evidence=evidence,
            level=AnalysisLevel.DAILY,
        )

    gains = compute_discrete_pid_gains_from_intelligence(intelligence)

    # Total evidence > 50, so Ki should be 0.002 (vs 0.003 continu)
    assert gains["ki"] == 0.002


def test_compute_discrete_gains_patterns():
    """Test Kd increases with frequent patterns (discrete version)."""
    from datetime import date

    intelligence = TrainingIntelligence()

    # Add 5 frequent patterns
    for i in range(5):
        pattern = intelligence.identify_pattern(
            name=f"pattern_{i}",
            trigger_conditions={"condition": f"value_{i}"},
            observed_outcome=f"outcome_{i}",
            observation_date=date.today(),
        )
        pattern.frequency = 15  # Frequent pattern

    gains = compute_discrete_pid_gains_from_intelligence(intelligence)

    # Kd should be 0.15 (vs 0.25 continu)
    assert gains["kd"] == 0.15


# ============================================================================
# STATE MANAGEMENT TESTS
# ============================================================================


def test_discrete_pid_get_state_info():
    """Test get_state_info returns correct state."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    # Initial state
    state = controller.get_state_info()
    assert state["integral"] == 0.0
    assert state["cycle_count"] == 0
    assert state["prev_ftp"] is None

    # After one cycle
    controller.compute_cycle_correction(measured_ftp=206, cycle_duration_weeks=6)
    state = controller.get_state_info()

    assert state["integral"] > 0.0
    assert state["cycle_count"] == 1
    assert state["prev_ftp"] == 206
    assert state["last_test_date"] is not None


def test_discrete_pid_cycle_count_increments():
    """Test cycle count increments correctly."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    for i in range(5):
        controller.compute_cycle_correction(measured_ftp=206, cycle_duration_weeks=6)
        assert controller.state.cycle_count == i + 1


def test_discrete_pid_invalid_cycle_duration():
    """Test compute_cycle_correction raises on invalid cycle duration."""
    controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

    with pytest.raises(ValueError, match="Cycle duration must be positive"):
        controller.compute_cycle_correction(measured_ftp=206, cycle_duration_weeks=0)

    with pytest.raises(ValueError, match="Cycle duration must be positive"):
        controller.compute_cycle_correction(measured_ftp=206, cycle_duration_weeks=-6)


# ============================================================================
# TRAINING INTELLIGENCE INTEGRATION TESTS
# ============================================================================


def test_training_intelligence_get_discrete_pid_correction():
    """Test TrainingIntelligence.get_discrete_pid_correction() integration."""
    intelligence = TrainingIntelligence()

    # Call discrete PID correction
    result = intelligence.get_discrete_pid_correction(
        measured_ftp=206, target_ftp=260, cycle_duration_weeks=6
    )

    # Validate result structure
    assert "correction" in result
    assert "recommendation" in result
    assert "gains" in result

    # Validate correction keys
    correction = result["correction"]
    assert "error" in correction
    assert "tss_per_week" in correction
    assert "recommendation" in correction

    # Validate gains
    gains = result["gains"]
    assert "kp" in gains
    assert "ki" in gains
    assert "kd" in gains

    # Validate conservative gains (default with no learnings)
    assert gains["kp"] == 0.005
    assert gains["ki"] == 0.0005
    assert gains["kd"] == 0.08


def test_training_intelligence_discrete_pid_with_learnings():
    """Test discrete PID gains adapt with learnings."""
    intelligence = TrainingIntelligence()

    # Add 10 validated learnings
    for i in range(10):
        learning = intelligence.add_learning(
            category=f"test_{i}",
            description=f"Test learning {i}",
            evidence=[f"evidence_{i}"],
            level=AnalysisLevel.WEEKLY,
        )
        learning.confidence = ConfidenceLevel.VALIDATED

    # Call discrete PID correction
    result = intelligence.get_discrete_pid_correction(
        measured_ftp=206, target_ftp=260, cycle_duration_weeks=6
    )

    # Gains should be higher with validated learnings
    gains = result["gains"]
    assert gains["kp"] > 0.005  # Higher than default
    assert gains["ki"] >= 0.0005
    assert gains["kd"] >= 0.08


def test_training_intelligence_discrete_pid_realistic_scenario():
    """Test discrete PID in realistic training scenario."""
    intelligence = TrainingIntelligence()

    # Add some learnings (simulating mature intelligence)
    for i in range(5):
        intelligence.add_learning(
            category=f"training_{i}",
            description=f"Training insight {i}",
            evidence=[f"workout_{i}_a", f"workout_{i}_b", f"workout_{i}_c"],
            level=AnalysisLevel.WEEKLY,
        )

    # Test FTP progression over 3 cycles
    current_ftp = 200.0
    target_ftp = 260.0

    for _cycle in range(3):
        result = intelligence.get_discrete_pid_correction(
            measured_ftp=current_ftp, target_ftp=target_ftp, cycle_duration_weeks=6
        )

        correction = result["correction"]

        # Error should be positive (below target)
        assert correction["error"] > 0

        # TSS adjustment should be positive
        assert correction["tss_per_week"] > 0

        # Simulate FTP progression
        current_ftp += correction["output"] * 3.0  # Conservative training response

    # FTP should have improved (conservative gains with 5 learnings)
    assert current_ftp > 200.0
    assert current_ftp >= 203.0  # At least 3W improvement over 3 cycles
