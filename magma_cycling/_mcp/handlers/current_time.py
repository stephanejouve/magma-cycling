"""Current time handler — AC6 levier 2/3 du plan iso-config S093-S096.

Ultra-light handler retournant l'autorité temporelle serveur sous forme
structurée. À appeler par le LLM coach dès qu'il doute de son contexte
temporel (drift typique sur conversations longues qui traversent minuit,
ou sessions reprises après plusieurs jours).

Conventions de retour :
- UTC + local + timezone explicite (3 vues redondantes pour annuler tout
  doute sur le décalage)
- jour de la semaine en français + numérique (0=lundi, semaine ISO)
- aides dérivées : today_iso, iso_year_week, hour_of_day, is_weekend
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response

if TYPE_CHECKING:
    from mcp.types import TextContent

logger = logging.getLogger(__name__)

__all__ = ["handle_current_time"]


_DAY_OF_WEEK_FR = {
    0: "lundi",
    1: "mardi",
    2: "mercredi",
    3: "jeudi",
    4: "vendredi",
    5: "samedi",
    6: "dimanche",
}


async def handle_current_time(args: dict) -> list[TextContent]:
    """Return canonical server time information as a structured payload.

    Designed as time-of-truth callable for LLM clients (Coach IA, Claude
    Desktop, etc.) that need to anchor their temporal context without
    inferring it from conversation history. AC6 levier 2/3.
    """
    now_local = datetime.now().astimezone()
    now_utc = now_local.astimezone(timezone.utc)

    iso_year, iso_week, _ = now_local.isocalendar()

    return mcp_response(
        {
            "server_time_utc": now_utc.isoformat(timespec="seconds"),
            "server_time_local": now_local.isoformat(timespec="seconds"),
            "tz": str(now_local.tzinfo),
            "today_iso": now_local.date().isoformat(),
            "day_of_week_fr": _DAY_OF_WEEK_FR[now_local.weekday()],
            "day_of_week_num": now_local.weekday(),
            "iso_year_week": f"{iso_year}-W{iso_week:02d}",
            "hour_of_day": now_local.hour,
            "is_weekend": now_local.weekday() >= 5,
        }
    )
