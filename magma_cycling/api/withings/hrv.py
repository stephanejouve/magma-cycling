"""HRV mixin for WithingsClient.

Exposes nocturnal RMSSD start/end averages from Withings Sleep Analyzer
via the ``v2/sleep/getsummary`` endpoint. Daytime SDNN via
``v2/measure/getintradayactivity`` is covered in a separate method that
may ship in a later iteration.

Only devices capable of HRV capture fill these fields — Sleep Analyzer
(model 32) in the EU and Sleep Rx in the US. Other devices return no HRV
data and the methods return an empty list without raising.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


class HrvMixin:
    """Sleep HRV retrieval (nocturnal start/end RMSSD averages)."""

    def get_sleep_hrv(
        self,
        start_date: date,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve nocturnal HRV summaries via sleep/getsummary.

        Args:
            start_date: First night to cover (inclusive).
            end_date: Last night to cover (inclusive, default: today).

        Returns:
            One dict per night with keys ``date``, ``rmssd_start_avg`` (float|None, ms),
            ``rmssd_end_avg`` (float|None, ms), ``model`` (int|None), ``model_id``
            (int|None). Nights without HRV data (unsupported device) are still
            returned with rmssd_*_avg = None so the caller can see the gap.
        """
        if end_date is None:
            end_date = date.today()

        params = {
            "action": "getsummary",
            "startdateymd": start_date.strftime("%Y-%m-%d"),
            "enddateymd": end_date.strftime("%Y-%m-%d"),
            "data_fields": "rmssd_start_avg,rmssd_end_avg",
        }

        body = self._make_request("v2/sleep", params)

        result = []
        for session in body.get("series", []):
            data = session.get("data") or {}
            result.append(
                {
                    "date": session.get("date"),
                    "rmssd_start_avg": data.get("rmssd_start_avg"),
                    "rmssd_end_avg": data.get("rmssd_end_avg"),
                    "model": session.get("model"),
                    "model_id": session.get("model_id"),
                }
            )

        logger.info("Retrieved %d HRV sleep summaries", len(result))
        return result
