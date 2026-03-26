"""Remote activity data handlers (details, intervals, streams)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_get_activity_details",
    "handle_get_activity_intervals",
    "handle_get_activity_streams",
]


async def handle_get_activity_details(args: dict) -> list[TextContent]:
    """Get complete details for a completed activity from the training platform."""
    from magma_cycling.config import create_intervals_client

    activity_id = args["activity_id"]
    include_streams = args.get("include_streams", False)

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            _provider_info = client.get_provider_info()
            activity = client.get_activity(activity_id)

            average_watts = activity.get("average_watts")
            weighted_average_watts = activity.get("weighted_average_watts")

            streams = None
            need_streams = (
                average_watts is None
                or weighted_average_watts is None
                or activity.get("average_heartrate") is not None
            )

            if need_streams:
                try:
                    streams = client.get_activity_streams(activity_id)
                except Exception:
                    streams = None

            if (average_watts is None or weighted_average_watts is None) and streams:
                try:
                    watts_stream = next((s for s in streams if s["type"] == "watts"), None)

                    if watts_stream and watts_stream["data"]:
                        watts_data = watts_stream["data"]

                        if average_watts is None:
                            non_zero_watts = [w for w in watts_data if w > 0]
                            if non_zero_watts:
                                average_watts = round(sum(non_zero_watts) / len(non_zero_watts), 1)

                        if weighted_average_watts is None and len(watts_data) > 30:
                            rolling_avgs = []
                            for i in range(len(watts_data) - 29):
                                window = watts_data[i : i + 30]
                                rolling_avgs.append(sum(window) / 30)

                            if rolling_avgs:
                                fourth_powers = [p**4 for p in rolling_avgs]
                                avg_fourth = sum(fourth_powers) / len(fourth_powers)
                                weighted_average_watts = round(avg_fourth ** (1 / 4), 1)
                except Exception:
                    pass

            cardiovascular_decoupling = None
            if streams:
                try:
                    from magma_cycling.utils.decoupling import calculate_decoupling

                    watts_stream = next((s for s in streams if s["type"] == "watts"), None)
                    hr_stream = next((s for s in streams if s["type"] == "heartrate"), None)

                    if (
                        watts_stream
                        and hr_stream
                        and watts_stream["data"]
                        and hr_stream["data"]
                        and weighted_average_watts is not None
                    ):
                        cardiovascular_decoupling = calculate_decoupling(
                            watts_stream["data"], hr_stream["data"]
                        )
                except Exception:
                    pass

            # decoupling_api: Intervals.icu server-side (portion active only)
            # cardiovascular_decoupling: local split-half NP/HR (biased if warmup >15min)
            # Prefer decoupling_api for sessions with significant warmup/cooldown
            decoupling_api = activity.get("decoupling")

            result = {
                "id": activity.get("id"),
                "name": activity.get("name"),
                "start_date_local": activity.get("start_date_local"),
                "type": activity.get("type"),
                "moving_time": activity.get("moving_time"),
                "distance": activity.get("distance"),
                "total_elevation_gain": activity.get("total_elevation_gain"),
                "icu_training_load": activity.get("icu_training_load"),
                "icu_intensity": activity.get("icu_intensity"),
                "average_watts": average_watts,
                "weighted_average_watts": weighted_average_watts,
                "average_heartrate": activity.get("average_heartrate"),
                "average_cadence": activity.get("average_cadence"),
                "cardiovascular_decoupling": cardiovascular_decoupling,
                "decoupling_api": decoupling_api,
                "description": activity.get("description", ""),
                "paired_event_id": activity.get("paired_event_id"),
            }

            if include_streams:
                streams = client.get_activity_streams(activity_id)
                result["streams"] = [
                    {"type": s["type"], "data_points": len(s["data"])} for s in streams
                ]

        return mcp_response(result, provider_info=_provider_info)

    except Exception as e:
        error = {
            "error": f"Failed to get activity details: {str(e)}",
            "activity_id": activity_id,
        }
        return mcp_response(error)


async def handle_get_activity_intervals(args: dict) -> list[TextContent]:
    """Get aggregated interval/lap data for a completed activity."""
    from magma_cycling.config import create_intervals_client

    activity_id = args["activity_id"]

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            _provider_info = client.get_provider_info()
            raw_intervals = client.get_activity_intervals(activity_id)

        keep_fields = {
            "type",
            "label",
            "start_index",
            "end_index",
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

        intervals = []
        total_elapsed = 0
        for iv in raw_intervals:
            filtered = {k: v for k, v in iv.items() if k in keep_fields and v is not None}
            intervals.append(filtered)
            total_elapsed += iv.get("elapsed_time", 0) or 0

        result = {
            "activity_id": activity_id,
            "total_intervals": len(intervals),
            "total_elapsed_seconds": total_elapsed,
            "intervals": intervals,
        }

        return mcp_response(result, provider_info=_provider_info)

    except Exception as e:
        error = {
            "error": f"Failed to get activity intervals: {str(e)}",
            "activity_id": activity_id,
        }
        return mcp_response(error)


async def handle_get_activity_streams(args: dict) -> list[TextContent]:
    """Get raw time-series stream data for an activity with optional slicing and type filtering."""
    from magma_cycling.config import create_intervals_client

    activity_id = args["activity_id"]
    requested_types = args.get("types")
    start_index = args.get("start_index", 0)
    end_index = args.get("end_index")

    try:
        with suppress_stdout_stderr():
            client = create_intervals_client()
            _provider_info = client.get_provider_info()
            streams = client.get_activity_streams(activity_id)

        if not streams:
            error = {
                "error": f"No stream data found for activity {activity_id}",
                "activity_id": activity_id,
            }
            return mcp_response(error)

        available_stream_types = [s["type"] for s in streams]

        missing_types = []
        if requested_types:
            available_set = set(available_stream_types)
            missing_types = [t for t in requested_types if t not in available_set]
            streams = [s for s in streams if s["type"] in set(requested_types)]

        total_data_points = len(streams[0]["data"]) if streams else 0

        start_index = max(0, start_index)
        if end_index is None:
            end_index = total_data_points
        end_index = max(start_index, min(end_index, total_data_points))

        result_streams = []
        for stream in streams:
            data = stream["data"][start_index:end_index]
            stats = {}
            if data:
                valid = [v for v in data if v is not None]
                if valid:
                    stats["min"] = min(valid)
                    stats["max"] = max(valid)
                    stats["avg"] = round(sum(valid) / len(valid), 2)
                    non_zero = [v for v in valid if v != 0]
                    stats["non_zero_count"] = len(non_zero)
                    stats["non_zero_avg"] = (
                        round(sum(non_zero) / len(non_zero), 2) if non_zero else 0
                    )
                stats["null_count"] = len(data) - len(valid) if valid else len(data)
            result_streams.append(
                {
                    "type": stream["type"],
                    "data_points": len(data),
                    "stats": stats,
                    "data": data,
                }
            )

        result = {
            "activity_id": activity_id,
            "total_data_points": total_data_points,
            "slice": {
                "start_index": start_index,
                "end_index": end_index,
                "length": end_index - start_index,
            },
            "available_stream_types": available_stream_types,
            "streams": result_streams,
        }

        if missing_types:
            result["missing_types"] = missing_types

        return mcp_response(result, provider_info=_provider_info)

    except Exception as e:
        error = {
            "error": f"Failed to get activity streams: {str(e)}",
            "activity_id": activity_id,
        }
        return mcp_response(error)
