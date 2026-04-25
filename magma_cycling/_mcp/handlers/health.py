"""Health data handlers."""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import requests

from magma_cycling._mcp._utils import mcp_response, suppress_stdout_stderr
from magma_cycling.utils.intervals_scales import sleep_score_to_quality

if TYPE_CHECKING:
    from mcp.types import TextContent

__all__ = [
    "handle_health_auth_status",
    "handle_health_authorize",
    "handle_get_sleep",
    "handle_get_hrv",
    "handle_get_body_composition",
    "handle_get_readiness",
    "handle_sync_health_to_calendar",
    "handle_analyze_health_trends",
    "handle_enrich_session_health",
    "sync_health_to_calendar",
]


async def handle_health_auth_status(args: dict) -> list[TextContent]:
    """Check health provider OAuth authentication status."""
    with suppress_stdout_stderr():
        from magma_cycling.config import get_withings_config
        from magma_cycling.health import create_health_provider

        config = get_withings_config()
        provider = create_health_provider()
        provider_info = provider.get_provider_info()

        status = {
            "configured": config.is_configured(),
            "has_credentials": config.has_valid_credentials(),
            "provider_name": provider_info["provider"],
            "provider_class": type(provider).__name__,
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

            # Add token expiry info for diagnostics
            import time

            try:
                with open(config.credentials_path, encoding="utf-8") as f:
                    creds = json.load(f)
                token_expiry = creds.get("token_expiry", 0)
                now = time.time()
                status["access_token_expired"] = token_expiry <= now
                status["auto_refresh"] = "refresh_token present, auto-refresh on next API call"
            except Exception:
                pass

    return mcp_response(status, provider_info=provider_info)


async def handle_health_authorize(args: dict) -> list[TextContent]:
    """Handle health provider OAuth authorization flow."""
    with suppress_stdout_stderr():
        from magma_cycling.config import create_withings_client
        from magma_cycling.health import create_health_provider

        client = create_withings_client()
        provider = create_health_provider()
        provider_info = provider.get_provider_info()
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

    return mcp_response(result, provider_info=provider_info)


async def handle_get_sleep(args: dict) -> list[TextContent]:
    """Get sleep data via HealthProvider."""
    with suppress_stdout_stderr():
        from magma_cycling.health import create_health_provider

        provider = create_health_provider()
        provider_info = provider.get_provider_info()

        last_night_only = args.get("last_night_only", False)

        if last_night_only:
            sleep = provider.get_sleep_summary(date.today())
            result = {"last_night_sleep": sleep.model_dump() if sleep else None}

            if not sleep:
                result["message"] = "No sleep data available for last night"
        else:
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")

            if not start_date_str:
                end_date_val = date.today()
                start_date_val = end_date_val - timedelta(days=7)
            else:
                start_date_val = date.fromisoformat(start_date_str)
                end_date_val = date.fromisoformat(end_date_str) if end_date_str else date.today()

            sessions = provider.get_sleep_range(start_date_val, end_date_val)

            result = {
                "start_date": start_date_val.isoformat(),
                "end_date": end_date_val.isoformat(),
                "sleep_sessions": [s.model_dump() for s in sessions],
                "count": len(sessions),
            }

    return mcp_response(result, provider_info=provider_info, default=str)


async def handle_get_hrv(args: dict) -> list[TextContent]:
    """Get nocturnal HRV readings via HealthProvider."""
    with suppress_stdout_stderr():
        from magma_cycling.health import create_health_provider

        provider = create_health_provider()
        provider_info = provider.get_provider_info()

        last_night_only = args.get("last_night_only", False)

        if last_night_only:
            reading = provider.get_hrv_nocturnal(date.today())
            result = {"last_night_hrv": reading.model_dump() if reading else None}
            if not reading:
                result["message"] = "No HRV data available for last night"
        else:
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")

            if not start_date_str:
                end_date_val = date.today()
                start_date_val = end_date_val - timedelta(days=7)
            else:
                start_date_val = date.fromisoformat(start_date_str)
                end_date_val = date.fromisoformat(end_date_str) if end_date_str else date.today()

            readings = provider.get_hrv_range(start_date_val, end_date_val)

            result = {
                "start_date": start_date_val.isoformat(),
                "end_date": end_date_val.isoformat(),
                "readings": [r.model_dump() for r in readings],
                "count": len(readings),
            }

    return mcp_response(result, provider_info=provider_info, default=str)


async def handle_get_body_composition(args: dict) -> list[TextContent]:
    """Get body composition measurements via HealthProvider."""
    with suppress_stdout_stderr():
        from magma_cycling.health import create_health_provider

        provider = create_health_provider()
        provider_info = provider.get_provider_info()

        latest_only = args.get("latest_only", False)

        if latest_only:
            weight = provider.get_body_composition()
            result = {"latest_weight": weight.model_dump() if weight else None}

            if not weight:
                result["message"] = "No weight data available"
        else:
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")

            if not start_date_str:
                end_date_val = date.today()
                start_date_val = end_date_val - timedelta(days=30)
            else:
                start_date_val = date.fromisoformat(start_date_str)
                end_date_val = date.fromisoformat(end_date_str) if end_date_str else date.today()

            measurements = provider.get_body_composition_range(start_date_val, end_date_val)

            result = {
                "start_date": start_date_val.isoformat(),
                "end_date": end_date_val.isoformat(),
                "measurements": [m.model_dump() for m in measurements],
                "count": len(measurements),
            }

    return mcp_response(result, provider_info=provider_info, default=str)


async def handle_get_readiness(args: dict) -> list[TextContent]:
    """Evaluate training readiness via HealthProvider."""
    with suppress_stdout_stderr():
        from magma_cycling.health import create_health_provider

        provider = create_health_provider()
        provider_info = provider.get_provider_info()

        eval_date_str = args.get("date")
        eval_date = date.fromisoformat(eval_date_str) if eval_date_str else date.today()

        readiness = provider.get_readiness(eval_date)

        if not readiness:
            result = {
                "date": eval_date.isoformat(),
                "status": "no_data",
                "message": "No sleep data available for evaluation",
            }
        else:
            result = {
                "date": eval_date.isoformat(),
                "status": "evaluated",
                "readiness": readiness.model_dump(),
            }

            # Sleep fragmentation warning
            sleep = provider.get_sleep_summary(eval_date)
            seg_count = getattr(sleep, "segments_count", None)
            if sleep and isinstance(seg_count, int) and seg_count > 1 and sleep.segments_detail:
                detail = " + ".join(f"{s['start']}\u2192{s['end']}" for s in sleep.segments_detail)
                first_seg = sleep.segments_detail[0]
                dur_h = int(first_seg["duration_hours"])
                dur_m = int((first_seg["duration_hours"] % 1) * 60)
                result["sleep_fragmentation"] = (
                    f"Nuit multi-segments d\u00e9tect\u00e9e "
                    f"({sleep.segments_count} segments fusionn\u00e9s). "
                    f"L\u2019app mobile Withings peut afficher uniquement le "
                    f"premier segment ({dur_h}h{dur_m:02d}) "
                    f"\u2014 les donn\u00e9es Magma sont correctes ({detail})."
                )

    return mcp_response(result, provider_info=provider_info, default=str)


def _extract_422_detail(http_err: requests.exceptions.HTTPError) -> str:
    """Extract error detail from a 422 response body."""
    try:
        if http_err.response is not None:
            return http_err.response.text[:500]
    except Exception:
        pass
    return "no response body"


def _put_wellness_defensive(
    client: Any, date_str: str, wellness: dict[str, Any]
) -> dict[str, Any] | None:
    """PUT wellness with 422 fallback and 429 retry.

    On 422 (unknown fields): retry without custom fields (muscleMass, boneMass, bodyWater).
    On 429 (rate limit): exponential backoff (5s, 10s, 20s) up to 3 attempts.

    Returns None on success, or a diagnostic dict on failure.
    """
    custom_fields = ("muscleMass", "boneMass", "bodyWater")
    max_retries = 3
    base_delay = 5

    for attempt in range(max_retries):
        try:
            client.update_wellness(date_str, wellness)
            return None
        except requests.exceptions.HTTPError as http_err:
            status = http_err.response.status_code if http_err.response is not None else 0
            if status == 422:
                stripped = {k: v for k, v in wellness.items() if k not in custom_fields}
                if stripped:
                    try:
                        client.update_wellness(date_str, stripped)
                        return None
                    except requests.exceptions.HTTPError as retry_err:
                        return {
                            "stage": "422_retry_failed",
                            "original_payload": wellness,
                            "stripped_payload": stripped,
                            "retry_status": (
                                retry_err.response.status_code
                                if retry_err.response is not None
                                else 0
                            ),
                            "retry_detail": _extract_422_detail(retry_err),
                        }
                return {
                    "stage": "422_empty_after_strip",
                    "original_payload": wellness,
                }
            if status == 429 and attempt < max_retries - 1:
                wait = base_delay * (2**attempt)
                time.sleep(wait)
                continue
            raise
    return None


def sync_health_to_calendar(
    start_date: date,
    end_date: date | None = None,
    data_types: list[str] | None = None,
) -> dict:
    """Synchronize health data to training calendar wellness fields.

    Reusable synchronous function. Fetches data via HealthProvider, transforms,
    and PUTs to calendar with defensive 422/429 handling.

    Returns a result dict with synced_dates, errors, and status.
    """
    from magma_cycling.config import create_intervals_client
    from magma_cycling.health import create_health_provider

    provider = create_health_provider()
    intervals_client = create_intervals_client()

    end_date_val = end_date if end_date is not None else date.today()
    types = data_types or ["all"]

    sync_sleep = "all" in types or "sleep" in types
    sync_weight = "all" in types or "weight" in types
    sync_bp = "all" in types or "blood_pressure" in types

    synced_dates: list[str] = []
    errors: list[dict] = []

    # Fetch data via provider
    sleep_data_list = []
    weight_data_list = []
    bp_data_list = []

    if sync_sleep:
        sleep_data_list = [
            s.model_dump() for s in provider.get_sleep_range(start_date, end_date_val)
        ]

    if sync_weight:
        weight_data_list = [
            m.model_dump() for m in provider.get_body_composition_range(start_date, end_date_val)
        ]

    if sync_bp:
        bp_data_list = [
            bp.model_dump() for bp in provider.get_blood_pressure_range(start_date, end_date_val)
        ]

    # Create lookup dictionaries
    sleep_by_date = {str(s["date"]): s for s in sleep_data_list}
    weight_by_date = {str(w["date"]): w for w in weight_data_list}
    bp_by_date = {str(bp["date"]): bp for bp in bp_data_list}

    # Iterate through each date and sync
    current_date = start_date
    while current_date <= end_date_val:
        date_str = current_date.isoformat()
        has_data = False

        try:
            wellness: dict[str, Any] = {}

            # Update with sleep data
            if sync_sleep and date_str in sleep_by_date:
                sleep_info = sleep_by_date[date_str]
                wellness["sleepSecs"] = int(sleep_info["total_sleep_hours"] * 3600)
                quality = sleep_score_to_quality(sleep_info.get("sleep_score"))
                if quality is not None:
                    wellness["sleepQuality"] = quality
                if sleep_info.get("hr_min"):
                    wellness["restingHR"] = sleep_info["hr_min"]
                has_data = True

            # Update with weight data
            if sync_weight and date_str in weight_by_date:
                weight_info = weight_by_date[date_str]
                wellness["weight"] = weight_info["weight_kg"]
                if weight_info.get("muscle_mass_kg"):
                    wellness["muscleMass"] = weight_info["muscle_mass_kg"]
                if weight_info.get("bone_mass_kg"):
                    wellness["boneMass"] = weight_info["bone_mass_kg"]
                if weight_info.get("body_water_kg"):
                    wellness["bodyWater"] = weight_info["body_water_kg"]
                has_data = True

            # Update with blood pressure data
            if sync_bp and date_str in bp_by_date:
                bp_info = bp_by_date[date_str]
                wellness["systolic"] = bp_info["systolic"]
                wellness["diastolic"] = bp_info["diastolic"]
                has_data = True

            # Only update if we have data to sync
            if has_data:
                diag = _put_wellness_defensive(intervals_client, date_str, wellness)
                if diag is not None:
                    errors.append({"date": date_str, **diag})
                else:
                    synced_dates.append(date_str)

                # Throttle: avoid saturating Intervals.icu API
                time.sleep(1)

        except Exception as e:
            errors.append({"date": date_str, "error": str(e), "payload": wellness})

        current_date = current_date + timedelta(days=1)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date_val.isoformat(),
        "data_types": types,
        "synced_dates": synced_dates,
        "synced_count": len(synced_dates),
        "errors": errors,
        "status": "success" if not errors else "partial_success",
    }


async def handle_sync_health_to_calendar(args: dict) -> list[TextContent]:
    """Synchronize health data to training calendar wellness via HealthProvider."""
    with suppress_stdout_stderr():
        from magma_cycling.config import create_intervals_client
        from magma_cycling.health import create_health_provider

        start_date_val = date.fromisoformat(args["start_date"])
        end_date_str = args.get("end_date")
        end_date_val = date.fromisoformat(end_date_str) if end_date_str else None
        data_types = args.get("data_types", ["all"])

        provider = create_health_provider()
        client = create_intervals_client()

        result = sync_health_to_calendar(start_date_val, end_date_val, data_types)
        result["providers"] = {
            "health": provider.get_provider_info(),
            "calendar": client.get_provider_info(),
        }

    return mcp_response(result, provider_info=provider.get_provider_info())


async def handle_analyze_health_trends(args: dict) -> list[TextContent]:
    """Analyze health trends over time via HealthProvider."""
    with suppress_stdout_stderr():
        from magma_cycling.health import create_health_provider

        provider = create_health_provider()
        provider_info = provider.get_provider_info()

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
                return mcp_response(result, provider_info=provider_info)

            start_date_val = date.fromisoformat(start_date_str)
            end_date_val = date.fromisoformat(end_date_str)

        # Fetch data via provider → convert to dicts for analysis
        sleep_sessions = [
            s.model_dump() for s in provider.get_sleep_range(start_date_val, end_date_val)
        ]
        weight_measurements = [
            m.model_dump()
            for m in provider.get_body_composition_range(start_date_val, end_date_val)
        ]

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

    return mcp_response(result, provider_info=provider_info)


async def handle_enrich_session_health(args: dict) -> list[TextContent]:
    """Enrich training session with health metrics via HealthProvider."""
    with suppress_stdout_stderr():
        from magma_cycling.health import create_health_provider
        from magma_cycling.planning.control_tower import planning_tower

        week_id = args["week_id"]
        session_id = args["session_id"]
        auto_readiness_check = args.get("auto_readiness_check", True)

        provider = create_health_provider()
        provider_info = provider.get_provider_info()

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
                return mcp_response(result, provider_info=provider_info)

            # Get session date
            session_date = session.session_date

            # Get sleep from previous night
            sleep_date = session_date - timedelta(days=1)
            sleep_sessions = provider.get_sleep_range(sleep_date, session_date)

            sleep_data = sleep_sessions[-1] if sleep_sessions else None

            # Get latest weight
            weight = provider.get_body_composition()

            # Build health metrics dict (Session is a Pydantic model — no extra attrs)
            health_metrics = {}

            # Add sleep metrics
            if sleep_data:
                health_metrics["sleep_hours"] = sleep_data.total_sleep_hours
                health_metrics["sleep_score"] = sleep_data.sleep_score
                health_metrics["deep_sleep_minutes"] = sleep_data.deep_sleep_minutes

                # Evaluate readiness
                if auto_readiness_check:
                    readiness = provider.get_readiness(session_date)
                    if readiness:
                        health_metrics["training_readiness"] = readiness.recommended_intensity
                        health_metrics["ready_for_intense"] = readiness.ready_for_intense
                        health_metrics["veto_reasons"] = readiness.veto_reasons
                        health_metrics["recommendations"] = readiness.recommendations

            # Add weight
            if weight:
                health_metrics["weight_kg"] = weight.weight_kg

            result = {
                "week_id": week_id,
                "session_id": session_id,
                "session_date": str(session.session_date),
                "health_metrics_added": health_metrics,
                "status": "success",
            }

        # Push health data to calendar wellness (outside Control Tower lock)
        sync_to_calendar = args.get("sync_to_calendar", True)
        if sync_to_calendar and health_metrics:
            try:
                sync_result = sync_health_to_calendar(
                    start_date=session_date,
                    end_date=session_date,
                    data_types=["sleep", "weight"],
                )
                result["calendar_sync"] = {
                    "synced": bool(sync_result.get("synced_dates")),
                    "synced_dates": sync_result.get("synced_dates", []),
                    "errors": sync_result.get("errors", []),
                }
            except Exception as e:
                result["calendar_sync"] = {"synced": False, "error": str(e)}

    return mcp_response(result, provider_info=provider_info)
