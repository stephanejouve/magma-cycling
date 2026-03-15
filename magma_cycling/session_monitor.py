#!/usr/bin/env python3
"""
Session Monitor — event-driven post-session orchestration.

Polls every 20 min (via LaunchAgent StartInterval=1200s, window 6h-23h).
When the planned session is detected as completed on Intervals.icu,
triggers the full chain: daily-sync → adherence → PID → end-of-week (Sunday).

Each step runs in its own try/except so a failure does not block the chain.
Exit 0 in all cases (LaunchAgent should not retry on its own).

Author: Claude Code
Created: 2026-03-01
"""

import subprocess
from datetime import date, datetime

from magma_cycling.config import create_intervals_client
from magma_cycling.daily_sync import calculate_current_week_info
from magma_cycling.planning.control_tower import planning_tower
from magma_cycling.utils.cli import cli_main

PREFIX = "[session-monitor]"
POETRY = "/Users/stephanejouve/.local/bin/poetry"
PROJECT_DIR = "/Users/stephanejouve/magma-cycling"


def log(msg: str) -> None:
    """Print a timestamped log line."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"{PREFIX} {ts} - {msg}")


def run_command(label: str, args: list[str]) -> bool:
    """Run a subprocess command, return True on success."""
    log(f"Triggering {label}...")
    try:
        result = subprocess.run(args, cwd=PROJECT_DIR, timeout=600)
        if result.returncode == 0:
            log(f"{label}... OK")
            return True
        else:
            log(f"{label}... FAILED (exit {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        log(f"{label}... TIMEOUT")
        return False
    except Exception as e:
        log(f"{label}... ERROR ({e})")
        return False


def _get_event_cutoff(client: object, session_ids: list[str], today_str: str) -> int | None:
    """Get cutoff hour from the planned event's start time on Intervals.icu.

    Looks up today's events, finds the one matching an actionable session,
    parses start_date_local, and returns start_hour + 3 (buffer).

    Returns None if no matching event or no parseable time (caller uses fallback).
    """
    try:
        events = client.get_events(oldest=today_str, newest=today_str)
        for event in events:
            event_name = event.get("name", "")
            if any(sid in event_name for sid in session_ids):
                start_local = event.get("start_date_local", "")
                if "T" in start_local:
                    hour = int(start_local.split("T")[1].split(":")[0])
                    return min(hour + 3, 23)  # cap at 23h
        return None
    except Exception:
        return None


def _fallback_cutoff(day_of_week: int) -> int:
    """Static fallback cutoff when no event time is available.

    Saturday/Sunday: 14h (morning sessions).
    Weekdays: 21h (sessions between 17h-20h).
    """
    if day_of_week in (5, 6):
        return 14
    return 21


@cli_main
def main() -> int:
    """Entry point."""
    now = datetime.now()

    # Step 0: Check time window (6h-23h)
    if not (6 <= now.hour < 23):
        return 0

    today = date.today()
    week_id, start_date = calculate_current_week_info(today)

    # Step 1: Read today's planned session
    try:
        plan = planning_tower.read_week(week_id)
    except FileNotFoundError:
        log(f"No planning file for {week_id}, exit")
        return 0

    todays_sessions = [s for s in plan.planned_sessions if s.session_date == today]

    # Step 2: No session today
    if not todays_sessions:
        log("No session today, exit")
        return 0

    # Step 3: Classify sessions (supports double sessions)
    terminal = ("completed", "cancelled", "skipped", "rest_day")
    actionable = [s for s in todays_sessions if s.status not in terminal]
    completed_count = sum(1 for s in todays_sessions if s.status == "completed")
    session_ids = ", ".join(s.session_id for s in todays_sessions)

    # All sessions are in terminal state — nothing to do
    if not actionable:
        log(f"{session_ids} all terminal, already processed, exit")
        return 0

    # Step 4: Check Intervals.icu for completed cycling activities today
    try:
        client = create_intervals_client()
        date_str = today.isoformat()
        activities = client.get_activities(oldest=date_str, newest=date_str)
        cycling = [
            a
            for a in activities
            if a.get("type") in ("Ride", "VirtualRide") and not a.get("icu_ignore_time", False)
        ]
    except Exception as e:
        log(f"Error querying Intervals.icu: {e}")
        return 0

    # Step 5: Compare activities vs already-completed sessions
    # New activity = more activities on Intervals.icu than sessions marked completed
    if len(cycling) <= completed_count:
        waiting_ids = ", ".join(s.session_id for s in actionable)

        # Smart cutoff: read planned event time from Intervals.icu, add 3h buffer
        actionable_ids = [s.session_id for s in actionable]
        cutoff = _get_event_cutoff(client, actionable_ids, date_str)
        if cutoff is None:
            cutoff = _fallback_cutoff(today.weekday())

        if now.hour >= cutoff:
            log(
                f"{waiting_ids} no activity past cutoff ({cutoff}h), " f"stopping monitor for today"
            )
            return 0

        log(f"{waiting_ids} waiting ({len(cycling)} activities, {completed_count} completed)")
        return 0

    new_activity = cycling[completed_count]  # first unprocessed activity
    activity_id = new_activity.get("id", "?")
    log(f"Activity {activity_id} detected ({len(cycling)} activities, {completed_count} completed)")

    # Step 6: Pre-sync Withings → Intervals.icu
    run_command("withings-presync", [POETRY, "run", "withings-presync"])

    # Step 7a: Trigger daily-sync
    try:
        run_command(
            "daily-sync",
            [POETRY, "run", "daily-sync", "--send-email", "--ai-analysis", "--auto-servo"],
        )
    except Exception as e:
        log(f"daily-sync error: {e}")

    # Step 7b: Trigger adherence check
    try:
        run_command(
            "adherence",
            [
                POETRY,
                "run",
                "python",
                "scripts/monitoring/check_workout_adherence.py",
                "--weekly-alert",
            ],
        )
    except Exception as e:
        log(f"adherence error: {e}")

    # Step 7c: Trigger PID evaluation
    try:
        run_command(
            "pid-evaluation",
            [POETRY, "run", "pid-daily-evaluation", "--days-back", "7"],
        )
    except Exception as e:
        log(f"pid-evaluation error: {e}")

    # Step 7d: If Sunday, trigger end-of-week
    if today.weekday() == 6:
        log("Sunday detected, triggering end-of-week")
        try:
            run_command(
                "end-of-week",
                [
                    POETRY,
                    "run",
                    "end-of-week",
                    "--auto-calculate",
                    "--provider",
                    "mistral_api",
                    "--auto",
                ],
            )
        except Exception as e:
            log(f"end-of-week error: {e}")

    log("Done")
    return 0


if __name__ == "__main__":
    main()  # @cli_main handles exit codes
