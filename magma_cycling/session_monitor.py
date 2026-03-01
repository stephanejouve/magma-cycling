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
import sys
from datetime import date, datetime

from magma_cycling.config import create_intervals_client
from magma_cycling.daily_sync import calculate_current_week_info
from magma_cycling.planning.control_tower import planning_tower

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

    session = todays_sessions[0]
    sid = session.session_id
    status = session.status

    # Step 3: Already processed by a previous run
    if status == "completed":
        log(f"{sid} status=completed, already processed, exit")
        return 0

    # Step 4: Session cancelled/skipped/rest_day — nothing to do
    if status in ("cancelled", "skipped", "rest_day"):
        log(f"{sid} status={status}, exit")
        return 0

    # Step 5: Check Intervals.icu for completed cycling activity today
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

    # Step 6: No activity yet — wait for next poll
    if not cycling:
        log(f"{sid} status={status}, no activity found, waiting")
        return 0

    activity = cycling[0]
    activity_id = activity.get("id", "?")
    log(f"Activity {activity_id} detected for {sid}")

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
    sys.exit(main())
