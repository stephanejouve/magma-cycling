"""AI coaching prompt assembly.

Builds (system_prompt, user_prompt) tuples for each workflow mission.
System prompt = base_system.txt + formatted athlete profile + mission.txt
User prompt = workflow-specific data (stats, session data, etc.)
"""

import logging
from datetime import datetime
from pathlib import Path

from magma_cycling.config.athlete_context import load_athlete_context

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent

VALID_MISSIONS = frozenset(
    {"mesocycle_analysis", "weekly_planning", "daily_feedback", "weekly_review"}
)


def load_current_metrics() -> dict:
    """Load FTP, weight, CTL, ATL, ramp_rate from env + Intervals.icu API.

    Returns:
        Dict with ftp, weight, ctl, atl, ramp_rate keys.
        Empty dict on failure (graceful degradation).
    """
    metrics: dict = {}
    try:
        from magma_cycling.config import AthleteProfile

        profile = AthleteProfile.from_env()
        metrics["ftp"] = profile.ftp
        metrics["weight"] = profile.weight
    except Exception:
        logger.debug("Could not load AthleteProfile, skipping FTP/weight")

    day = {}
    try:
        from magma_cycling.config import create_intervals_client

        today = datetime.now().strftime("%Y-%m-%d")
        client = create_intervals_client()
        wellness = client.get_wellness(oldest=today, newest=today)
        if wellness:
            day = wellness[0]
            metrics["ctl"] = day.get("ctl")
            metrics["atl"] = day.get("atl")
            metrics["ramp_rate"] = day.get("rampRate")
    except Exception:
        logger.debug("Could not load Intervals.icu metrics, skipping CTL/ATL")

    # --- ACWR / Monotony / Strain + consecutive days (1 extra API call: 28d activities) ---
    activities = []
    try:
        from datetime import timedelta

        from magma_cycling.utils.training_load import (
            compute_training_load,
            count_consecutive_training_days,
        )

        if "client" not in locals():
            from magma_cycling.config import create_intervals_client

            client = create_intervals_client()
            today = datetime.now().strftime("%Y-%m-%d")

        oldest_28d = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
        activities = client.get_activities(oldest=oldest_28d, newest=today)
        load = compute_training_load(activities)
        if load:
            metrics["acwr"] = load["acwr"]
            metrics["monotony"] = load["monotony"]
            metrics["strain"] = load["strain"]
        consec = count_consecutive_training_days(activities)
        if consec:
            metrics["consecutive_training_days"] = consec["consecutive_days"]
    except Exception:
        logger.debug("Could not compute training load indicators")

    # --- Derived metrics from existing data (no extra API call) ---
    ctl = metrics.get("ctl")
    atl = metrics.get("atl")
    if isinstance(ctl, (int, float)) and isinstance(atl, (int, float)) and ctl > 0:
        from magma_cycling.utils.metrics_advanced import (
            detect_overtraining_risk,
            get_recovery_recommendation,
        )

        tsb = ctl - atl
        ratio = atl / ctl
        metrics["atl_ctl_ratio"] = round(ratio, 2)
        metrics["tsb"] = round(tsb, 1)

        sleep_secs = day.get("sleepSecs") if day else None
        sleep_hours = sleep_secs / 3600 if sleep_secs else None

        try:
            risk = detect_overtraining_risk(
                ctl=ctl,
                atl=atl,
                tsb=tsb,
                sleep_hours=sleep_hours,
                consecutive_days=metrics.get("consecutive_training_days"),
                profile={"age": 54, "category": "master", "sleep_dependent": True},
            )
            metrics["overtraining_risk"] = risk["risk_level"]
            metrics["overtraining_veto"] = risk["veto"]
            metrics["overtraining_factors"] = risk["factors"]

            recovery = get_recovery_recommendation(
                tsb=tsb,
                atl_ctl_ratio=ratio,
                profile={"age": 54, "category": "master"},
            )
            metrics["recovery_priority"] = recovery["priority"]
            metrics["recovery_recommendation"] = recovery["recommendation"]
            metrics["intensity_limit_pct"] = recovery["intensity_limit"]
        except Exception:
            logger.debug("Could not compute overtraining/recovery metrics")

    return metrics


def build_prompt(
    mission: str,
    current_metrics: dict,
    workflow_data: str,
    athlete_context: dict | None = None,
) -> tuple[str, str]:
    """Assemble (system_prompt, user_prompt) for a given workflow.

    Args:
        mission: One of VALID_MISSIONS.
        current_metrics: Runtime metrics (ftp, weight, ctl, atl, etc.).
        workflow_data: Workflow-specific data string (stats, session, etc.).
        athlete_context: Override for athlete context dict. If None, loads
            from default YAML.

    Returns:
        Tuple of (system_prompt, user_prompt).

    Raises:
        ValueError: If mission is not in VALID_MISSIONS.
        FileNotFoundError: If a required prompt template file is missing.
    """
    if mission not in VALID_MISSIONS:
        raise ValueError(f"Unknown mission '{mission}'. Valid: {sorted(VALID_MISSIONS)}")

    context = athlete_context if athlete_context is not None else load_athlete_context()

    # Load template files
    base_text = (PROMPTS_DIR / "base_system.txt").read_text(encoding="utf-8")
    mission_text = (PROMPTS_DIR / f"{mission}.txt").read_text(encoding="utf-8")

    # Assemble system prompt
    profile_text = format_athlete_profile(context, current_metrics)
    system_prompt = f"{base_text}\n\n## Profil athlete\n{profile_text}\n\n{mission_text}"

    return system_prompt, workflow_data


def format_athlete_profile(context: dict, metrics: dict) -> str:
    """Format athlete profile for prompt injection.

    Args:
        context: Static athlete context from YAML.
        metrics: Runtime metrics dict with keys like ftp, weight, ctl, atl.

    Returns:
        Formatted multi-line string for prompt injection.
    """
    if not context:
        return "(Contexte athlete non disponible)"

    ftp = metrics.get("ftp")
    weight = metrics.get("weight")
    if isinstance(ftp, (int, float)) and isinstance(weight, (int, float)) and weight > 0:
        w_per_kg = f"{ftp / weight:.2f}"
    else:
        w_per_kg = "?"

    lines = [
        f"- {context.get('name', 'Athlete')}, {context.get('age', '?')} ans",
        f"- FTP: {ftp if ftp is not None else '?'}W ({w_per_kg} W/kg)"
        f" - Poids: {weight if weight is not None else '?'}kg",
        f"- Entrainement structure depuis {context.get('training_since', '?')}",
        f"- Plateforme: {context.get('platform', '?')}",
        f"- Objectifs: {context.get('objectives', 'Non definis')}",
    ]

    # Dynamic metrics line
    ctl = metrics.get("ctl")
    atl = metrics.get("atl")
    ramp = metrics.get("ramp_rate")
    metrics_parts = []
    if ctl is not None:
        metrics_parts.append(f"CTL: {ctl:.1f}" if isinstance(ctl, float) else f"CTL: {ctl}")
    if atl is not None:
        metrics_parts.append(f"ATL: {atl:.1f}" if isinstance(atl, float) else f"ATL: {atl}")
    if ramp is not None:
        metrics_parts.append(f"Ramp: {ramp}")
    if metrics_parts:
        lines.append(f"- {' | '.join(metrics_parts)}")

    # Load indicators (derived metrics)
    risk = metrics.get("overtraining_risk")
    if risk:
        tsb = metrics.get("tsb")
        ratio = metrics.get("atl_ctl_ratio")
        lines.append("")
        lines.append("Indicateurs de charge:")
        lines.append(f"  - TSB: {tsb:+.1f}")
        lines.append(f"  - ATL/CTL ratio: {ratio:.2f}")
        lines.append(f"  - Risque surentrainement: {risk.upper()}")
        if metrics.get("overtraining_veto"):
            lines.append("  - VETO ACTIF: repos ou Z1 uniquement")
        factors = metrics.get("overtraining_factors", [])
        if factors:
            for f in factors:
                lines.append(f"  - Signal: {f}")
        rec = metrics.get("recovery_recommendation")
        if rec:
            lines.append(f"  - Prescription recup: {rec}")
            limit = metrics.get("intensity_limit_pct")
            if limit and limit < 100:
                lines.append(f"  - Intensite max: {limit}% FTP")
        acwr = metrics.get("acwr")
        if acwr is not None:
            if acwr < 0.8:
                acwr_label = "sous-entrainement"
            elif acwr <= 1.3:
                acwr_label = "optimal"
            elif acwr <= 1.5:
                acwr_label = "attention"
            else:
                acwr_label = "DANGER"
            lines.append(f"  - ACWR: {acwr:.2f} ({acwr_label})")
        monotony = metrics.get("monotony")
        if monotony is not None:
            mono_label = "elevee (risque)" if monotony > 2.0 else "OK"
            lines.append(f"  - Monotonie: {monotony:.2f} ({mono_label})")
        strain = metrics.get("strain")
        if strain is not None:
            strain_label = "ALERTE" if strain > 3500 else "OK"
            lines.append(f"  - Strain: {strain:.0f} ({strain_label})")
        consec = metrics.get("consecutive_training_days")
        if consec and consec >= 2:
            lines.append(f"  - Jours consecutifs: {consec}")

    # Constraints
    constraints = context.get("constraints", [])
    if constraints:
        lines.append("")
        lines.append("Contraintes connues:")
        for c in constraints:
            lines.append(f"  - {c}")

    # System context
    sys_ctx = context.get("system_context", "")
    if sys_ctx:
        lines.append("")
        lines.append(sys_ctx.strip())

    return "\n".join(lines)
