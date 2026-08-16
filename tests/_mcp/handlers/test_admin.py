"""Tests for _mcp/handlers/admin.py."""

import hashlib
import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from magma_cycling._mcp.handlers.admin import (
    handle_reload_server,
    handle_report_config_file_state,
)

_SKIP_POSIX_PERMS = pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX permission bits (chmod 0o600/0o644/0o700) are not honoured by Windows",
)


class TestHandleReloadServer:
    """Tests for handle_reload_server."""

    @pytest.mark.asyncio
    async def test_reload_returns_list(self):
        """Returns a list of TextContent."""
        result = await handle_reload_server({})
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_reload_response_is_valid_json(self):
        """Response text is valid JSON."""
        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "success" in data
        assert "reloaded_count" in data

    @pytest.mark.asyncio
    async def test_reload_handles_module_error(self):
        """Reports failed modules when reload raises."""
        bad_module = types.ModuleType("magma_cycling.config")

        with patch.dict("sys.modules", {"magma_cycling.config": bad_module}):
            with patch("importlib.reload", side_effect=ImportError("broken")):
                result = await handle_reload_server({})

        data = json.loads(result[0].text)
        assert len(data["failed"]) >= 1
        assert data["failed"][0]["error"] == "broken"

    @pytest.mark.asyncio
    async def test_reload_response_has_message(self):
        """Response always contains a message field."""
        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "message" in data

    @pytest.mark.asyncio
    async def test_reload_response_has_note(self):
        """Response contains note about handler limitation."""
        result = await handle_reload_server({})
        data = json.loads(result[0].text)
        assert "note" in data
        assert "NOT reloaded" in data["note"]


class TestHandleSystemInfoToolCount:
    """tool_count est aligné avec TOOL_HANDLERS (single source of truth)."""

    @pytest.mark.asyncio
    async def test_tool_count_matches_handlers(self):
        """`tool_count` retourné == `len(TOOL_HANDLERS)` — pas de drift possible.

        Régression : avant le fix, system-info re-listait 10 schemas et
        oubliait `terrain` + `handoff`, retournant 54 alors que TOOL_HANDLERS
        en contient 60. Ce test pin l'invariant : ce que system-info compte
        doit être exactement ce que le serveur peut dispatcher.
        """
        from magma_cycling._mcp.handlers.admin import handle_system_info
        from magma_cycling.mcp_server import TOOL_HANDLERS

        result = await handle_system_info({})
        data = json.loads(result[0].text)
        assert data["tool_count"] == len(TOOL_HANDLERS)


class TestHandleSystemInfoAIProvidersDiscovery:
    """ai_providers utilise AIConfig.get_available_providers (single source).

    Régression du bug d'origine : ``AIProviderFactory.create(name)`` était
    appelé avec un seul argument alors que la signature exige
    ``(provider, config)``, levant ``TypeError`` silencieusement avalée par
    ``except Exception: pass`` → ``ai_providers: []`` constant en prod.
    """

    @pytest.mark.asyncio
    async def test_uses_ai_config_get_available_providers(self):
        """Le retour ai_providers vient de get_ai_config().get_available_providers()."""
        from magma_cycling._mcp.handlers.admin import handle_system_info

        fake_config = MagicMock()
        fake_config.get_available_providers.return_value = ["mistral_api", "claude_api"]

        with patch("magma_cycling.config.get_ai_config", return_value=fake_config):
            result = await handle_system_info({})

        data = json.loads(result[0].text)
        assert data["ai_providers"] == ["mistral_api", "claude_api"]
        fake_config.get_available_providers.assert_called_once()

    @pytest.mark.asyncio
    async def test_discovery_failure_logs_warning_and_returns_empty(self, caplog):
        """Si get_ai_config() raise, log warning et retourne []."""
        import logging

        from magma_cycling._mcp.handlers.admin import handle_system_info

        with patch(
            "magma_cycling.config.get_ai_config",
            side_effect=RuntimeError("simulated config failure"),
        ):
            with caplog.at_level(logging.WARNING, logger="magma_cycling._mcp.handlers.admin"):
                result = await handle_system_info({})

        data = json.loads(result[0].text)
        assert data["ai_providers"] == []
        warnings = [r for r in caplog.records if "ai_provider discovery failed" in r.message]
        assert len(warnings) == 1
        assert "simulated config failure" in warnings[0].message


class TestHandleSystemInfoExtendedFields:
    """Tests for the version + data_repo fields exposed for TNR post-deploy."""

    @pytest.mark.asyncio
    async def test_response_contains_version(self):
        """The response exposes ``version`` from ``magma_cycling.__version__``."""
        from magma_cycling import __version__
        from magma_cycling._mcp.handlers.admin import handle_system_info

        result = await handle_system_info({})
        data = json.loads(result[0].text)
        assert data["version"] == __version__

    @pytest.mark.asyncio
    async def test_response_contains_data_repo_fields(self):
        """The response exposes ``data_repo_path`` and ``data_repo_health_ok``."""
        from magma_cycling._mcp.handlers.admin import handle_system_info

        result = await handle_system_info({})
        data = json.loads(result[0].text)
        assert "data_repo_path" in data
        assert "data_repo_health_ok" in data
        assert isinstance(data["data_repo_health_ok"], bool)

    @pytest.mark.asyncio
    async def test_data_repo_failure_is_logged_and_fields_safe(self, caplog):
        """If get_data_config raises, fields fallback to None / False with log warning."""
        import logging

        from magma_cycling._mcp.handlers.admin import handle_system_info

        with patch(
            "magma_cycling.config.get_data_config",
            side_effect=RuntimeError("simulated data_repo failure"),
        ):
            with caplog.at_level(logging.WARNING, logger="magma_cycling._mcp.handlers.admin"):
                result = await handle_system_info({})

        data = json.loads(result[0].text)
        assert data["data_repo_path"] is None
        assert data["data_repo_health_ok"] is False
        warnings = [r for r in caplog.records if "data_repo discovery failed" in r.message]
        assert len(warnings) == 1


class TestBT038HealthcheckWriterScopedMode:
    """BT-038 : le healthcheck ``data_repo_health_ok`` doit tester
    ``.git`` sur ``root_path`` (racine du repo git), pas sur ``data_repo_path``
    (qui = ``root_path/<writer_id>`` en writer-scoped, un simple dossier
    tracké et pas un git repo autonome).

    Cas prod 2026-08-16 Coach AI msg alerte : après activation writer-scoped,
    ``data_repo_health_ok=false`` remontait à tort — le sous-répertoire
    writer n'a pas de ``.git/`` par design, mais le repo git racine oui.
    Faux positif healthcheck → gel préventif tools par Coach AI.
    """

    @pytest.mark.asyncio
    async def test_healthcheck_true_when_git_on_root_and_scoped_path_exists(self, tmp_path):
        """Cas nominal writer-scoped : root_path a .git/, data_repo_path
        (subdir writer) existe → health_ok=True."""
        import json as json_mod

        from magma_cycling._mcp.handlers.admin import handle_system_info

        # Fixture repo writer-scoped : root a .git/, writer subdir peuplé
        (tmp_path / ".git").mkdir()
        writer_subdir = tmp_path / "abc123def456"
        writer_subdir.mkdir()

        class FakeCfg:
            root_path = tmp_path
            data_repo_path = writer_subdir

        with patch("magma_cycling.config.get_data_config", return_value=FakeCfg()):
            result = await handle_system_info({})
        data = json_mod.loads(result[0].text)
        assert data["data_repo_health_ok"] is True, (
            f"Expected healthcheck OK when .git exists on root_path and "
            f"data_repo_path (writer subdir) exists, got False. "
            f"data_repo_path={data['data_repo_path']}"
        )

    @pytest.mark.asyncio
    async def test_healthcheck_false_when_git_missing_on_root(self, tmp_path):
        """Root sans .git/ → False (pas un git repo)."""
        import json as json_mod

        from magma_cycling._mcp.handlers.admin import handle_system_info

        writer_subdir = tmp_path / "abc123def456"
        writer_subdir.mkdir()

        class FakeCfg:
            root_path = tmp_path
            data_repo_path = writer_subdir

        with patch("magma_cycling.config.get_data_config", return_value=FakeCfg()):
            result = await handle_system_info({})
        data = json_mod.loads(result[0].text)
        assert data["data_repo_health_ok"] is False

    @pytest.mark.asyncio
    async def test_healthcheck_false_when_scoped_path_missing(self, tmp_path):
        """Root avec .git/ mais writer subdir absent → False (writer
        subdir non monté ou WRITER_ID pointe sur un hash orphelin).
        Coach AI Q : deux conditions distinctes, deux échecs distincts."""
        import json as json_mod

        from magma_cycling._mcp.handlers.admin import handle_system_info

        (tmp_path / ".git").mkdir()
        writer_subdir = tmp_path / "abc123def456"  # non créé volontairement

        class FakeCfg:
            root_path = tmp_path
            data_repo_path = writer_subdir

        with patch("magma_cycling.config.get_data_config", return_value=FakeCfg()):
            result = await handle_system_info({})
        data = json_mod.loads(result[0].text)
        assert data["data_repo_health_ok"] is False


class TestHandleReportConfigFileState:
    """Tests for handle_report_config_file_state (self-reported sha256 + perms)."""

    @pytest.mark.asyncio
    async def test_default_scope_both_returns_bundle_and_user_yaml(self):
        """Default scope ``both`` includes both keys + the self-reported disclaimer."""
        result = await handle_report_config_file_state({})
        data = json.loads(result[0].text)
        assert data["self_reported"] is True
        assert "Not an external integrity attestation" in data["note"]
        assert "bundle" in data
        assert "user_yaml" in data

    @pytest.mark.asyncio
    async def test_scope_bundle_only(self):
        result = await handle_report_config_file_state({"scope": "bundle"})
        data = json.loads(result[0].text)
        assert "bundle" in data
        assert "user_yaml" not in data

    @pytest.mark.asyncio
    async def test_scope_user_yaml_only(self):
        result = await handle_report_config_file_state({"scope": "user_yaml"})
        data = json.loads(result[0].text)
        assert "user_yaml" in data
        assert "bundle" not in data

    @pytest.mark.asyncio
    async def test_invalid_scope_returns_error(self):
        result = await handle_report_config_file_state({"scope": "everything"})
        data = json.loads(result[0].text)
        assert "error" in data
        assert "invalid scope" in data["error"]

    @_SKIP_POSIX_PERMS
    @pytest.mark.asyncio
    async def test_bundle_state_matches_known_fixture(self, tmp_path):
        """SHA256 + size + perms reported for a known fixture file."""
        fake_bundle = tmp_path / "athlete_context.yaml"
        content = b"name: test\nweight: 70\n"
        fake_bundle.write_bytes(content)
        fake_bundle.chmod(0o644)
        expected_sha = hashlib.sha256(content).hexdigest()
        with patch(
            "magma_cycling.config.athlete_context.BUNDLE_ATHLETE_YAML",
            fake_bundle,
        ):
            result = await handle_report_config_file_state({"scope": "bundle"})
        bundle = json.loads(result[0].text)["bundle"]
        assert bundle["exists"] is True
        assert bundle["size_bytes"] == len(content)
        assert bundle["sha256"] == expected_sha
        assert bundle["perms_octal"] == "644"

    @pytest.mark.asyncio
    async def test_bundle_state_shape_cross_platform(self, tmp_path):
        """sha256/size/perms_octal fields exist regardless of OS (Windows-safe)."""
        fake_bundle = tmp_path / "athlete_context.yaml"
        content = b"name: test\n"
        fake_bundle.write_bytes(content)
        with patch(
            "magma_cycling.config.athlete_context.BUNDLE_ATHLETE_YAML",
            fake_bundle,
        ):
            result = await handle_report_config_file_state({"scope": "bundle"})
        bundle = json.loads(result[0].text)["bundle"]
        assert bundle["exists"] is True
        assert bundle["size_bytes"] == len(content)
        assert bundle["sha256"] == hashlib.sha256(content).hexdigest()
        assert "perms_octal" in bundle
        assert isinstance(bundle["perms_octal"], str)
        assert len(bundle["perms_octal"]) == 3

    @pytest.mark.asyncio
    async def test_bundle_missing_degrades_gracefully(self, tmp_path):
        """A missing bundle file reports exists=False without raising."""
        ghost = tmp_path / "does-not-exist.yaml"
        with patch(
            "magma_cycling.config.athlete_context.BUNDLE_ATHLETE_YAML",
            ghost,
        ):
            result = await handle_report_config_file_state({"scope": "bundle"})
        bundle = json.loads(result[0].text)["bundle"]
        assert bundle["exists"] is False
        assert "sha256" not in bundle
        assert "error" not in bundle

    @_SKIP_POSIX_PERMS
    @pytest.mark.asyncio
    async def test_user_yaml_reports_parent_dir_perms(self, tmp_path):
        """The user_yaml block embeds parent_dir perms (case 8 of the TNR brief)."""
        user_dir = tmp_path / "athlete"
        user_dir.mkdir(mode=0o700)
        user_file = user_dir / "athlete.yaml"
        user_file.write_text("name: stub\n")
        user_file.chmod(0o600)
        with patch(
            "magma_cycling.config.data_repo.resolve_athlete_yaml_path",
            return_value=user_file,
        ):
            result = await handle_report_config_file_state({"scope": "user_yaml"})
        user_yaml = json.loads(result[0].text)["user_yaml"]
        assert user_yaml["exists"] is True
        assert user_yaml["perms_octal"] == "600"
        assert user_yaml["parent_dir"]["exists"] is True
        assert user_yaml["parent_dir"]["perms_octal"] == "700"

    @pytest.mark.asyncio
    async def test_user_yaml_parent_dir_shape_cross_platform(self, tmp_path):
        """parent_dir block is always emitted with path + exists + perms_octal (Windows-safe)."""
        user_dir = tmp_path / "athlete"
        user_dir.mkdir()
        user_file = user_dir / "athlete.yaml"
        user_file.write_text("name: stub\n")
        with patch(
            "magma_cycling.config.data_repo.resolve_athlete_yaml_path",
            return_value=user_file,
        ):
            result = await handle_report_config_file_state({"scope": "user_yaml"})
        user_yaml = json.loads(result[0].text)["user_yaml"]
        assert user_yaml["exists"] is True
        assert user_yaml["parent_dir"]["exists"] is True
        assert "perms_octal" in user_yaml["parent_dir"]
        assert len(user_yaml["parent_dir"]["perms_octal"]) == 3

    @pytest.mark.asyncio
    async def test_user_yaml_resolve_failure_reports_error(self):
        """If resolve_athlete_yaml_path() raises, the user_yaml block contains an error field."""
        with patch(
            "magma_cycling.config.data_repo.resolve_athlete_yaml_path",
            side_effect=RuntimeError("boom"),
        ):
            result = await handle_report_config_file_state({"scope": "user_yaml"})
        user_yaml = json.loads(result[0].text)["user_yaml"]
        assert "error" in user_yaml
        assert "boom" in user_yaml["error"]
