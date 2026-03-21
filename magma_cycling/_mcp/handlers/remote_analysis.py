"""Remote analysis handlers (compare activity intervals, apply workout intervals)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_compare_activity_intervals",
    "handle_apply_workout_intervals",
]


async def handle_compare_activity_intervals(args: dict) -> list[TextContent]:
    """Compare interval data across multiple activities to track progression."""
    from magma_cycling.config import create_intervals_client

    NUMERIC_METRICS = {
        "elapsed_time",
        "moving_time",
        "distance",
        "average_watts",
        "weighted_average_watts",
        "min_watts",
        "max_watts",
        "average_heartrate",
        "min_heartrate",
        "max_heartrate",
        "average_cadence",
        "intensity",
        "training_load",
        "decoupling",
        "average_speed",
        "total_elevation_gain",
        "average_torque",
        "min_torque",
        "max_torque",
        "avg_lr_balance",
    }

    activity_ids = args.get("activity_ids")
    name_pattern = args.get("name_pattern")
    weeks_back = args.get("weeks_back", 6)
    label_filter = args.get("label_filter")
    type_filter = args.get("type_filter")
    requested_metrics = args.get("metrics")

    if not activity_ids and not name_pattern:
        error = {
            "error": "Either 'activity_ids' or 'name_pattern' is required.",
        }
        return mcp_response(error)

    if requested_metrics:
        invalid = [m for m in requested_metrics if m not in NUMERIC_METRICS]
        if invalid:
            error = {
                "error": f"Invalid metrics: {invalid}",
                "available_metrics": sorted(NUMERIC_METRICS),
            }
            return mcp_response(error)

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

        if activity_ids:
            mode = "explicit"
            resolved = []
            for aid in activity_ids:
                with suppress_stdout_stderr():
                    act = client.get_activity(aid)
                resolved.append(
                    {
                        "id": aid,
                        "name": act.get("name", ""),
                        "date": (act.get("start_date_local", "") or "")[:10],
                    }
                )
        else:
            mode = "search"
            newest = date.today().isoformat()
            oldest = (date.today() - timedelta(weeks=weeks_back)).isoformat()
            with suppress_stdout_stderr():
                all_activities = client.get_activities(oldest=oldest, newest=newest)
            pattern_lower = name_pattern.lower()
            resolved = [
                {
                    "id": a.get("id", ""),
                    "name": a.get("name", ""),
                    "date": (a.get("start_date_local", "") or "")[:10],
                }
                for a in all_activities
                if pattern_lower in (a.get("name", "") or "").lower()
            ]
            resolved.sort(key=lambda x: x["date"])

            if not resolved:
                error = {
                    "error": f"No activities matching '{name_pattern}' in the last {weeks_back} weeks.",
                }
                return mcp_response(error)

        activity_intervals = {}
        for act_info in resolved:
            aid = act_info["id"]
            with suppress_stdout_stderr():
                raw = client.get_activity_intervals(aid)
            activity_intervals[aid] = raw

        activity_metadata = {a["id"]: {"name": a["name"], "date": a["date"]} for a in resolved}
        intervals_per_activity = {aid: len(ivs) for aid, ivs in activity_intervals.items()}

        metrics_to_use = set(requested_metrics) if requested_metrics else NUMERIC_METRICS

        filtered_intervals = {}
        for aid, raw_ivs in activity_intervals.items():
            kept = []
            for iv in raw_ivs:
                if (iv.get("elapsed_time") or 0) <= 2:
                    continue
                if type_filter and iv.get("type") != type_filter:
                    continue
                if label_filter and label_filter.lower() not in (iv.get("label", "") or "").lower():
                    continue
                kept.append(iv)
            filtered_intervals[aid] = kept

        label_groups = defaultdict(lambda: defaultdict(list))
        for aid, ivs in filtered_intervals.items():
            for iv in ivs:
                label = (iv.get("label", "") or "").strip().lower()
                label_groups[label][aid].append(iv)

        label_display = {}
        for aid, ivs in filtered_intervals.items():
            for iv in ivs:
                norm = (iv.get("label", "") or "").strip().lower()
                if norm not in label_display:
                    label_display[norm] = (iv.get("label", "") or "").strip()

        ordered_ids = [a["id"] for a in resolved]
        comparison = []
        for norm_label in sorted(label_groups.keys()):
            group = label_groups[norm_label]
            activities_data = []
            values_by_metric = defaultdict(list)

            for aid in ordered_ids:
                if aid not in group:
                    activities_data.append(
                        {
                            "activity_id": aid,
                            "date": activity_metadata[aid]["date"],
                            "data": None,
                        }
                    )
                    continue

                ivs = group[aid]
                agg = {}
                for metric in metrics_to_use:
                    vals = [iv[metric] for iv in ivs if metric in iv and iv[metric] is not None]
                    if vals:
                        avg_val = sum(vals) / len(vals)
                        agg[metric] = round(avg_val, 2) if avg_val != int(avg_val) else int(avg_val)

                activities_data.append(
                    {
                        "activity_id": aid,
                        "date": activity_metadata[aid]["date"],
                        "data": agg if agg else None,
                    }
                )

                for metric, val in agg.items():
                    values_by_metric[metric].append(val)

            trends = {}
            for metric, vals in values_by_metric.items():
                if len(vals) >= 2:
                    first = vals[0]
                    last = vals[-1]
                    delta = round(last - first, 2)
                    delta_pct = round((delta / first) * 100, 1) if first != 0 else None
                    avg = round(sum(vals) / len(vals), 2)
                    trends[metric] = {
                        "first": first,
                        "last": last,
                        "delta": delta,
                        "delta_pct": delta_pct,
                        "avg": avg,
                    }

            comparison.append(
                {
                    "label": label_display.get(norm_label, norm_label),
                    "activities": activities_data,
                    "trends": trends,
                }
            )

        result = {
            "mode": mode,
            "activities_compared": len(resolved),
            "activity_ids": ordered_ids,
            "activity_metadata": activity_metadata,
            "intervals_per_activity": intervals_per_activity,
            "filters_applied": {
                "label_filter": label_filter,
                "type_filter": type_filter,
                "metrics": requested_metrics if requested_metrics else "all",
            },
            "comparison": comparison,
        }

        return mcp_response(result)

    except Exception as e:
        error = {"error": f"Failed to compare intervals: {str(e)}"}
        return mcp_response(error)


async def handle_apply_workout_intervals(args: dict) -> list[TextContent]:
    """Apply custom interval boundaries to a remote activity."""
    import re

    from magma_cycling.config import create_intervals_client
    from magma_cycling.planning.models import SESSION_ID_PATTERN
    from magma_cycling.workout_parser import (
        compute_intervals,
        load_workout_descriptions,
        parse_workout_text,
    )

    activity_id = args["activity_id"]
    dry_run = args.get("dry_run", True)
    manual_intervals = args.get("intervals")

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()

        if manual_intervals is not None:
            if dry_run:
                preview = {
                    "mode": "manual",
                    "dry_run": True,
                    "activity_id": activity_id,
                    "intervals_count": len(manual_intervals),
                    "intervals": manual_intervals,
                    "message": "Preview only. Set dry_run=false to apply.",
                }
                return mcp_response(preview)
            with suppress_stdout_stderr():
                result = client.put_activity_intervals(activity_id, manual_intervals)
            applied = {
                "mode": "manual",
                "dry_run": False,
                "activity_id": activity_id,
                "applied": True,
                "result": result,
            }
            return mcp_response(applied)

        session_id = args.get("session_id")
        if not session_id:
            with suppress_stdout_stderr():
                activity = client.get_activity(activity_id)
            activity_name = activity.get("name", "")
            m = re.search(SESSION_ID_PATTERN, activity_name)
            if not m:
                error = {
                    "error": f"Cannot extract session_id from activity name: '{activity_name}'",
                    "hint": "Provide session_id parameter explicitly (e.g. S082-02)",
                }
                return mcp_response(error)
            session_id = m.group()

        week_id = session_id.split("-")[0]
        descriptions = load_workout_descriptions(week_id)

        workout_text = None
        for name, text in descriptions.items():
            if session_id in name:
                workout_text = text
                break

        if workout_text is None:
            error = {
                "error": f"No workout found for session {session_id} in {week_id}_workouts.txt",
                "available_workouts": list(descriptions.keys()),
            }
            return mcp_response(error)

        blocks = parse_workout_text(workout_text)
        if not blocks:
            error = {
                "error": f"Workout {session_id} is a rest day (no blocks to apply)",
            }
            return mcp_response(error)

        with suppress_stdout_stderr():
            streams = client.get_activity_streams(activity_id)

        if not streams or not streams[0].get("data"):
            error = {
                "error": f"No stream data found for activity {activity_id}",
            }
            return mcp_response(error)
        total_points = len(streams[0]["data"])

        computed = compute_intervals(blocks, total_points)

        interval_dicts = [
            {
                "type": iv.type,
                "label": iv.label,
                "start_index": iv.start_index,
                "end_index": iv.end_index,
            }
            for iv in computed
        ]

        from magma_cycling.workout_parser import Phase

        main_seconds = sum(b.duration_seconds for b in blocks if b.phase == Phase.MAIN_SET)
        cooldown_seconds = sum(b.duration_seconds for b in blocks if b.phase == Phase.COOLDOWN)
        prescription_seconds = sum(b.duration_seconds for b in blocks)
        warmup_absorbed = total_points - main_seconds - cooldown_seconds

        summary = {
            "mode": "auto",
            "dry_run": dry_run,
            "activity_id": activity_id,
            "session_id": session_id,
            "stream_points": total_points,
            "prescription_seconds": prescription_seconds,
            "warmup_absorbed": warmup_absorbed,
            "intervals_count": len(interval_dicts),
            "intervals": interval_dicts,
        }

        if dry_run:
            summary["message"] = "Preview only. Set dry_run=false to apply."
            return mcp_response(summary)

        with suppress_stdout_stderr():
            result = client.put_activity_intervals(activity_id, interval_dicts)
        summary["applied"] = True
        summary["result"] = result
        return mcp_response(summary)

    except Exception as e:
        error = {
            "error": f"Failed to apply workout intervals: {str(e)}",
            "activity_id": activity_id,
        }
        return mcp_response(error)
