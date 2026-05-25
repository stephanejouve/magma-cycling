"""Shared utilities for MCP handlers."""

import json
import sys
from contextlib import contextmanager
from datetime import date, datetime, timezone
from io import StringIO

from mcp.types import TextContent

from magma_cycling.utils.event_sync import compute_start_time  # noqa: F401 — re-export

# AC6 (plan iso-config S093-S096) — autorité temporelle injectée dans toute
# réponse MCP pour que le LLM coach puisse recaler sa dérive sans appel
# `current-time` explicite. Naming aligné avec :mod:`current_time` handler
# (PR8ter) et CDC import-context §2.2 — server_time_utc est l'unique champ
# nom-stable que les consommateurs doivent lire pour leur clock interne.
_DAY_OF_WEEK_FR = {
    0: "lundi",
    1: "mardi",
    2: "mercredi",
    3: "jeudi",
    4: "vendredi",
    5: "samedi",
    6: "dimanche",
}


def build_server_time_metadata(now_local: datetime | None = None) -> dict:
    """Return the 5 AC6 timestamp fields injected into every MCP `_metadata`.

    Single source of truth for the temporal anchor exposed to LLM consumers
    (Coach IA, Claude Desktop). Aligné avec `handle_current_time` (PR8ter)
    qui renvoie ces 5 champs au top-level + 4 dérivés ; ici on factorise
    les 5 cœur dans un helper réutilisable côté wrapper :func:`mcp_response`.

    Args:
        now_local: instant local TZ-aware optionnel. Défaut =
            ``datetime.now().astimezone()`` (instant d'invocation). Le
            paramètre permet aux appelants qui ont déjà calculé un
            ``now_local`` (ex: handler current-time) de partager l'instant
            exact entre payload et metadata, évitant toute dérive sub-seconde.

    Returns:
        Dict avec 5 clés stables :
            - ``server_time_utc``   : ISO 8601 UTC (timespec seconds)
            - ``server_time_local`` : ISO 8601 local + offset
            - ``tz``                : nom de timezone (str)
            - ``today_iso``         : date locale YYYY-MM-DD
            - ``day_of_week_fr``    : jour de la semaine en français
    """
    if now_local is None:
        now_local = datetime.now().astimezone()
    now_utc = now_local.astimezone(timezone.utc)
    return {
        "server_time_utc": now_utc.isoformat(timespec="seconds"),
        "server_time_local": now_local.isoformat(timespec="seconds"),
        "tz": str(now_local.tzinfo),
        "today_iso": now_local.date().isoformat(),
        "day_of_week_fr": _DAY_OF_WEEK_FR[now_local.weekday()],
    }


@contextmanager
def suppress_stdout_stderr():
    """Suppress all stdout/stderr to prevent MCP protocol pollution."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


# Statuses that should be synced to Intervals.icu.
# Any other status (completed, skipped, cancelled, rest_day, replaced) is protected.
SYNCABLE_STATUSES = {"pending", "planned", "uploaded", "modified"}


def load_workout_descriptions(week_id: str) -> dict[str, str]:
    """Load full workout descriptions from {week_id}_workouts.txt.

    Delegates to workout_parser.load_workout_descriptions.
    """
    from magma_cycling.workout_parser import load_workout_descriptions as _load

    return _load(week_id)


def mcp_response(
    result: dict, *, provider_info: dict | None = None, **json_kwargs
) -> list[TextContent]:
    """Wrap a result dict with _metadata and return as MCP TextContent.

    Le ``_metadata`` injecté contient :

    - ``response_date`` / ``response_timestamp`` — naming historique conservé
      pour rétro-compat des consumers existants (naive datetime).
    - 5 champs AC6 via :func:`build_server_time_metadata`
      (``server_time_utc``, ``server_time_local``, ``tz``, ``today_iso``,
      ``day_of_week_fr``) — naming stable cross-handlers exigé par le CDC
      import-context §2.2 et la convention dérive temporelle LLM (Levier
      1/3 AC6 plan iso-config S093-S096).
    - ``provider`` — optionnel, identifie la source data quand pertinent.
    """
    now_local = datetime.now().astimezone()
    metadata: dict = {
        "response_date": date.today().isoformat(),
        "response_timestamp": now_local.replace(tzinfo=None).isoformat(),
        **build_server_time_metadata(now_local),
    }
    if provider_info:
        metadata["provider"] = provider_info
    result["_metadata"] = metadata
    json_kwargs.setdefault("indent", 2)
    return [TextContent(type="text", text=json.dumps(result, **json_kwargs))]
