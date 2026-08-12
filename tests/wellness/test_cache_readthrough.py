"""Tests BT-023 pour le cache read-through wellness.

Couvre :
- Écriture cache : archive_wellness_payload alimente training-logs/data/wellness/.
- Lecture cache : read_wellness_day + read_wellness_range récupèrent l'archive.
- Fallback IntervalsClient : ConnectionError / Timeout / HTTP 5xx → cache local.
- Nominal préservé : API OK → payload retourné + cache alimenté (best-effort).
- Auth failure (401/403) : PAS de fallback (surface l'erreur telle quelle).
- Cache vide + API down : exception d'origine propagée.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from magma_cycling.api.intervals_client import IntervalsClient
from magma_cycling.wellness import (
    archive_wellness_day,
    archive_wellness_payload,
    read_wellness_day,
    read_wellness_range,
    wellness_archive_path,
)


@pytest.fixture
def wellness_tmp_dir(tmp_path, monkeypatch):
    """Redirige resolve_wellness_dir vers un tmp_path isolé."""
    from magma_cycling.wellness import archive as archive_mod

    monkeypatch.setattr(archive_mod, "resolve_wellness_dir", lambda: tmp_path)
    return tmp_path


class TestReadWellnessDay:
    """read_wellness_day — brique lecture single-day."""

    def test_returns_none_if_missing(self, wellness_tmp_dir):
        assert read_wellness_day("2026-01-15") is None

    def test_returns_payload_if_present(self, wellness_tmp_dir):
        payload = {"id": "2026-01-15", "ctl": 40.5, "atl": 30.2, "tsb": 10.3}
        archive_wellness_day("2026-01-15", payload)
        assert read_wellness_day("2026-01-15") == payload

    def test_corrupted_json_treated_as_absent(self, wellness_tmp_dir, caplog):
        path = wellness_archive_path("2026-01-15")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ invalid json", encoding="utf-8")
        with caplog.at_level("WARNING"):
            result = read_wellness_day("2026-01-15")
        assert result is None
        assert any("corrupted" in r.message for r in caplog.records)


class TestReadWellnessRange:
    """read_wellness_range — brique lecture window."""

    def test_empty_range_when_no_archive(self, wellness_tmp_dir):
        assert read_wellness_range("2026-01-15", "2026-01-20") == []

    def test_returns_only_archived_days(self, wellness_tmp_dir):
        # 3 jours dans la fenêtre, 1 archivé
        archive_wellness_day("2026-01-16", {"id": "2026-01-16", "ctl": 41.0})
        result = read_wellness_range("2026-01-15", "2026-01-18")
        assert len(result) == 1
        assert result[0]["id"] == "2026-01-16"

    def test_returns_range_sorted_by_date(self, wellness_tmp_dir):
        for date_str in ["2026-01-18", "2026-01-15", "2026-01-16"]:
            archive_wellness_day(date_str, {"id": date_str, "ctl": 40.0})
        result = read_wellness_range("2026-01-15", "2026-01-20")
        ids = [entry["id"] for entry in result]
        assert ids == ["2026-01-15", "2026-01-16", "2026-01-18"]

    def test_invalid_dates_rejected(self, wellness_tmp_dir):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            read_wellness_range("not-a-date", "2026-01-20")

    def test_reversed_range_rejected(self, wellness_tmp_dir):
        with pytest.raises(ValueError, match="must be <="):
            read_wellness_range("2026-01-20", "2026-01-15")


class TestArchiveWellnessPayload:
    """archive_wellness_payload — brique write-through."""

    def test_writes_all_entries(self, wellness_tmp_dir):
        payload = [
            {"id": "2026-01-15", "ctl": 40.0},
            {"id": "2026-01-16", "ctl": 41.0},
        ]
        written = archive_wellness_payload(payload)
        assert written == 2
        assert wellness_archive_path("2026-01-15").is_file()
        assert wellness_archive_path("2026-01-16").is_file()

    def test_skips_entries_without_valid_id(self, wellness_tmp_dir):
        payload = [
            {"id": "2026-01-15", "ctl": 40.0},
            {"id": None, "ctl": 41.0},  # no id
            {"id": "invalid-date", "ctl": 42.0},  # bad format
            {"ctl": 43.0},  # missing id key
        ]
        assert archive_wellness_payload(payload) == 1

    def test_write_failure_logged_but_returns_partial_count(
        self, wellness_tmp_dir, caplog, monkeypatch
    ):
        from magma_cycling.wellness import archive as archive_mod

        original = archive_mod.archive_wellness_day
        call_count = {"n": 0}

        def failing_second_call(date_str, payload):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise OSError("simulated disk full")
            return original(date_str, payload)

        monkeypatch.setattr(archive_mod, "archive_wellness_day", failing_second_call)

        payload = [
            {"id": "2026-01-15", "ctl": 40.0},
            {"id": "2026-01-16", "ctl": 41.0},
            {"id": "2026-01-17", "ctl": 42.0},
        ]
        with caplog.at_level("WARNING"):
            written = archive_wellness_payload(payload)
        assert written == 2  # 1st and 3rd succeed, 2nd fails
        assert any("archive write failed for 2026-01-16" in r.message for r in caplog.records)


class TestIntervalsClientGetWellnessCache:
    """IntervalsClient.get_wellness — intégration cache read-through."""

    def _make_client(self):
        return IntervalsClient(athlete_id="iXXXXXX", api_key="test-key")

    def _mock_response(self, payload, status=200):
        response = MagicMock()
        response.status_code = status
        response.json.return_value = payload
        response.text = json.dumps(payload)
        response.raise_for_status = MagicMock()
        return response

    def test_nominal_api_ok_populates_cache(self, wellness_tmp_dir):
        client = self._make_client()
        payload = [
            {"id": "2026-01-15", "ctl": 40.0},
            {"id": "2026-01-16", "ctl": 41.0},
        ]

        with patch.object(client.session, "get", return_value=self._mock_response(payload)):
            result = client.get_wellness(oldest="2026-01-15", newest="2026-01-16")

        assert result == payload
        # Write-through: cache alimenté
        assert wellness_archive_path("2026-01-15").is_file()
        assert wellness_archive_path("2026-01-16").is_file()

    def test_connection_error_falls_back_to_cache(self, wellness_tmp_dir, caplog):
        client = self._make_client()
        # Pré-remplir le cache
        archive_wellness_day("2026-01-15", {"id": "2026-01-15", "ctl": 40.0})
        archive_wellness_day("2026-01-16", {"id": "2026-01-16", "ctl": 41.0})

        with patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("network down"),
        ):
            with caplog.at_level("WARNING"):
                result = client.get_wellness(oldest="2026-01-15", newest="2026-01-16")

        assert len(result) == 2
        assert {entry["id"] for entry in result} == {"2026-01-15", "2026-01-16"}
        assert any("falling back to local cache" in r.message for r in caplog.records)

    def test_timeout_falls_back_to_cache(self, wellness_tmp_dir):
        client = self._make_client()
        archive_wellness_day("2026-01-15", {"id": "2026-01-15", "ctl": 40.0})

        with patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.Timeout("api slow"),
        ):
            result = client.get_wellness(oldest="2026-01-15", newest="2026-01-15")

        assert len(result) == 1
        assert result[0]["id"] == "2026-01-15"

    def test_http_500_falls_back_to_cache(self, wellness_tmp_dir):
        client = self._make_client()
        archive_wellness_day("2026-01-15", {"id": "2026-01-15", "ctl": 40.0})

        response = MagicMock()
        response.status_code = 500
        error = requests.exceptions.HTTPError("500 Server Error", response=response)
        response.raise_for_status.side_effect = error

        with patch.object(client.session, "get", return_value=response):
            result = client.get_wellness(oldest="2026-01-15", newest="2026-01-15")

        assert len(result) == 1
        assert result[0]["id"] == "2026-01-15"

    def test_http_401_does_not_fall_back(self, wellness_tmp_dir):
        """Auth failure = pas de fallback. Masquer l'auth avec du cache serait pire."""
        client = self._make_client()
        # Cache présent mais NE DOIT PAS être servi sur 401
        archive_wellness_day("2026-01-15", {"id": "2026-01-15", "ctl": 40.0})

        response = MagicMock()
        response.status_code = 401
        error = requests.exceptions.HTTPError("401 Unauthorized", response=response)
        response.raise_for_status.side_effect = error

        with patch.object(client.session, "get", return_value=response):
            with pytest.raises(requests.exceptions.HTTPError, match="401"):
                client.get_wellness(oldest="2026-01-15", newest="2026-01-15")

    def test_cache_empty_propagates_original_error(self, wellness_tmp_dir):
        """API down + cache vide = propage l'exception réseau."""
        client = self._make_client()

        with patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("network down"),
        ):
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get_wellness(oldest="2026-01-15", newest="2026-01-15")

    def test_fallback_requires_oldest_and_newest(self, wellness_tmp_dir):
        """Sans oldest/newest, impossible de fenêtrer le cache — propage."""
        client = self._make_client()
        archive_wellness_day("2026-01-15", {"id": "2026-01-15", "ctl": 40.0})

        with patch.object(
            client.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("network down"),
        ):
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get_wellness()

    def test_write_through_failure_does_not_break_api_response(self, wellness_tmp_dir):
        """Cache write en échec ne casse pas la réponse API (best-effort)."""
        client = self._make_client()
        payload = [{"id": "2026-01-15", "ctl": 40.0}]

        with (
            patch.object(client.session, "get", return_value=self._mock_response(payload)),
            patch(
                "magma_cycling.wellness.archive_wellness_payload",
                side_effect=OSError("disk full"),
            ),
        ):
            result = client.get_wellness(oldest="2026-01-15", newest="2026-01-15")

        assert result == payload  # API response returned despite cache failure
