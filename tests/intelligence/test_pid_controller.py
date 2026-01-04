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
