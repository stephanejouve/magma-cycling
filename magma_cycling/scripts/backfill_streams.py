"""Backfill historic activity streams into training-logs/data/streams/ (BT-025).

Itère les activités Intervals.icu de ``--since`` à ``--to`` (inclusifs),
fetch les streams de chacune via :class:`IntervalsClient`, et archive
sous ``<TRAINING_DATA_ROOT>/data/streams/YYYY/MM/<activity_id>.json.gz``
avec mise à jour du manifest.

Idempotent : activités déjà indexées dans le manifest sont skippées
(override avec ``--force``). La partition YYYY/MM est calculée sur
``start_date_local`` de l'activité (Q-K : jamais dérivée de la TZ
container prod qui tourne UTC).

Usage::

    poetry run backfill-streams --since 2026-05-01 --to 2026-08-31
    poetry run backfill-streams --since 2026-05-01 --to 2026-08-31 --dry-run
    poetry run backfill-streams --since 2026-05-01 --to 2026-08-31 --force
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from magma_cycling.streams import (
    archive_activity_streams,
    resolve_streams_dir,
    streams_archive_exists,
)

logger = logging.getLogger(__name__)


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date {s!r} (expected YYYY-MM-DD)") from exc


def backfill(
    since: date,
    to: date,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Run the backfill and return a counters summary.

    Args:
        since: Start date (inclusive).
        to: End date (inclusive).
        force: If True, re-archive activities already in the manifest.
        dry_run: If True, count without writing.

    Returns:
        Dict with keys ``fetched``, ``written``, ``skipped``, ``failed``.
    """
    if since > to:
        raise ValueError(f"--since {since} must be <= --to {to}")

    from magma_cycling.config import create_intervals_client

    client = create_intervals_client()
    counters = {"fetched": 0, "written": 0, "skipped": 0, "failed": 0}

    activities = client.get_activities(oldest=since.isoformat(), newest=to.isoformat())
    counters["fetched"] = len(activities)
    logger.info("fetched %d activities in range [%s, %s]", len(activities), since, to)

    for activity in activities:
        activity_id = str(activity.get("id") or "")
        start_date_local = activity.get("start_date_local")
        if not activity_id or not start_date_local:
            logger.warning("activity missing id or start_date_local — skipped: %r", activity)
            counters["failed"] += 1
            continue

        if not force and streams_archive_exists(activity_id):
            counters["skipped"] += 1
            continue

        if dry_run:
            counters["written"] += 1
            continue

        try:
            streams = client.get_activity_streams(activity_id)
        except Exception as exc:  # noqa: BLE001 — backfill continues on per-activity fail
            logger.warning("streams fetch failed for %s (%s) — skipped", activity_id, exc)
            counters["failed"] += 1
            continue

        try:
            archive_activity_streams(
                activity_id,
                streams,
                start_date_local=start_date_local,
                start_date_utc=activity.get("start_date"),
                duration_sec=activity.get("moving_time") or activity.get("elapsed_time"),
                sport_type=activity.get("type") or activity.get("sport"),
                session_id=None,  # weekly-planner association out of scope for backfill
            )
            counters["written"] += 1
        except (OSError, ValueError) as exc:
            logger.warning("archive failed for %s (%s) — skipped", activity_id, exc)
            counters["failed"] += 1

    return counters


def main() -> int:
    """CLI entry point: ``poetry run backfill-streams``."""
    parser = argparse.ArgumentParser(
        prog="backfill-streams",
        description="Backfill historic activity streams into training-logs/data/streams/.",
    )
    parser.add_argument("--since", type=_parse_date, required=True, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--to", type=_parse_date, required=True, help="YYYY-MM-DD (inclusive)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-archive activities already in the manifest (default: skip).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + count without writing files.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    target_dir = resolve_streams_dir()
    print(f"📁 archive dir: {target_dir}", file=sys.stderr)
    print(f"📅 range: {args.since} → {args.to}", file=sys.stderr)
    if args.dry_run:
        print("ℹ️  dry-run: no files written", file=sys.stderr)

    try:
        counters = backfill(args.since, args.to, force=args.force, dry_run=args.dry_run)
    except (ValueError, RuntimeError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    print(
        f"✅ done — fetched={counters['fetched']} written={counters['written']} "
        f"skipped={counters['skipped']} failed={counters['failed']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
