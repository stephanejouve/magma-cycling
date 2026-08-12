"""Tests BT-025 pour l'archive streams cold + read-through cache + backfill.

Couvre :
- Archive : partitioning Q-K (heure locale, pas UTC), path structure,
  atomic gzip write, read+decompress, corruption gzip.
- Manifest : load/save atomic, add_entry idempotent, compute_sha256,
  verify_checksum, fallback safe sur manifest corrompu.
- IntervalsClient.get_activity_streams : nominal API OK, write-through
  best-effort si metadata fourni, ConnectionError/Timeout/HTTP 5xx →
  fallback lecture cache, HTTP 4xx propage sans fallback, cache miss +
  API down propage, write-through failure ne casse pas la réponse.
- Backfill script : itère activités, skip existing sauf --force, dry-run,
  reject invalid ranges.
"""

from __future__ import annotations

import gzip
import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from magma_cycling.api.intervals_client import IntervalsClient
from magma_cycling.scripts.backfill_streams import backfill
from magma_cycling.streams import archive as archive_mod
from magma_cycling.streams import (
    archive_activity_streams,
    load_manifest,
    partition_from_local_dt,
    read_activity_streams,
    save_manifest,
    streams_archive_exists,
    streams_archive_path,
)
from magma_cycling.streams.manifest import (
    add_manifest_entry,
    compute_sha256,
    verify_checksum,
)


@pytest.fixture
def streams_tmp_dir(tmp_path, monkeypatch):
    """Redirige resolve_streams_dir vers un tmp_path isolé + reset manifest cache."""
    monkeypatch.setattr(archive_mod, "resolve_streams_dir", lambda: tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Q-K critical: partitioning derives from local datetime, NOT container TZ
# ---------------------------------------------------------------------------


class TestPartitionQKAware:
    """Le partitionnement doit venir du start_date_local, pas de la TZ container."""

    def test_partition_summer_evening(self):
        dt = datetime.fromisoformat("2026-08-10T20:30:00")
        assert partition_from_local_dt(dt) == "2026/08"

    def test_partition_month_boundary_late_evening(self):
        """23:59 le 31 août LOCAL = août, pas septembre (même si container UTC voit sept)."""
        dt = datetime.fromisoformat("2026-08-31T23:59:00")
        assert partition_from_local_dt(dt) == "2026/08"

    def test_partition_year_boundary_late_evening(self):
        """31 déc 23:00 local = 2026/12 (même si UTC+1 → container UTC voit 2026/12 22:00 → 2027 aux passages critiques)."""
        dt = datetime.fromisoformat("2026-12-31T23:00:00")
        assert partition_from_local_dt(dt) == "2026/12"

    def test_partition_early_morning(self):
        dt = datetime.fromisoformat("2026-01-01T01:15:00")
        assert partition_from_local_dt(dt) == "2026/01"


# ---------------------------------------------------------------------------
# Archive path + write/read atomicity
# ---------------------------------------------------------------------------


class TestArchivePath:
    def test_path_structure(self, streams_tmp_dir):
        dt = datetime.fromisoformat("2026-08-10T20:30:00")
        path = streams_archive_path("i123456", dt)
        assert path == streams_tmp_dir / "2026" / "08" / "i123456.json.gz"

    def test_exists_reads_manifest(self, streams_tmp_dir):
        assert streams_archive_exists("i123456") is False
        archive_activity_streams(
            "i123456",
            [{"type": "watts", "data": [100, 150]}],
            start_date_local="2026-08-10T20:30:00",
        )
        assert streams_archive_exists("i123456") is True


class TestArchiveWriteRead:
    def test_write_creates_gzip_and_updates_manifest(self, streams_tmp_dir):
        streams = [
            {"type": "watts", "data": [100, 200, 300]},
            {"type": "hr", "data": [130, 140, 150]},
        ]
        path = archive_activity_streams(
            "i123456",
            streams,
            start_date_local="2026-08-10T20:30:00",
            start_date_utc="2026-08-10T18:30:00Z",
            duration_sec=3600,
            sport_type="Ride",
            session_id="S106-02",
        )
        assert path.is_file()
        # Content is gzip'd
        with gzip.open(path, "rb") as fh:
            decoded = json.loads(fh.read().decode("utf-8"))
        assert decoded == streams

        # Manifest updated
        manifest = load_manifest()
        assert "i123456" in manifest["activities"]
        entry = manifest["activities"]["i123456"]
        assert entry["path"] == "2026/08/i123456.json.gz"
        assert entry["start_date_local"] == "2026-08-10T20:30:00"
        assert entry["start_date_utc"] == "2026-08-10T18:30:00Z"
        assert entry["duration_sec"] == 3600
        assert entry["sport_type"] == "Ride"
        assert entry["session_id"] == "S106-02"
        assert entry["checksum_sha256"]

    def test_read_returns_decompressed(self, streams_tmp_dir):
        streams = [{"type": "watts", "data": [100, 200]}]
        archive_activity_streams("i123", streams, start_date_local="2026-08-10T20:30:00")
        assert read_activity_streams("i123") == streams

    def test_read_missing_returns_none(self, streams_tmp_dir):
        assert read_activity_streams("i999") is None

    def test_read_corrupted_gzip_returns_none_and_logs(self, streams_tmp_dir, caplog):
        # Create manifest entry pointing at a non-gzip file
        archive_activity_streams(
            "i123", [{"type": "watts", "data": [1]}], start_date_local="2026-08-10T20:30:00"
        )
        target = streams_tmp_dir / "2026" / "08" / "i123.json.gz"
        target.write_bytes(b"not a valid gzip")
        with caplog.at_level("WARNING"):
            assert read_activity_streams("i123") is None
        assert any("corrupted" in r.message for r in caplog.records)

    def test_invalid_start_date_raises(self, streams_tmp_dir):
        with pytest.raises(ValueError, match="ISO 8601"):
            archive_activity_streams("i123", [{"type": "watts"}], start_date_local="not-a-date")

    def test_rewrite_is_idempotent(self, streams_tmp_dir):
        """--force scenario: rewrite same activity_id overrides gracefully."""
        streams_v1 = [{"type": "watts", "data": [100]}]
        streams_v2 = [{"type": "watts", "data": [200]}]
        archive_activity_streams("i123", streams_v1, start_date_local="2026-08-10T20:30:00")
        archive_activity_streams("i123", streams_v2, start_date_local="2026-08-10T20:30:00")
        assert read_activity_streams("i123") == streams_v2
        # Manifest checksum updated
        manifest = load_manifest()
        assert len(manifest["activities"]) == 1


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------


class TestManifest:
    def test_load_missing_returns_empty(self, streams_tmp_dir):
        m = load_manifest()
        assert m["activities"] == {}
        assert m["version"] == "1.0"

    def test_load_corrupted_returns_empty_and_logs(self, streams_tmp_dir, caplog):
        (streams_tmp_dir / "manifest.json").write_text("{invalid json", encoding="utf-8")
        with caplog.at_level("WARNING"):
            m = load_manifest()
        assert m["activities"] == {}
        assert any("corrupted" in r.message for r in caplog.records)

    def test_load_invalid_schema_returns_empty(self, streams_tmp_dir, caplog):
        (streams_tmp_dir / "manifest.json").write_text('["not a dict"]', encoding="utf-8")
        with caplog.at_level("WARNING"):
            m = load_manifest()
        assert m["activities"] == {}

    def test_save_atomic(self, streams_tmp_dir):
        m = {"version": "1.0", "activities": {"i1": {"foo": "bar"}}}
        save_manifest(m)
        assert (streams_tmp_dir / "manifest.json").is_file()
        # No .tmp leftover
        assert not (streams_tmp_dir / "manifest.json.tmp").exists()

    def test_add_entry_idempotent(self, streams_tmp_dir):
        m = load_manifest()
        add_manifest_entry(
            m,
            activity_id="i1",
            start_date_local="2026-08-10T20:30:00",
            start_date_utc=None,
            duration_sec=3600,
            sport_type="Ride",
            session_id=None,
            path="2026/08/i1.json.gz",
            checksum_sha256="abc",
        )
        add_manifest_entry(
            m,
            activity_id="i1",
            start_date_local="2026-08-10T20:30:00",
            start_date_utc=None,
            duration_sec=3700,  # updated value
            sport_type="Ride",
            session_id=None,
            path="2026/08/i1.json.gz",
            checksum_sha256="def",
        )
        assert m["activities"]["i1"]["checksum_sha256"] == "def"
        assert m["activities"]["i1"]["duration_sec"] == 3700

    def test_compute_sha256(self, tmp_path):
        p = tmp_path / "sample.bin"
        p.write_bytes(b"hello world")
        # Precomputed SHA-256 for "hello world"
        assert (
            compute_sha256(p) == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        )

    def test_verify_checksum_ok(self, streams_tmp_dir):
        streams = [{"type": "watts", "data": [1, 2, 3]}]
        archive_activity_streams("i1", streams, start_date_local="2026-08-10T20:30:00")
        m = load_manifest()
        assert verify_checksum(m, "i1", streams_dir=streams_tmp_dir) is True

    def test_verify_checksum_missing_entry(self, streams_tmp_dir):
        m = load_manifest()
        assert verify_checksum(m, "i999", streams_dir=streams_tmp_dir) is False

    def test_verify_checksum_file_missing(self, streams_tmp_dir):
        archive_activity_streams("i1", [{"type": "watts"}], start_date_local="2026-08-10T20:30:00")
        (streams_tmp_dir / "2026" / "08" / "i1.json.gz").unlink()
        m = load_manifest()
        assert verify_checksum(m, "i1", streams_dir=streams_tmp_dir) is False

    def test_verify_checksum_mismatch(self, streams_tmp_dir):
        archive_activity_streams(
            "i1", [{"type": "watts", "data": [1]}], start_date_local="2026-08-10T20:30:00"
        )
        # Tamper with the file
        target = streams_tmp_dir / "2026" / "08" / "i1.json.gz"
        with gzip.open(target, "wb") as fh:
            fh.write(b'[{"type":"tampered"}]')
        m = load_manifest()
        assert verify_checksum(m, "i1", streams_dir=streams_tmp_dir) is False


# ---------------------------------------------------------------------------
# IntervalsClient.get_activity_streams cache integration
# ---------------------------------------------------------------------------


class TestIntervalsClientGetActivityStreamsCache:
    def _make_client(self):
        return IntervalsClient(athlete_id="iXXXXXX", api_key="test-key")

    def _mock_response(self, payload, status=200):
        response = MagicMock()
        response.status_code = status
        response.json.return_value = payload
        response.text = json.dumps(payload)
        response.raise_for_status = MagicMock()
        return response

    def test_nominal_api_ok_without_metadata_no_writethrough(self, streams_tmp_dir):
        """Backward compat: 9 call sites existants sans metadata → pas d'écriture cache."""
        client = self._make_client()
        payload = [{"type": "watts", "data": [100, 200]}]
        with patch.object(client.session, "get", return_value=self._mock_response(payload)):
            result = client.get_activity_streams("i123")
        assert result == payload
        assert streams_archive_exists("i123") is False

    def test_nominal_api_ok_with_metadata_writes_through(self, streams_tmp_dir):
        client = self._make_client()
        payload = [{"type": "watts", "data": [100, 200]}]
        metadata = {
            "start_date_local": "2026-08-10T20:30:00",
            "start_date_utc": "2026-08-10T18:30:00Z",
            "duration_sec": 3600,
            "sport_type": "Ride",
        }
        with patch.object(client.session, "get", return_value=self._mock_response(payload)):
            result = client.get_activity_streams("i123", activity_metadata=metadata)
        assert result == payload
        assert streams_archive_exists("i123") is True

    def test_connection_error_falls_back_to_cache(self, streams_tmp_dir, caplog):
        client = self._make_client()
        streams = [{"type": "watts", "data": [100]}]
        archive_activity_streams("i123", streams, start_date_local="2026-08-10T20:30:00")

        with patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("net down"),
        ):
            with caplog.at_level("WARNING"):
                result = client.get_activity_streams("i123")
        assert result == streams
        assert any("falling back to local cache" in r.message for r in caplog.records)

    def test_timeout_falls_back_to_cache(self, streams_tmp_dir):
        client = self._make_client()
        streams = [{"type": "watts", "data": [1]}]
        archive_activity_streams("i123", streams, start_date_local="2026-08-10T20:30:00")

        with patch.object(client.session, "get", side_effect=requests.exceptions.Timeout("slow")):
            result = client.get_activity_streams("i123")
        assert result == streams

    def test_http_500_falls_back_to_cache(self, streams_tmp_dir):
        client = self._make_client()
        streams = [{"type": "watts", "data": [1]}]
        archive_activity_streams("i123", streams, start_date_local="2026-08-10T20:30:00")

        response = MagicMock()
        response.status_code = 500
        error = requests.exceptions.HTTPError("500", response=response)
        response.raise_for_status.side_effect = error

        with patch.object(client.session, "get", return_value=response):
            result = client.get_activity_streams("i123")
        assert result == streams

    def test_http_401_does_not_fall_back(self, streams_tmp_dir):
        client = self._make_client()
        archive_activity_streams(
            "i123", [{"type": "watts", "data": [1]}], start_date_local="2026-08-10T20:30:00"
        )

        response = MagicMock()
        response.status_code = 401
        error = requests.exceptions.HTTPError("401", response=response)
        response.raise_for_status.side_effect = error

        with patch.object(client.session, "get", return_value=response):
            with pytest.raises(requests.exceptions.HTTPError, match="401"):
                client.get_activity_streams("i123")

    def test_cache_miss_propagates_original_error(self, streams_tmp_dir):
        client = self._make_client()
        # No archive
        with patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("net down"),
        ):
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get_activity_streams("i999")

    def test_writethrough_failure_does_not_break_api_response(self, streams_tmp_dir):
        client = self._make_client()
        payload = [{"type": "watts", "data": [1]}]
        metadata = {"start_date_local": "2026-08-10T20:30:00"}

        with (
            patch.object(client.session, "get", return_value=self._mock_response(payload)),
            patch(
                "magma_cycling.streams.archive_activity_streams",
                side_effect=OSError("disk full"),
            ),
        ):
            result = client.get_activity_streams("i123", activity_metadata=metadata)
        assert result == payload  # API response returned despite cache failure


# ---------------------------------------------------------------------------
# Backfill CLI logic
# ---------------------------------------------------------------------------


class TestBackfillStreams:
    def test_reject_reversed_range(self, streams_tmp_dir):
        with pytest.raises(ValueError, match="must be <="):
            backfill(date(2026, 8, 10), date(2026, 8, 5))

    def test_dry_run_counts_without_writing(self, streams_tmp_dir):
        activities = [
            {
                "id": "i1",
                "start_date_local": "2026-08-10T20:30:00",
                "moving_time": 3600,
                "type": "Ride",
            },
            {
                "id": "i2",
                "start_date_local": "2026-08-11T18:00:00",
                "moving_time": 1800,
                "type": "Ride",
            },
        ]
        mock_client = MagicMock()
        mock_client.get_activities.return_value = activities

        with patch("magma_cycling.config.create_intervals_client", return_value=mock_client):
            counters = backfill(date(2026, 8, 10), date(2026, 8, 11), dry_run=True)

        assert counters == {"fetched": 2, "written": 2, "skipped": 0, "failed": 0}
        # Nothing archived
        assert streams_archive_exists("i1") is False
        assert streams_archive_exists("i2") is False

    def test_write_activities(self, streams_tmp_dir):
        activities = [
            {
                "id": "i1",
                "start_date_local": "2026-08-10T20:30:00",
                "moving_time": 3600,
                "type": "Ride",
            },
        ]
        mock_client = MagicMock()
        mock_client.get_activities.return_value = activities
        mock_client.get_activity_streams.return_value = [{"type": "watts", "data": [100]}]

        with patch("magma_cycling.config.create_intervals_client", return_value=mock_client):
            counters = backfill(date(2026, 8, 10), date(2026, 8, 10))

        assert counters["written"] == 1
        assert streams_archive_exists("i1") is True

    def test_skip_existing_unless_force(self, streams_tmp_dir):
        activities = [
            {
                "id": "i1",
                "start_date_local": "2026-08-10T20:30:00",
                "moving_time": 3600,
                "type": "Ride",
            },
        ]
        archive_activity_streams(
            "i1", [{"type": "watts", "data": [1]}], start_date_local="2026-08-10T20:30:00"
        )

        mock_client = MagicMock()
        mock_client.get_activities.return_value = activities
        mock_client.get_activity_streams.return_value = [{"type": "watts", "data": [2]}]

        with patch("magma_cycling.config.create_intervals_client", return_value=mock_client):
            counters = backfill(date(2026, 8, 10), date(2026, 8, 10))
        assert counters == {"fetched": 1, "written": 0, "skipped": 1, "failed": 0}
        # Original value unchanged
        assert read_activity_streams("i1") == [{"type": "watts", "data": [1]}]

        # With --force
        with patch("magma_cycling.config.create_intervals_client", return_value=mock_client):
            counters = backfill(date(2026, 8, 10), date(2026, 8, 10), force=True)
        assert counters == {"fetched": 1, "written": 1, "skipped": 0, "failed": 0}
        assert read_activity_streams("i1") == [{"type": "watts", "data": [2]}]

    def test_activity_without_id_counted_failed(self, streams_tmp_dir):
        activities = [
            {"start_date_local": "2026-08-10T20:30:00"},  # no id
        ]
        mock_client = MagicMock()
        mock_client.get_activities.return_value = activities

        with patch("magma_cycling.config.create_intervals_client", return_value=mock_client):
            counters = backfill(date(2026, 8, 10), date(2026, 8, 10))
        assert counters["failed"] == 1
        assert counters["written"] == 0

    def test_stream_fetch_failure_counted_failed(self, streams_tmp_dir):
        activities = [
            {
                "id": "i1",
                "start_date_local": "2026-08-10T20:30:00",
                "moving_time": 3600,
                "type": "Ride",
            },
        ]
        mock_client = MagicMock()
        mock_client.get_activities.return_value = activities
        mock_client.get_activity_streams.side_effect = requests.exceptions.HTTPError("API down")

        with patch("magma_cycling.config.create_intervals_client", return_value=mock_client):
            counters = backfill(date(2026, 8, 10), date(2026, 8, 10))
        assert counters == {"fetched": 1, "written": 0, "skipped": 0, "failed": 1}
