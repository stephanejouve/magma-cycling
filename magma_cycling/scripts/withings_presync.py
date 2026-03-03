"""Pre-sync Withings health data to Intervals.icu wellness fields.

Standalone script for LaunchAgent (21h00, 30 min before daily-sync).
Also called by session_monitor before triggering daily-sync.

Exit 0 in all cases — LaunchAgent should not retry on its own.
"""

import sys
from datetime import date, datetime, timedelta

PREFIX = "[withings-presync]"


def log(msg: str) -> None:
    """Print a timestamped log line."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"{PREFIX} {ts} - {msg}")


def main() -> int:
    """Entry point."""
    try:
        from magma_cycling.config import get_withings_config

        config = get_withings_config()
        if not config.is_configured() or not config.has_valid_credentials():
            log("Withings not configured or no credentials, skip")
            return 0
    except Exception as e:
        log(f"Config check failed: {e}, skip")
        return 0

    today = date.today()
    yesterday = today - timedelta(days=1)

    log(f"Syncing {yesterday} → {today} (sleep, weight)")

    try:
        from magma_cycling._mcp.handlers.withings import sync_withings_to_intervals

        result = sync_withings_to_intervals(
            start_date=yesterday,
            end_date=today,
            data_types=["sleep", "weight"],
        )

        synced = result.get("synced_count", 0)
        errors = result.get("errors", [])
        log(f"Done: {synced} date(s) synced, {len(errors)} error(s)")

        if errors:
            for err in errors:
                log(f"  error: {err}")

    except Exception as e:
        log(f"Sync failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
