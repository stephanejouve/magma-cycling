"""Athlete context loader for AI coaching prompts.

Loads static athlete profile from YAML for injection into AI prompts.
Dynamic metrics (FTP, CTL, ATL) come from AthleteProfile.from_env()
and Intervals.icu API at runtime — not duplicated here.

PR5 plan iso-config (AC1 portabilité athlète) : the YAML now lives in
``<TRAINING_DATA_ROOT>/config/athlete.yaml`` (portable, shared cross
operators). Resolution priority is delegated to
:func:`magma_cycling.config.data_repo.resolve_athlete_yaml_path`. The
bundled ``athlete_context.yaml`` next to this module is kept as a
bootstrap fallback (read-only) for first-boot scenarios where the repo
training-logs has no ``config/athlete.yaml`` yet.
"""

import logging
from pathlib import Path

import yaml

from magma_cycling.config.data_repo import resolve_athlete_yaml_path

logger = logging.getLogger(__name__)

#: Bundle fallback (read-only) shipped inside the package — used only when
#: the resolved athlete YAML does not exist on disk yet (1st boot).
BUNDLE_ATHLETE_YAML = Path(__file__).parent / "athlete_context.yaml"


def load_athlete_context(path: Path | None = None) -> dict:
    """Load static athlete context from YAML.

    Resolution chain (when ``path`` not provided):
      1. :func:`resolve_athlete_yaml_path` (env override, then training-logs
         repo, then legacy user config dir).
      2. Bundle fallback :data:`BUNDLE_ATHLETE_YAML` if (1) does not exist
         on disk (bootstrap initial après un fresh clone du repo).

    Returns:
        Dict with athlete context, or empty dict if no source available
        (graceful degradation).
    """
    if path is not None:
        context_path = path
    else:
        resolved = resolve_athlete_yaml_path()
        context_path = resolved if resolved.exists() else BUNDLE_ATHLETE_YAML
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
