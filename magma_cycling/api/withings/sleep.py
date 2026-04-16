"""Sleep data mixin for WithingsClient."""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class SleepMixin:
    """Sleep data retrieval and segment aggregation."""

    def get_sleep(
        self,
        start_date: date,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get sleep summary data for a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive, default: today)

        Returns:
            List of sleep sessions as dictionaries

        Example:
            >>> from datetime import date, timedelta
            >>> end = date.today()
            >>> start = end - timedelta(days=7)
            >>> sleep_data = client.get_sleep(start, end)
            >>> for session in sleep_data:
            ...     print(f"{session['date']}: {session['total_sleep_hours']}h")
        """
        if end_date is None:
            end_date = date.today()

        params = {
            "action": "getsummary",
            "startdateymd": start_date.strftime("%Y-%m-%d"),
            "enddateymd": end_date.strftime("%Y-%m-%d"),
            "data_fields": ",".join(
                [
                    "sleep_score",
                    "sleep_efficiency",
                    "total_sleep_time",
                    "deepsleepduration",
                    "lightsleepduration",
                    "remsleepduration",
                    "wakeupcount",
                    "wakeupduration",
                    "hr_average",
                    "hr_min",
                    "hr_max",
                    "rr_average",
                    "rr_min",
                    "rr_max",
                    "sleep_latency",
                    "out_of_bed_count",
                    "waso",
                    "nb_rem_episodes",
                ]
            ),
        }

        body = self._make_request("v2/sleep", params)

        sleep_sessions = []
        series = body.get("series", [])

        for session in series:
            # Parse sleep data
            start_ts = session.get("startdate")
            end_ts = session.get("enddate")

            if not start_ts or not end_ts:
                continue

            start_dt = datetime.fromtimestamp(start_ts)
            end_dt = datetime.fromtimestamp(end_ts)

            # Sleep date is the ending date (morning)
            sleep_date = end_dt.date()

            # Calculate total sleep in hours
            total_sleep_seconds = session.get("data", {}).get("total_sleep_time", 0)
            total_sleep_hours = total_sleep_seconds / 3600 if total_sleep_seconds else 0

            # Get sleep stages and metrics
            data = session.get("data", {})
            deep_sleep_sec = data.get("deepsleepduration", 0)
            light_sleep_sec = data.get("lightsleepduration", 0)
            rem_sleep_sec = data.get("remsleepduration", 0)
            wakeup_dur_sec = data.get("wakeupduration", 0)

            sleep_sessions.append(
                {
                    "date": sleep_date.isoformat(),
                    "start_datetime": start_dt.isoformat(),
                    "end_datetime": end_dt.isoformat(),
                    "total_sleep_hours": round(total_sleep_hours, 2),
                    "deep_sleep_minutes": round(deep_sleep_sec / 60, 1) if deep_sleep_sec else None,
                    "light_sleep_minutes": (
                        round(light_sleep_sec / 60, 1) if light_sleep_sec else None
                    ),
                    "rem_sleep_minutes": round(rem_sleep_sec / 60, 1) if rem_sleep_sec else None,
                    "sleep_score": data.get("sleep_score"),
                    "sleep_efficiency": data.get("sleep_efficiency"),
                    "wakeup_count": data.get("wakeupcount", 0),
                    "wakeup_minutes": round(wakeup_dur_sec / 60, 1) if wakeup_dur_sec else None,
                    "hr_average": data.get("hr_average"),
                    "hr_min": data.get("hr_min"),
                    "hr_max": data.get("hr_max"),
                    "rr_average": data.get("rr_average"),
                    "rr_min": data.get("rr_min"),
                    "rr_max": data.get("rr_max"),
                    "sleep_latency_min": (
                        round(data.get("sleep_latency", 0) / 60, 1)
                        if data.get("sleep_latency")
                        else None
                    ),
                    "out_of_bed_count": data.get("out_of_bed_count"),
                    "breathing_disturbances": data.get("breathing_disturbances_intensity"),
                }
            )

        # Filter false positives before aggregation
        sleep_sessions = self._filter_false_positives(sleep_sessions)

        # Aggregate segments by sleep_date
        sleep_sessions = self._aggregate_sleep_segments(sleep_sessions)

        logger.info(f"Retrieved {len(sleep_sessions)} sleep sessions")
        return sleep_sessions

    @staticmethod
    def _filter_false_positives(
        sessions: list[dict],
        min_sleep_hours: float = 2.0,
        min_nap_hours: float = 1.5,
    ) -> list[dict]:
        """Filter out Withings false positive sleep segments.

        Short segments during the night (< 2h) and short daytime segments
        (< 1.5h, 06:00-20:00) are likely inactivity misdetected as sleep.
        """
        filtered = []
        for s in sessions:
            hours = s["total_sleep_hours"]
            start_str = s.get("start_datetime", "")
            start_hour = int(start_str[11:13]) if len(start_str) >= 13 else 0
            is_daytime = 6 <= start_hour < 20

            if not is_daytime and hours < min_sleep_hours:
                logger.warning("Filtered short night segment: %.1fh (%s)", hours, start_str)
                continue
            if is_daytime and hours < min_nap_hours:
                logger.warning("Filtered short daytime segment: %.1fh (%s)", hours, start_str)
                continue
            filtered.append(s)
        return filtered

    @staticmethod
    def _aggregate_sleep_segments(
        sessions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Aggregate multiple Withings segments that belong to the same night.

        Withings may split a single night into multiple segments (e.g. 22h->01h30
        + 01h30->07h). This method merges them into one session per date.
        """
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for s in sessions:
            by_date[s["date"]].append(s)

        result: list[dict[str, Any]] = []
        for sleep_date, segments in sorted(by_date.items()):
            if len(segments) == 1:
                segments[0]["segments_count"] = 1
                result.append(segments[0])
                continue

            # Sort segments by start time
            segments.sort(key=lambda s: s["start_datetime"])

            merged: dict[str, Any] = {
                "date": sleep_date,
                "start_datetime": min(s["start_datetime"] for s in segments),
                "end_datetime": max(s["end_datetime"] for s in segments),
            }

            # Sum durations
            merged["total_sleep_hours"] = round(sum(s["total_sleep_hours"] for s in segments), 2)

            # Sum sleep stages (skip None)
            for key in ("deep_sleep_minutes", "light_sleep_minutes", "rem_sleep_minutes"):
                values = [s[key] for s in segments if s.get(key) is not None]
                merged[key] = round(sum(values), 1) if values else None

            # Sum counts
            merged["wakeup_count"] = sum(s.get("wakeup_count", 0) for s in segments)
            merged["wakeup_minutes"] = None
            wakeup_vals = [s["wakeup_minutes"] for s in segments if s.get("wakeup_minutes")]
            if wakeup_vals:
                merged["wakeup_minutes"] = round(sum(wakeup_vals), 1)

            merged["out_of_bed_count"] = None
            oob_vals = [s["out_of_bed_count"] for s in segments if s.get("out_of_bed_count")]
            if oob_vals:
                merged["out_of_bed_count"] = sum(oob_vals)

            # First non-None for scores
            merged["sleep_score"] = next(
                (s["sleep_score"] for s in segments if s.get("sleep_score") is not None), None
            )
            merged["sleep_efficiency"] = next(
                (s["sleep_efficiency"] for s in segments if s.get("sleep_efficiency") is not None),
                None,
            )

            # HR: min/max/weighted average
            hr_mins = [s["hr_min"] for s in segments if s.get("hr_min") is not None]
            hr_maxs = [s["hr_max"] for s in segments if s.get("hr_max") is not None]
            merged["hr_min"] = min(hr_mins) if hr_mins else None
            merged["hr_max"] = max(hr_maxs) if hr_maxs else None

            hr_avgs = [
                (s["hr_average"], s["total_sleep_hours"])
                for s in segments
                if s.get("hr_average") is not None and s["total_sleep_hours"] > 0
            ]
            if hr_avgs:
                total_dur = sum(d for _, d in hr_avgs)
                merged["hr_average"] = round(sum(v * d for v, d in hr_avgs) / total_dur)
            else:
                merged["hr_average"] = None

            # RR: min/max/weighted average
            rr_mins = [s["rr_min"] for s in segments if s.get("rr_min") is not None]
            rr_maxs = [s["rr_max"] for s in segments if s.get("rr_max") is not None]
            merged["rr_min"] = min(rr_mins) if rr_mins else None
            merged["rr_max"] = max(rr_maxs) if rr_maxs else None

            rr_avgs = [
                (s["rr_average"], s["total_sleep_hours"])
                for s in segments
                if s.get("rr_average") is not None and s["total_sleep_hours"] > 0
            ]
            if rr_avgs:
                total_dur = sum(d for _, d in rr_avgs)
                merged["rr_average"] = round(sum(v * d for v, d in rr_avgs) / total_dur, 1)
            else:
                merged["rr_average"] = None

            # Sleep latency from first segment only
            merged["sleep_latency_min"] = segments[0].get("sleep_latency_min")

            # Breathing disturbances: first non-None
            merged["breathing_disturbances"] = next(
                (
                    s["breathing_disturbances"]
                    for s in segments
                    if s.get("breathing_disturbances") is not None
                ),
                None,
            )

            # Fragmentation metadata
            merged["segments_count"] = len(segments)
            merged["segments_detail"] = []
            for seg in segments:
                start_str = seg["start_datetime"]
                end_str = seg["end_datetime"]
                # Parse ISO strings to extract HH:MM
                start_hm = start_str[11:16] if len(start_str) >= 16 else start_str
                end_hm = end_str[11:16] if len(end_str) >= 16 else end_str
                merged["segments_detail"].append(
                    {
                        "start": start_hm,
                        "end": end_hm,
                        "duration_hours": seg["total_sleep_hours"],
                    }
                )

            result.append(merged)

        return result

    def get_last_night_sleep(self) -> dict[str, Any] | None:
        """Get last night's sleep data.

        Returns:
            Sleep session dict for last night, or None if not available

        Example:
            >>> sleep = client.get_last_night_sleep()
            >>> if sleep:
            ...     print(f"Slept {sleep['total_sleep_hours']}h")
        """
        # Get sleep from yesterday and today
        today = date.today()
        yesterday = today - timedelta(days=1)

        sessions = self.get_sleep(yesterday, today)

        if not sessions:
            return None

        # Return the most recent session
        return max(sessions, key=lambda s: s["end_datetime"])
