"""Backfill historic wellness data (plan iso-config PR2bis, AC2 self-contained).

Iterates ``--since`` to ``--to`` (inclusive) day-by-day, fetches the
Intervals.icu wellness payload via :class:`IntervalsClient`, and writes
each day to ``<TRAINING_DATA_ROOT>/data/wellness/YYYY-MM-DD.json`` via
:func:`magma_cycling.wellness.archive.archive_wellness_day`.

Idempotent : days already archived are skipped (override with
``--force``). Volume estimate for 90 days ≈ 270 KB.

Usage::

    poetry run backfill-wellness --since 2026-02-10 --to 2026-05-10
    poetry run backfill-wellness --since 2026-02-10 --to 2026-05-10 --dry-run
    poetry run backfill-wellness --since 2026-02-10 --to 2026-05-10 --force
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

from magma_cycling.wellness import (
    archive_wellness_day,
    resolve_wellness_dir,
    wellness_archive_exists,
)

logger = logging.getLogger(__name__)


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date {s!r} (expected YYYY-MM-DD)") from exc


def _iter_days(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def backfill(
    since: date,
    to: date,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Run the backfill and return a counters summary.

    Returns:
        Dict with keys ``fetched``, ``written``, ``skipped``, ``failed``.
    """
    if since > to:
        raise ValueError(f"--since {since} must be <= --to {to}")

    from magma_cycling.config import create_intervals_client

    client = create_intervals_client()
    payload_by_date: dict[str, dict] = {}
    counters = {"fetched": 0, "written": 0, "skipped": 0, "failed": 0}

    # Single API call covering the whole range — Intervals.icu returns one entry per day.
    raw = client.get_wellness(oldest=since.isoformat(), newest=to.isoformat())
    counters["fetched"] = len(raw)
    for entry in raw:
        d = entry.get("id")
        if isinstance(d, str):
            payload_by_date[d] = entry

    for day in _iter_days(since, to):
        date_str = day.isoformat()
        if not force and wellness_archive_exists(date_str):
            counters["skipped"] += 1
            continue
        payload = payload_by_date.get(date_str)
        if payload is None:
            logger.warning("no wellness data for %s — skipping", date_str)
            counters["failed"] += 1
            continue
        if dry_run:
            counters["written"] += 1
            continue
        archive_wellness_day(date_str, payload)
        counters["written"] += 1

    return counters


def main() -> int:
    """CLI entry point: ``poetry run backfill-wellness``."""
    parser = argparse.ArgumentParser(
        prog="backfill-wellness",
        description="Backfill historic wellness data into training-logs/data/wellness/.",
    )
    parser.add_argument("--since", type=_parse_date, required=True, help="YYYY-MM-DD")
    parser.add_argument("--to", type=_parse_date, required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-write existing archives (default: skip).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + count without writing files.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    target_dir = resolve_wellness_dir()
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
