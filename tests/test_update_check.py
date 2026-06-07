"""Tests for ``magma_cycling.update_check``.

Cover the four behavioural contracts that matter at boot time :

* opt-out via ``MAGMA_NO_UPDATE_CHECK`` env var,
* up-to-date case returns ``None``,
* update-available case returns the release URL,
* network/parse failure paths are silent and return ``None``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from magma_cycling import update_check


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Force the cache file under tmp_path so tests do not pollute the real one."""
    monkeypatch.setattr(update_check, "_cache_path", lambda: tmp_path / "update_check.json")
    monkeypatch.delenv(update_check.ENV_OPT_OUT, raising=False)
    yield


def _ok_response(tag: str, html_url: str) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"tag_name": tag, "html_url": html_url}
    return resp


class TestOptOut:
    @pytest.mark.parametrize("value", ["1", "true", "yes"])
    def test_env_var_disables_check(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv(update_check.ENV_OPT_OUT, value)
        # If opt-out is respected, requests.get must NEVER be called.
        with patch("magma_cycling.update_check.requests.get") as mock_get:
            assert update_check.check_for_updates(current_version="3.43.1") is None
        mock_get.assert_not_called()


class TestUpToDate:
    def test_same_version_returns_none(self) -> None:
        with patch(
            "magma_cycling.update_check.requests.get",
            return_value=_ok_response("v3.43.1", "https://example/releases/v3.43.1"),
        ):
            assert update_check.check_for_updates(current_version="3.43.1") is None

    def test_v_prefix_normalised(self) -> None:
        # ``__version__`` exposes "3.43.1" while the tag is "v3.43.1" — they
        # must compare equal.
        with patch(
            "magma_cycling.update_check.requests.get",
            return_value=_ok_response("v3.43.1", "https://example/releases/v3.43.1"),
        ):
            assert update_check.check_for_updates(current_version="v3.43.1") is None


class TestUpdateAvailable:
    def test_newer_release_returns_url(self) -> None:
        with patch(
            "magma_cycling.update_check.requests.get",
            return_value=_ok_response("v3.51.1", "https://example/releases/v3.51.1"),
        ):
            url = update_check.check_for_updates(current_version="3.47.2")
        assert url == "https://example/releases/v3.51.1"

    def test_cache_written_on_success(self, tmp_path: Path) -> None:
        with patch(
            "magma_cycling.update_check.requests.get",
            return_value=_ok_response("v3.51.1", "https://example/releases/v3.51.1"),
        ):
            update_check.check_for_updates(current_version="3.47.2")
        cache = update_check._cache_path()
        assert cache.is_file()
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert data["latest_tag"] == "v3.51.1"
        assert data["url"] == "https://example/releases/v3.51.1"

    def test_cache_hit_skips_network(self, tmp_path: Path) -> None:
        cache = update_check._cache_path()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps(
                {
                    "checked_at": time.time(),
                    "latest_tag": "v3.51.1",
                    "url": "https://example/releases/v3.51.1",
                }
            ),
            encoding="utf-8",
        )
        with patch("magma_cycling.update_check.requests.get") as mock_get:
            url = update_check.check_for_updates(current_version="3.47.2")
        assert url == "https://example/releases/v3.51.1"
        mock_get.assert_not_called()

    def test_cache_expired_refetches(self, tmp_path: Path) -> None:
        cache = update_check._cache_path()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps(
                {
                    "checked_at": time.time() - update_check.CACHE_TTL_SECONDS - 60,
                    "latest_tag": "v3.50.0",
                    "url": "https://example/releases/v3.50.0",
                }
            ),
            encoding="utf-8",
        )
        with patch(
            "magma_cycling.update_check.requests.get",
            return_value=_ok_response("v3.51.1", "https://example/releases/v3.51.1"),
        ) as mock_get:
            url = update_check.check_for_updates(current_version="3.47.2")
        mock_get.assert_called_once()
        assert url == "https://example/releases/v3.51.1"


class TestSilentFailure:
    def test_network_error_returns_none(self) -> None:
        with patch(
            "magma_cycling.update_check.requests.get",
            side_effect=requests.ConnectionError("offline"),
        ):
            assert update_check.check_for_updates(current_version="3.47.2") is None

    def test_timeout_returns_none(self) -> None:
        with patch(
            "magma_cycling.update_check.requests.get",
            side_effect=requests.Timeout(),
        ):
            assert update_check.check_for_updates(current_version="3.47.2") is None

    def test_malformed_payload_returns_none(self) -> None:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"unexpected": "shape"}
        with patch("magma_cycling.update_check.requests.get", return_value=resp):
            assert update_check.check_for_updates(current_version="3.47.2") is None

    def test_announce_swallows_all_errors(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(
            "magma_cycling.update_check.check_for_updates",
            side_effect=RuntimeError("boom"),
        ):
            update_check.announce_update_if_any()
        out, err = capsys.readouterr()
        assert out == ""
        assert err == ""


class TestAnnouncement:
    def test_prints_only_when_update_available(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(
            "magma_cycling.update_check.check_for_updates",
            return_value="https://example/releases/v3.51.1",
        ):
            update_check.announce_update_if_any()
        out, err = capsys.readouterr()
        assert "Update disponible" in err
        assert "https://example/releases/v3.51.1" in err
        assert out == ""

    def test_silent_when_up_to_date(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("magma_cycling.update_check.check_for_updates", return_value=None):
            update_check.announce_update_if_any()
        out, err = capsys.readouterr()
        assert out == ""
        assert err == ""
