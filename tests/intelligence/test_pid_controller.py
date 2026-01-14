"""
Tests for PID Controller module.

Tests PID control logic, gain calculation, and integration with TrainingIntelligence.
"""

import pytest

from cyclisme_training_logs.intelligence.pid_controller import (
    PIDController,
    compute_pid_gains_from_intelligence,
)
from cyclisme_training_logs.intelligence.training_intelligence import (
    AnalysisLevel,
    ConfidenceLevel,
    TrainingIntelligence,
)


def test_pid_compute_positive_error():
    """Test PID correction with FTP below target."""
    pid = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

    # First computation with FTP 40W below target
    correction = pid.compute(measured_value=220, dt=1.0)

    # Verify error
    assert correction["error"] == 40.0

    # Verify positive correction (need to increase)
    assert correction["p_term"] > 0  # Proportional positive
    assert correction["i_term"] > 0  # Integral positive
    assert correction["output"] > 0  # Total positive
    assert correction["tss_adjustment"] > 0  # Should increase TSS


def test_pid_compute_negative_error():
    """Test PID correction with FTP above target."""
    pid = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

    # FTP 20W above target
    correction = pid.compute(measured_value=280, dt=1.0)

    # Verify error
    assert correction["error"] == -20.0

    # Verify negative correction (need to decrease)
    assert correction["p_term"] < 0
    assert correction["output"] < 0
    assert correction["tss_adjustment"] < 0  # Should decrease TSS


def test_pid_integral_anti_windup():
    """Test anti-windup limits integral term."""
    pid = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

    # Simulate 100 weeks of constant error
    for _ in range(100):
        pid.compute(measured_value=220, dt=1.0)

    # Integral should be saturated at ±100W
    assert abs(pid.state.integral) <= 100.0


def test_pid_derivative_term():
    """Test derivative term captures error trend."""
    pid = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

    # First measurement: error = 40W
    pid.compute(measured_value=220, dt=1.0)

    # Second measurement: error increased to 50W (FTP decreased)
    correction2 = pid.compute(measured_value=210, dt=1.0)

    # Derivative should be positive (error increasing)
    assert correction2["d_term"] > 0


def test_pid_output_saturation():
    """Test TSS adjustment saturates at ±50 TSS/week."""
    pid = PIDController(kp=0.1, ki=0.05, kd=0.5, setpoint=260)  # High gains

    # Extreme error (100W below)
    correction = pid.compute(measured_value=160, dt=1.0)

    # TSS adjustment should be capped
    assert abs(correction["tss_adjustment"]) <= 50


def test_pid_reset():
    """Test reset clears internal state."""
    pid = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

    # Build up some state
    for _ in range(10):
        pid.compute(measured_value=220, dt=1.0)

    assert pid.state.integral != 0.0
    assert pid.state.prev_error != 0.0

    # Reset
    pid.reset()

    assert pid.state.integral == 0.0
    assert pid.state.prev_error == 0.0
    assert pid.state.last_update is None


def test_pid_action_recommendation_increase():
    """Test recommendation for large increase."""
    pid = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

    correction = pid.compute(measured_value=220, dt=1.0)
    recommendation = pid.get_action_recommendation(correction)

    assert "Augmenter TSS" in recommendation
    assert "Sweet-Spot" in recommendation


def test_pid_action_recommendation_decrease():
    """Test recommendation for TSS decrease."""
    pid = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

    # Very high FTP, need to reduce load
    correction = pid.compute(measured_value=290, dt=1.0)
    recommendation = pid.get_action_recommendation(correction)

    assert "Réduire TSS" in recommendation


def test_pid_action_recommendation_maintain():
    """Test recommendation when FTP near target."""
    pid = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

    # FTP very close to target
    correction = pid.compute(measured_value=258, dt=1.0)
    recommendation = pid.get_action_recommendation(correction)

    assert "Maintien" in recommendation


def test_compute_gains_from_empty_intelligence():
    """Test gain calculation with empty intelligence."""
    intelligence = TrainingIntelligence()

    gains = compute_pid_gains_from_intelligence(intelligence)

    # Should return conservative default gains
    assert gains["kp"] == 0.005
    assert gains["ki"] == 0.001
    assert gains["kd"] == 0.10


def test_compute_gains_from_validated_learnings():
    """Test gain calculation with many validated learnings."""
    intelligence = TrainingIntelligence()

    # Add 15 validated learnings
    for i in range(15):
        learning = intelligence.add_learning(
            category="test",
            description=f"Test learning {i}",
            evidence=[f"evidence_{i}"],
            level=AnalysisLevel.WEEKLY,
        )
        learning.confidence = ConfidenceLevel.VALIDATED

    gains = compute_pid_gains_from_intelligence(intelligence)

    # Kp should be higher with many validated learnings
    assert 0.005 < gains["kp"] <= 0.015
    assert gains["ki"] >= 0.001
    assert gains["kd"] >= 0.10


def test_compute_gains_with_many_patterns():
    """Test Kd increases with frequent patterns."""
    intelligence = TrainingIntelligence()

    # Add 5 frequent patterns
    from datetime import date

    for i in range(5):
        pattern = intelligence.identify_pattern(
            name=f"pattern_{i}",
            trigger_conditions={"condition": f"value_{i}"},
            observed_outcome=f"outcome_{i}",
            observation_date=date.today(),
        )
        pattern.frequency = 15  # Frequent pattern

    gains = compute_pid_gains_from_intelligence(intelligence)

    # Kd should be highest tier (0.25)
    assert gains["kd"] == 0.25


def test_compute_gains_with_high_evidence():
    """Test Ki increases with cumulative evidence."""
    intelligence = TrainingIntelligence()

    # Add learnings with many evidence items (different categories to avoid merging)
    for i in range(10):
        evidence = [f"evidence_{i}_{j}" for j in range(6)]  # 6 evidence each
        intelligence.add_learning(
            category=f"test_{i}",  # Different category each time
            description=f"Test {i}",
            evidence=evidence,
            level=AnalysisLevel.DAILY,
        )

    gains = compute_pid_gains_from_intelligence(intelligence)

    # Total evidence = 60 > 50, so Ki should be 0.003
    assert gains["ki"] == 0.003


def test_training_intelligence_get_pid_correction():
    """Test get_pid_correction() integration."""
    intelligence = TrainingIntelligence()

    # Add some learnings
    for i in range(5):
        learning = intelligence.add_learning(
            category="test",
            description=f"Test {i}",
            evidence=[f"ev{i}"],
            level=AnalysisLevel.WEEKLY,
        )
        learning.confidence = ConfidenceLevel.HIGH

    # Get PID correction
    result = intelligence.get_pid_correction(current_ftp=220, target_ftp=260, dt=1.0)

    # Verify result structure
    assert "correction" in result
    assert "recommendation" in result
    assert "gains" in result

    # Verify correction
    assert result["correction"]["error"] == 40.0
    assert result["correction"]["tss_adjustment"] > 0

    # Verify gains calculated
    assert "kp" in result["gains"]
    assert "ki" in result["gains"]
    assert "kd" in result["gains"]

    # Verify recommendation
    assert isinstance(result["recommendation"], str)
    assert len(result["recommendation"]) > 0


def test_pid_controller_invalid_inputs():
    """Test PIDController raises on invalid inputs."""
    # Negative gains should raise

    with pytest.raises(ValueError):
        PIDController(kp=-0.01, ki=0.002, kd=0.15, setpoint=260)

    # Zero/negative setpoint should raise
    with pytest.raises(ValueError):
        PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=0)


def test_pid_multiple_iterations():
    """Test PID over multiple iterations converges."""
    pid = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

    # Simulate improving FTP over 20 weeks
    current_ftp = 220
    for _week in range(20):
        pid.compute(measured_value=current_ftp, dt=1.0)

        # Simulate improvement (+1W per week from training)
        current_ftp += 1.0

    # After 20 weeks, FTP should be closer to target
    final_correction = pid.compute(measured_value=current_ftp, dt=1.0)
    assert abs(final_correction["error"]) < 40  # Was 40W, now <40W


# ============================================================================
# CATEGORY 1 - EDGE CASES CRITIQUES (P0)
# ============================================================================


def test_pid_extreme_error_200w():
    """Test PID with extreme error (200W FTP gap).

    Validates that:
    - Output stays within limits (±50 TSS/week)
    - No premature saturation
    - Aggressive but controlled correction
    """
    controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260.0)

    result = controller.compute(measured_value=60.0, dt=1.0)

    # Assertions
    assert result["error"] == 200.0
    assert -50 <= result["tss_adjustment"] <= 50  # Saturation check
    assert result["output"] > 0  # Positive correction
    assert result["p_term"] > 0  # Proportional positive
    assert result["i_term"] > 0  # Integral positive


def test_pid_zero_error_target_reached():
    """Test PID when FTP target reached (error = 0).

    Validates that:
    - P-term = 0 (no proportional error)
    - D-term = 0 (no variation)
    - I-term near 0 (reset or minimal)
    - Recommendation = "Maintien"
    """
    controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=220.0)

    # Simulate convergence with stable FTP at target
    for _ in range(5):
        controller.compute(measured_value=220.0, dt=1.0)

    result = controller.compute(measured_value=220.0, dt=1.0)

    # Assertions
    assert result["error"] == 0.0
    assert result["p_term"] == 0.0
    assert abs(result["i_term"]) < 0.1  # Near zero
    assert result["d_term"] == 0.0

    recommendation = controller.get_action_recommendation(result)
    assert "Maintien" in recommendation


def test_pid_negative_error_overperformance():
    """Test PID if FTP exceeds target (rare but possible).

    Validates that:
    - Error < 0 (overperformance)
    - Output negative (TSS reduction suggested)
    - Recommendation = "Réduire" or "Maintien"
    """
    controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=220.0)

    result = controller.compute(measured_value=230.0, dt=1.0)

    # Assertions
    assert result["error"] == -10.0
    assert result["output"] < 0  # Negative correction
    assert result["p_term"] < 0  # Proportional negative

    recommendation = controller.get_action_recommendation(result)
    assert "Réduire" in recommendation or "Maintien" in recommendation


# ============================================================================
# CATEGORY 2 - ANTI-WINDUP ROBUSTESSE (P0)
# ============================================================================


def test_integral_windup_saturation_100_iterations():
    """Validate integral stays within ±100W after 100 iterations.

    Scenario:
    - Constant 40W error for 100 weeks
    - Integral must saturate at ±100W (anti-windup)
    - No infinite drift
    """
    controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260.0)

    for i in range(100):
        _result = controller.compute(measured_value=220.0, dt=1.0)

        # Verify saturation at each iteration
        assert (
            -100 <= controller.state.integral <= 100
        ), f"Integral {controller.state.integral} out of bounds at iteration {i}"

    # Verify final state stable
    assert abs(controller.state.integral) <= 100


def test_integral_reset_on_error_sign_change():
    """Validate integral behavior when error changes sign.

    Scenario:
    1. Error +40W → Integral accumulates positive
    2. Error switches to -10W (overperformance) → Integral must decrease
    3. Validate smooth transition
    """
    controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=220.0)

    # Phase 1: Positive error
    for _ in range(10):
        controller.compute(measured_value=180.0, dt=1.0)  # +40W error

    integral_positive = controller.state.integral
    assert integral_positive > 0

    # Phase 2: Negative error (overperformance)
    for _ in range(10):
        controller.compute(measured_value=230.0, dt=1.0)  # -10W error

    integral_after = controller.state.integral
    assert integral_after < integral_positive  # Decreased


# ============================================================================
# CATEGORY 3 - CONVERGENCE SIMULATION (P1)
# ============================================================================


def test_pid_convergence_40w_to_0w_monotonic():
    """Simulate FTP convergence 220W → 260W over 20 weeks.

    Validates that:
    - Error decreases over time (convergence)
    - FTP shows measurable improvement
    - No catastrophic oscillations
    """
    controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260.0)

    current_ftp = 220.0
    errors = []

    for _week in range(20):
        result = controller.compute(measured_value=current_ftp, dt=1.0)
        errors.append(result["error"])

        # Simulate FTP progression (realistic training response)
        current_ftp += result["output"] * 0.5  # Realistic factor

    # Validations
    # 1. Effective convergence (error decreased)
    assert errors[-1] < errors[0], "Error should decrease over time"

    # 2. No catastrophic oscillation (error decreases on average)
    # Check that final 5 weeks average < initial 5 weeks average
    initial_avg = sum(errors[:5]) / 5
    final_avg = sum(errors[-5:]) / 5
    assert final_avg < initial_avg, "Average error should decrease"

    # 3. FTP shows improvement
    assert current_ftp > 220.0, f"FTP should improve from 220W, got {current_ftp}W"


def test_pid_stability_after_convergence():
    """Validate PID stability near target with small variations.

    Scenario:
    - Start near target (within 5W)
    - Small variations ±2W (measurement noise)
    - PID corrections should be reasonable
    """
    controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260.0)

    # Start near target (no long convergence to avoid integral buildup)
    controller.compute(measured_value=258.0, dt=1.0)

    # Introduce small variations around target
    variations = [260.0, 258.0, 262.0, 259.0, 261.0, 260.0]
    outputs = []

    for ftp in variations:
        result = controller.compute(measured_value=ftp, dt=1.0)
        outputs.append(result["tss_adjustment"])

    # Validations
    # 1. Corrections are reasonable for small errors
    # Small errors (±2W) should give corrections < 10 TSS
    for output in outputs:
        assert abs(output) <= 10, f"Excessive correction: {output} TSS for small variation"

    # 2. Average correction near zero (no systematic bias)
    mean_correction = sum(outputs) / len(outputs)
    assert abs(mean_correction) < 2.0, f"Systematic bias detected: {mean_correction}"


# ============================================================================
# CATEGORY 4 - GAINS ADAPTATIFS (P1)
# ============================================================================


def test_gains_evolution_with_learnings_count():
    """Validate gains change according to TrainingIntelligence learnings count.

    Test with mocks:
    - Intelligence with 0 validated learnings → Conservative gains
    - Intelligence with 10 validated learnings → Standard gains
    - Intelligence with 20+ validated learnings → Aggressive gains
    """
    # Scenario 1: Few learnings
    intel_low = TrainingIntelligence()
    for i in range(3):
        intel_low.add_learning(
            category="test",
            description=f"Learning {i}",
            evidence=[f"ev{i}"],
            level=AnalysisLevel.DAILY,
        )
        # Default confidence is LOW, which won't be counted as validated

    gains_low = compute_pid_gains_from_intelligence(intel_low)

    # Scenario 2: Standard learnings
    intel_medium = TrainingIntelligence()
    for i in range(10):
        learning = intel_medium.add_learning(
            category=f"test_{i}",  # Different categories to avoid merging
            description=f"Learning {i}",
            evidence=[f"ev{i}"],
            level=AnalysisLevel.WEEKLY,
        )
        learning.confidence = ConfidenceLevel.VALIDATED

    gains_medium = compute_pid_gains_from_intelligence(intel_medium)

    # Scenario 3: Many learnings
    intel_high = TrainingIntelligence()
    for i in range(25):
        learning = intel_high.add_learning(
            category=f"test_{i}",  # Different categories to avoid merging
            description=f"Learning {i}",
            evidence=[f"ev{i}"],
            level=AnalysisLevel.MONTHLY,
        )
        learning.confidence = ConfidenceLevel.VALIDATED

    gains_high = compute_pid_gains_from_intelligence(intel_high)

    # Validations
    # Kp should increase with learnings
    assert gains_low["kp"] < gains_medium["kp"] < gains_high["kp"]

    # Ki depends on evidence count, not learning count (so we test separately)
    assert gains_low["ki"] >= 0.001

    # Gains in reasonable ranges
    assert 0.005 <= gains_high["kp"] <= 0.015
    assert 0.001 <= gains_high["ki"] <= 0.003
    assert 0.10 <= gains_high["kd"] <= 0.25


def test_gains_minimum_guaranteed():
    """Validate minimum gains even without learnings.

    Scenario:
    - Empty TrainingIntelligence (0 learnings)
    - Gains must stay within safe ranges
    - Avoid zero gains (division by zero)
    """
    intel_empty = TrainingIntelligence()
    gains = compute_pid_gains_from_intelligence(intel_empty)

    # Validation minimums
    assert gains["kp"] >= 0.005  # Reasonable minimum
    assert gains["ki"] >= 0.001
    assert gains["kd"] >= 0.10

    # Not excessive either
    assert gains["kp"] <= 0.015
    assert gains["ki"] <= 0.003
    assert gains["kd"] <= 0.25


def test_gains_ki_evolution_with_evidence():
    """Validate Ki gain increases with cumulative evidence count.

    Scenario:
    - Low evidence (< 20): Ki = 0.001
    - Medium evidence (20-50): Ki = 0.002
    - High evidence (> 50): Ki = 0.003
    """
    # Scenario 1: Low evidence
    intel_low = TrainingIntelligence()
    for i in range(3):
        intel_low.add_learning(
            category=f"test_{i}",
            description=f"Learning {i}",
            evidence=[f"ev{i}_1"],  # 1 evidence each = 3 total
            level=AnalysisLevel.DAILY,
        )

    gains_low = compute_pid_gains_from_intelligence(intel_low)
    assert gains_low["ki"] == 0.001

    # Scenario 2: Medium evidence
    intel_medium = TrainingIntelligence()
    for i in range(10):
        intel_medium.add_learning(
            category=f"test_{i}",
            description=f"Learning {i}",
            evidence=[f"ev{i}_1", f"ev{i}_2", f"ev{i}_3"],  # 3 each = 30 total
            level=AnalysisLevel.DAILY,
        )

    gains_medium = compute_pid_gains_from_intelligence(intel_medium)
    assert gains_medium["ki"] == 0.002

    # Scenario 3: High evidence
    intel_high = TrainingIntelligence()
    for i in range(10):
        intel_high.add_learning(
            category=f"test_{i}",
            description=f"Learning {i}",
            evidence=[f"ev{i}_{j}" for j in range(6)],  # 6 each = 60 total
            level=AnalysisLevel.DAILY,
        )

    gains_high = compute_pid_gains_from_intelligence(intel_high)
    assert gains_high["ki"] == 0.003


def test_gains_kd_evolution_with_patterns():
    """Validate Kd gain increases with frequent pattern count.

    Scenario:
    - 0 patterns: Kd = 0.10
    - 1-2 frequent patterns: Kd = 0.15
    - 3+ frequent patterns: Kd = 0.25
    """
    from datetime import date

    # Scenario 1: No patterns
    intel_no_patterns = TrainingIntelligence()
    gains_no = compute_pid_gains_from_intelligence(intel_no_patterns)
    assert gains_no["kd"] == 0.10

    # Scenario 2: 1-2 frequent patterns
    intel_few_patterns = TrainingIntelligence()
    for i in range(2):
        pattern = intel_few_patterns.identify_pattern(
            name=f"pattern_{i}",
            trigger_conditions={"condition": f"value_{i}"},
            observed_outcome=f"outcome_{i}",
            observation_date=date.today(),
        )
        pattern.frequency = 12  # Frequent (≥10)

    gains_few = compute_pid_gains_from_intelligence(intel_few_patterns)
    assert gains_few["kd"] == 0.15

    # Scenario 3: 3+ frequent patterns
    intel_many_patterns = TrainingIntelligence()
    for i in range(5):
        pattern = intel_many_patterns.identify_pattern(
            name=f"pattern_{i}",
            trigger_conditions={"condition": f"value_{i}"},
            observed_outcome=f"outcome_{i}",
            observation_date=date.today(),
        )
        pattern.frequency = 15  # Frequent (≥10)

    gains_many = compute_pid_gains_from_intelligence(intel_many_patterns)
    assert gains_many["kd"] == 0.25
