"""Pre-session VETO check for overtraining risk (P0 CRITICAL)."""

from magma_cycling.config import get_logger

logger = get_logger(__name__)


def check_pre_session_veto(
    wellness_data: dict, athlete_profile: dict, session_intensity: float | None = None
) -> dict:
    """Check if session should be vetoed due to overtraining risk (CRITICAL safety).

    This function implements VETO logic to protect master athletes from
    overtraining. It should be called BEFORE any high-intensity session
    (>85% FTP) to determine if the session should be cancelled.

    VETO Triggers (Master Athlete):
        - TSB < -25 (critical fatigue)
        - ATL/CTL ratio > 1.8 (acute overload)
        - Sleep < 5.5h (insufficient recovery)
        - Sleep < 6h + TSB < -15 (combined stress)

    Args:
        wellness_data: Wellness metrics from Intervals.icu containing:
            - ctl: Chronic Training Load (fitness)
            - atl: Acute Training Load (fatigue)
            - tsb: Training Stress Balance (form)
            - sleep_hours: Hours of sleep (optional)
        athlete_profile: Athlete characteristics:
            - age: Athlete age
            - category: 'junior', 'senior', or 'master'
            - sleep_dependent: True if performance highly sleep-dependent
        session_intensity: Optional session intensity (% FTP) for context

    Returns:
        Dict with keys:
            - cancel: True if session should be cancelled (VETO)
            - risk_level: 'low', 'medium', 'high', or 'critical'
            - recommendation: Detailed recommendation text
            - factors: List of VETO factors triggered
            - veto: Boolean (same as cancel, for backward compatibility)

    Examples:
        >>> # Check before high-intensity session
        >>> wellness = api.get_wellness(oldest=date, newest=date)[0]
        >>> profile = AthleteProfile.from_env()
        >>> result = check_pre_session_veto(wellness, profile.dict(), 95.0)
        >>> if result['cancel']:
        ...     log_cancellation(date, reason=result['recommendation'])
        ...     print(f"VETO: {result['factors']}")

        >>> # Normal session (no VETO)
        >>> wellness = {'ctl': 65, 'atl': 60, 'tsb': 5, 'sleep_hours': 7.5}
        >>> profile = {'age': 54, 'category': 'master'}
        >>> result = check_pre_session_veto(wellness, profile)
        >>> result['cancel']
        False

        >>> # VETO triggered (critical TSB)
        >>> wellness = {'ctl': 65, 'atl': 95, 'tsb': -30, 'sleep_hours': 7}
        >>> result = check_pre_session_veto(wellness, profile)
        >>> result['cancel']
        True
        >>> result['factors']
        ['TSB < -25 (critical fatigue)']

    Notes:
        - VETO logic calibrated for master athletes (50+ years)
        - For senior athletes, thresholds can be adjusted in detect_overtraining_risk()
        - If wellness data incomplete, function returns conservative recommendation
        - Sleep hours optional but strongly recommended for accurate assessment

    See Also:
        - detect_overtraining_risk() in utils/metrics_advanced.py (core logic)
        - generate_cancelled_session_entry() for logging cancelled sessions
        - VETO_PROTOCOL.md for detailed protocol documentation

    Version:
        Added: Sprint R2.1 (2026-01-01)
        Priority: P0 (CRITICAL - athlete safety)
    """
    from magma_cycling.utils.metrics_advanced import detect_overtraining_risk

    # Extract metrics from wellness data
    ctl = wellness_data.get("ctl", 0)
    atl = wellness_data.get("atl", 0)
    tsb = wellness_data.get("tsb")

    # Calculate TSB if not provided
    if tsb is None and ctl > 0:
        tsb = ctl - atl
    elif tsb is None:
        tsb = 0

    sleep_hours = wellness_data.get("sleep_hours")

    # Call VETO detection (Sprint R2.1)
    risk_result = detect_overtraining_risk(
        ctl=ctl, atl=atl, tsb=tsb, sleep_hours=sleep_hours, profile=athlete_profile
    )

    # Build result with additional context
    result = {
        "cancel": risk_result["veto"],
        "veto": risk_result["veto"],  # Backward compatibility
        "risk_level": risk_result["risk_level"],
        "recommendation": risk_result["recommendation"],
        "factors": risk_result["factors"],
    }

    # Add session intensity context if provided
    if session_intensity and risk_result["veto"]:
        logger.warning(f"⚠️  VETO: Session cancelled (intensity={session_intensity:.0f}% FTP)")
        logger.warning(f"Factors: {', '.join(risk_result['factors'])}")
        result["session_intensity"] = session_intensity

    return result
