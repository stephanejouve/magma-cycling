"""Tests for the backfill-wellness CLI (PR2bis plan iso-config)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling.config.data_repo import LEGACY_ROOT_ENV, ROOT_ENV, WELLNESS_SUBDIR
from magma_cycling.scripts.backfill_wellness import backfill
from magma_cycling.wellness import wellness_archive_exists, wellness_archive_path


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for v in (ROOT_ENV, LEGACY_ROOT_ENV):
        monkeypatch.delenv(v, raising=False)


def _fake_client(payloads: list[dict]) -> MagicMock:
    client = MagicMock()
    client.get_wellness.return_value = payloads
    return client


class TestBackfill:
    def test_writes_one_file_per_day(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        payloads = [
            {"id": "2026-05-12", "ctl": 40},
            {"id": "2026-05-13", "ctl": 41},
            {"id": "2026-05-14", "ctl": 42},
        ]
        with patch(
            "magma_cycling.config.create_intervals_client", return_value=_fake_client(payloads)
        ):
            counters = backfill(date(2026, 5, 12), date(2026, 5, 14))
        assert counters["fetched"] == 3
        assert counters["written"] == 3
        assert counters["skipped"] == 0
        assert counters["failed"] == 0
        for d in ("2026-05-12", "2026-05-13", "2026-05-14"):
            assert wellness_archive_exists(d)

    def test_skips_existing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        # Pre-populate one day
        wellness_dir = tmp_path / WELLNESS_SUBDIR
        wellness_dir.mkdir(parents=True)
        (wellness_dir / "2026-05-13.json").write_text("{}", encoding="utf-8")

        payloads = [
            {"id": "2026-05-12", "ctl": 40},
            {"id": "2026-05-13", "ctl": 41},  # ignored — file exists
            {"id": "2026-05-14", "ctl": 42},
        ]
        with patch(
            "magma_cycling.config.create_intervals_client", return_value=_fake_client(payloads)
        ):
            counters = backfill(date(2026, 5, 12), date(2026, 5, 14))
        assert counters["written"] == 2
        assert counters["skipped"] == 1

    def test_force_overwrites(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        target = wellness_archive_path("2026-05-13")
        target.parent.mkdir(parents=True)
        target.write_text("OLD", encoding="utf-8")

        payloads = [{"id": "2026-05-13", "ctl": 99}]
        with patch(
            "magma_cycling.config.create_intervals_client", return_value=_fake_client(payloads)
        ):
            counters = backfill(date(2026, 5, 13), date(2026, 5, 13), force=True)
        assert counters["written"] == 1
        assert counters["skipped"] == 0
        assert "OLD" not in target.read_text(encoding="utf-8")

    def test_dry_run_does_not_write(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        payloads = [{"id": "2026-05-13", "ctl": 41}]
        with patch(
            "magma_cycling.config.create_intervals_client", return_value=_fake_client(payloads)
        ):
            counters = backfill(date(2026, 5, 13), date(2026, 5, 13), dry_run=True)
        assert counters["written"] == 1  # accounted as would-write
        assert not wellness_archive_exists("2026-05-13")

    def test_missing_day_counted_as_failed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        # API returns only 2 of the 3 days
        payloads = [
            {"id": "2026-05-12", "ctl": 40},
            {"id": "2026-05-14", "ctl": 42},
        ]
        with patch(
            "magma_cycling.config.create_intervals_client", return_value=_fake_client(payloads)
        ):
            counters = backfill(date(2026, 5, 12), date(2026, 5, 14))
        assert counters["written"] == 2
        assert counters["failed"] == 1
        assert not wellness_archive_exists("2026-05-13")

    def test_invalid_date_range_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(ROOT_ENV, str(tmp_path))
        with pytest.raises(ValueError, match="must be"):
            backfill(date(2026, 5, 14), date(2026, 5, 12))
