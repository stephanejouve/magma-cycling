"""Withings health data handlers."""

import json
from datetime import date, timedelta

from mcp.types import TextContent

from magma_cycling._mcp._utils import suppress_stdout_stderr

__all__ = [
    "handle_withings_auth_status",
    "handle_withings_authorize",
    "handle_withings_get_sleep",
    "handle_withings_get_weight",
    "handle_withings_get_readiness",
    "handle_withings_sync_to_intervals",
    "handle_withings_analyze_trends",
    "handle_withings_enrich_session",
]


async def handle_withings_auth_status(args: dict) -> list[TextContent]:
    """Check Withings OAuth authentication status."""
    with suppress_stdout_stderr():
        from magma_cycling.config import get_withings_config

        config = get_withings_config()

        status = {
            "configured": config.is_configured(),
            "has_credentials": config.has_valid_credentials(),
        }

        if not config.is_configured():
            status["message"] = "Withings not configured"
            status["next_steps"] = (
                "Set WITHINGS_CLIENT_ID and WITHINGS_CLIENT_SECRET environment variables"
            )
        elif not config.has_valid_credentials():
            status["message"] = "Not authenticated"
            status["next_steps"] = (
                "Run 'withings-authorize' tool to get authorization URL, "
                "then call again with authorization_code parameter"
            )
        else:
            status["message"] = "Authenticated and ready"
            status["credentials_path"] = str(config.credentials_path)

    return [TextContent(type="text", text=json.dumps(status, indent=2))]


async def handle_withings_authorize(args: dict) -> list[TextContent]:
    """Handle Withings OAuth authorization flow."""
    with suppress_stdout_stderr():
        from magma_cycling.config import create_withings_client

        client = create_withings_client()
        authorization_code = args.get("authorization_code")

        if not authorization_code:
            # Step 1: Return authorization URL
            auth_url = client.get_authorization_url()

            result = {
                "step": "authorization_required",
                "authorization_url": auth_url,
                "instructions": [
                    "1. Visit the authorization URL above in your browser",
                    "2. Authorize the application",
                    "3. Copy the authorization code from the callback URL",
                    "4. Call this tool again with authorization_code parameter",
                ],
                "note": (
                    "Alternatively, run the setup script: "
                    "python -m magma_cycling.scripts.setup_withings"
                ),
            }
        else:
            # Step 2: Exchange code for tokens
            try:
                tokens = client.exchange_code(authorization_code)

                result = {
                    "step": "authorization_complete",
                    "status": "success",
                    "message": "✓ Successfully authenticated with Withings",
                    "user_id": tokens["user_id"],
                    "credentials_saved": True,
                }
            except Exception as e:
                result = {"step": "authorization_failed", "status": "error", "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_get_sleep(args: dict) -> list[TextContent]:
    """Get sleep data from Withings."""
    with suppress_stdout_stderr():
        from magma_cycling.config import create_withings_client

        client = create_withings_client()

        last_night_only = args.get("last_night_only", False)

        if last_night_only:
            # Get last night's sleep
            sleep_data = client.get_last_night_sleep()
            result = {"last_night_sleep": sleep_data if sleep_data else None}

            if not sleep_data:
                result["message"] = "No sleep data available for last night"
        else:
            # Get sleep for date range
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")

            if not start_date_str:
                # Default: last 7 days
                end_date_val = date.today()
                start_date_val = end_date_val - timedelta(days=7)
            else:
                start_date_val = date.fromisoformat(start_date_str)
                end_date_val = date.fromisoformat(end_date_str) if end_date_str else date.today()

            sleep_sessions = client.get_sleep(start_date_val, end_date_val)

            result = {
                "start_date": start_date_val.isoformat(),
                "end_date": end_date_val.isoformat(),
                "sleep_sessions": sleep_sessions,
                "count": len(sleep_sessions),
            }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_get_weight(args: dict) -> list[TextContent]:
    """Get weight measurements from Withings."""
    with suppress_stdout_stderr():
        from magma_cycling.config import create_withings_client

        client = create_withings_client()

        latest_only = args.get("latest_only", False)

        if latest_only:
            # Get latest weight
            weight_data = client.get_latest_weight()
            result = {"latest_weight": weight_data if weight_data else None}

            if not weight_data:
                result["message"] = "No weight data available"
        else:
            # Get weight for date range
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")

            if not start_date_str:
                # Default: last 30 days
                end_date_val = date.today()
                start_date_val = end_date_val - timedelta(days=30)
            else:
                start_date_val = date.fromisoformat(start_date_str)
                end_date_val = date.fromisoformat(end_date_str) if end_date_str else date.today()

            measurements = client.get_measurements(
                start_date_val, end_date_val, measure_types=[1, 6, 8, 76, 88]
            )

            result = {
                "start_date": start_date_val.isoformat(),
                "end_date": end_date_val.isoformat(),
                "measurements": measurements,
                "count": len(measurements),
            }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_get_readiness(args: dict) -> list[TextContent]:
    """Evaluate training readiness based on health metrics."""
    with suppress_stdout_stderr():
        from magma_cycling.config import create_withings_client

        client = create_withings_client()

        eval_date_str = args.get("date")
        eval_date = date.fromisoformat(eval_date_str) if eval_date_str else date.today()

        # Get last night's sleep
        sleep_data = client.get_last_night_sleep()

        if not sleep_data:
            result = {
                "date": eval_date.isoformat(),
                "status": "no_data",
                "message": "No sleep data available for evaluation",
            }
        else:
            # Evaluate readiness
            readiness = client.evaluate_training_readiness(sleep_data)

            # Get latest weight for context
            weight_data = client.get_latest_weight()
            if weight_data:
                readiness["weight_kg"] = weight_data["weight_kg"]

            result = {
                "date": eval_date.isoformat(),
                "status": "evaluated",
                "readiness": readiness,
            }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_sync_to_intervals(args: dict) -> list[TextContent]:
    """Synchronize Withings data to Intervals.icu wellness."""
    with suppress_stdout_stderr():
        from magma_cycling.config import create_intervals_client, create_withings_client

        withings_client = create_withings_client()
        intervals_client = create_intervals_client()

        start_date_str = args["start_date"]
        end_date_str = args.get("end_date")
        data_types = args.get("data_types", ["all"])

        start_date_val = date.fromisoformat(start_date_str)
        end_date_val = date.fromisoformat(end_date_str) if end_date_str else date.today()

        # Determine what to sync
        sync_sleep = "all" in data_types or "sleep" in data_types
        sync_weight = "all" in data_types or "weight" in data_types

        synced_dates = []
        errors = []

        # Fetch Withings data
        sleep_data_list = []
        weight_data_list = []

        if sync_sleep:
            sleep_data_list = withings_client.get_sleep(start_date_val, end_date_val)

        if sync_weight:
            weight_data_list = withings_client.get_measurements(start_date_val, end_date_val)

        # Create lookup dictionaries
        sleep_by_date = {s["date"]: s for s in sleep_data_list}
        weight_by_date = {w["date"]: w for w in weight_data_list}

        # Iterate through each date and sync
        current_date = start_date_val
        while current_date <= end_date_val:
            date_str = current_date.isoformat()

            try:
                # Get current wellness data for this date
                wellness = intervals_client.get_wellness(date_str)

                if wellness is None:
                    wellness = {}

                # Update with sleep data
                if sync_sleep and date_str in sleep_by_date:
                    sleep_info = sleep_by_date[date_str]
                    wellness["sleepSecs"] = int(sleep_info["total_sleep_hours"] * 3600)
                    wellness["sleepQuality"] = sleep_info.get("sleep_score")

                # Update with weight data
                if sync_weight and date_str in weight_by_date:
                    weight_info = weight_by_date[date_str]
                    wellness["weight"] = weight_info["weight_kg"]

                # Only update if we have data to sync
                if date_str in sleep_by_date or date_str in weight_by_date:
                    intervals_client.update_wellness(date_str, wellness)
                    synced_dates.append(date_str)

            except Exception as e:
                errors.append({"date": date_str, "error": str(e)})

            current_date = current_date + timedelta(days=1)

        result = {
            "start_date": start_date_val.isoformat(),
            "end_date": end_date_val.isoformat(),
            "data_types": data_types,
            "synced_dates": synced_dates,
            "synced_count": len(synced_dates),
            "errors": errors,
            "status": "success" if not errors else "partial_success",
        }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_analyze_trends(args: dict) -> list[TextContent]:
    """Analyze health trends over time."""
    with suppress_stdout_stderr():
        from magma_cycling.config import create_withings_client

        client = create_withings_client()

        period = args.get("period", "week")

        if period == "week":
            end_date_val = date.today()
            start_date_val = end_date_val - timedelta(days=7)
        elif period == "month":
            end_date_val = date.today()
            start_date_val = end_date_val - timedelta(days=30)
        else:  # custom
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")

            if not start_date_str or not end_date_str:
                result = {
                    "error": "start_date and end_date required for custom period",
                    "status": "error",
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            start_date_val = date.fromisoformat(start_date_str)
            end_date_val = date.fromisoformat(end_date_str)

        # Fetch data
        sleep_sessions = client.get_sleep(start_date_val, end_date_val)
        weight_measurements = client.get_measurements(start_date_val, end_date_val)

        # Analyze sleep trends
        total_nights = len(sleep_sessions)

        if total_nights > 0:
            total_sleep_hours = sum(s["total_sleep_hours"] for s in sleep_sessions)
            avg_sleep_hours = total_sleep_hours / total_nights

            sleep_scores = [s["sleep_score"] for s in sleep_sessions if s.get("sleep_score")]
            avg_sleep_score = sum(sleep_scores) / len(sleep_scores) if sleep_scores else None

            nights_above_7h = sum(1 for s in sleep_sessions if s["total_sleep_hours"] >= 7)

            # Calculate sleep debt (assume 7h target)
            sleep_debt_hours = (7 * total_nights) - total_sleep_hours
        else:
            avg_sleep_hours = 0
            avg_sleep_score = None
            nights_above_7h = 0
            sleep_debt_hours = 0

        # Analyze weight trends
        if weight_measurements:
            weight_start = weight_measurements[0]["weight_kg"]
            weight_end = weight_measurements[-1]["weight_kg"]
            weight_delta = weight_end - weight_start
        else:
            weight_start = None
            weight_end = None
            weight_delta = None

        # Determine status
        if avg_sleep_hours >= 7.5 and nights_above_7h / max(total_nights, 1) >= 0.85:
            status = "optimal"
        elif avg_sleep_hours >= 6.5:
            status = "adequate"
        elif avg_sleep_hours >= 5.5:
            status = "debt"
        else:
            status = "critical"

        # Generate alerts
        alerts = []
        if sleep_debt_hours > 7:
            alerts.append(f"Sleep debt: {sleep_debt_hours:.1f}h over {total_nights} nights")
        if avg_sleep_hours < 6.5:
            alerts.append(f"Low average sleep: {avg_sleep_hours:.1f}h/night")
        if weight_delta and abs(weight_delta) > 2:
            alerts.append(f"Significant weight change: {weight_delta:+.1f} kg")

        result = {
            "period": period,
            "start_date": start_date_val.isoformat(),
            "end_date": end_date_val.isoformat(),
            "sleep_analysis": {
                "avg_sleep_hours": round(avg_sleep_hours, 2),
                "avg_sleep_score": round(avg_sleep_score, 1) if avg_sleep_score else None,
                "nights_above_7h": nights_above_7h,
                "total_nights": total_nights,
                "sleep_debt_hours": round(sleep_debt_hours, 1),
            },
            "weight_analysis": {
                "weight_start_kg": weight_start,
                "weight_end_kg": weight_end,
                "weight_delta_kg": round(weight_delta, 2) if weight_delta else None,
            },
            "status": status,
            "alerts": alerts,
        }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_withings_enrich_session(args: dict) -> list[TextContent]:
    """Enrich training session with Withings health metrics."""
    with suppress_stdout_stderr():
        from magma_cycling.config import create_withings_client
        from magma_cycling.planning.control_tower import planning_tower

        week_id = args["week_id"]
        session_id = args["session_id"]
        auto_readiness_check = args.get("auto_readiness_check", True)

        withings_client = create_withings_client()

        # Load session
        with planning_tower.modify_week(
            week_id, requesting_script="mcp-server", reason="Enrich session with Withings data"
        ) as plan:
            # Find session
            session = None
            for s in plan.planned_sessions:
                if s.session_id == session_id:
                    session = s
                    break

            if not session:
                result = {
                    "error": f"Session {session_id} not found in week {week_id}",
                    "status": "error",
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            # Get session date
            session_date = date.fromisoformat(session.date)

            # Get sleep from previous night
            sleep_date = session_date - timedelta(days=1)
            sleep_sessions = withings_client.get_sleep(sleep_date, session_date)

            sleep_data = sleep_sessions[-1] if sleep_sessions else None

            # Get latest weight
            weight_data = withings_client.get_latest_weight()

            # Initialize health_metrics if not present
            if not hasattr(session, "health_metrics"):
                session.health_metrics = {}

            # Add sleep metrics
            if sleep_data:
                session.health_metrics["sleep_hours"] = sleep_data["total_sleep_hours"]
                session.health_metrics["sleep_score"] = sleep_data.get("sleep_score")
                session.health_metrics["deep_sleep_minutes"] = sleep_data.get("deep_sleep_minutes")

                # Evaluate readiness
                if auto_readiness_check:
                    readiness = withings_client.evaluate_training_readiness(sleep_data)
                    session.health_metrics["training_readiness"] = readiness[
                        "recommended_intensity"
                    ]
                    session.health_metrics["ready_for_intense"] = readiness["ready_for_intense"]
                    session.health_metrics["veto_reasons"] = readiness["veto_reasons"]
                    session.health_metrics["recommendations"] = readiness["recommendations"]

            # Add weight
            if weight_data:
                session.health_metrics["weight_kg"] = weight_data["weight_kg"]

            result = {
                "week_id": week_id,
                "session_id": session_id,
                "session_date": session.date,
                "health_metrics_added": session.health_metrics,
                "status": "success",
            }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
