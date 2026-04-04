"""Athlete context loader for AI coaching prompts.

Loads static athlete profile from YAML for injection into AI prompts.
Dynamic metrics (FTP, CTL, ATL) come from AthleteProfile.from_env()
and Intervals.icu API at runtime — not duplicated here.
"""

import logging
from pathlib import Path

import yaml

from magma_cycling.paths import get_athlete_yaml_path

logger = logging.getLogger(__name__)

# User config dir first (bundle or dev), then fallback to bundled data
_user_yaml = get_athlete_yaml_path()
ATHLETE_CONTEXT_PATH = (
    _user_yaml if _user_yaml.exists() else Path(__file__).parent / "athlete_context.yaml"
)


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
