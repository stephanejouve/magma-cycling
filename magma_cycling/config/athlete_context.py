"""Athlete context loader for AI coaching prompts.

Loads static athlete profile from YAML for injection into AI prompts.
Dynamic metrics (FTP, CTL, ATL) come from AthleteProfile.from_env()
and Intervals.icu API at runtime — not duplicated here.
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

ATHLETE_CONTEXT_PATH = Path(__file__).parent / "athlete_context.yaml"


def load_athlete_context(path: Path | None = None) -> dict:
    """Load static athlete context from YAML.

    Args:
        path: Custom path to YAML file. Defaults to athlete_context.yaml
              next to this module.

    Returns:
        Dict with athlete context, or empty dict if file absent
        (graceful degradation).
    """
    context_path = path or ATHLETE_CONTEXT_PATH
    if not context_path.exists():
        logger.warning("Athlete context not found at %s, using empty context", context_path)
        return {}
    try:
        with open(context_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("athlete", {}) if data else {}
    except Exception:
        logger.exception("Failed to load athlete context from %s", context_path)
        return {}
