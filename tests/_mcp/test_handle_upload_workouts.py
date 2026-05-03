"""Tests for the MCP handler ``upload-workouts``.

Wraps ``WorkoutUploader.upload_all`` (legacy CLI ``upload-workouts``) to
expose its capability via MCP. Tests focus on the wiring (handler →
WorkoutUploader → response) plus the path-traversal guard.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def fake_data_repo(tmp_path):
    """Build a fake data_repo with a workouts file inside."""
    repo = tmp_path / "training-logs"
    week_planning = repo / "data" / "week_planning"
    week_planning.mkdir(parents=True)
    workouts_file = week_planning / "S091_workouts.txt"
    workouts_file.write_text(
        "=== WORKOUT S091-01-END-X-V001 ===\nfake content\n=== FIN WORKOUT ===\n"
    )
    return repo


def _patch_data_config(repo_path):
    """Helper: patch get_data_config to return a config pointing at repo_path."""
    cfg = MagicMock()
    cfg.data_repo_path = repo_path
    return patch("magma_cycling.config.get_data_config", return_value=cfg)


class TestHandleUploadWorkouts:
    @pytest.mark.asyncio
    async def test_success_dry_run(self, fake_data_repo):
        """dry_run=true: parses file, calls upload_all dry, returns stats."""
        from magma_cycling.mcp_server import handle_upload_workouts

        uploader = MagicMock()
        uploader.parse_workouts_file.return_value = [{"name": "S091-01-END-X-V001"}]
        uploader.upload_all.return_value = {"success": 1, "failed": 0, "total": 1}

        with (
            _patch_data_config(fake_data_repo),
            patch("magma_cycling.upload_workouts.WorkoutUploader", return_value=uploader),
        ):
            result = await handle_upload_workouts(
                {
                    "week_id": "S091",
                    "workouts_file_path": "data/week_planning/S091_workouts.txt",
                    "start_date": "2026-04-27",
                    "dry_run": True,
                }
            )

        uploader.upload_all.assert_called_once()
        call_kwargs = uploader.upload_all.call_args
        # dry_run propagated
        assert call_kwargs.kwargs.get("dry_run") is True

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "success"
        assert data["dry_run"] is True
        assert data["workout_count"] == 1
        assert data["stats"]["success"] == 1

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, fake_data_repo):
        """Path with ../ outside data_repo MUST be rejected."""
        from magma_cycling.mcp_server import handle_upload_workouts

        with _patch_data_config(fake_data_repo):
            result = await handle_upload_workouts(
                {
                    "week_id": "S091",
                    "workouts_file_path": "../../../etc/passwd",
                    "start_date": "2026-04-27",
                }
            )

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "error"
        assert "outside" in data["message"].lower() or "stay within" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_missing_file_returns_error(self, fake_data_repo):
        """File that doesn't exist → error, no crash."""
        from magma_cycling.mcp_server import handle_upload_workouts

        with _patch_data_config(fake_data_repo):
            result = await handle_upload_workouts(
                {
                    "week_id": "S091",
                    "workouts_file_path": "data/week_planning/S099_workouts.txt",
                    "start_date": "2026-04-27",
                }
            )

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_empty_workouts_returns_error(self, fake_data_repo):
        """parse returns empty → error, doesn't call upload_all."""
        from magma_cycling.mcp_server import handle_upload_workouts

        uploader = MagicMock()
        uploader.parse_workouts_file.return_value = []

        with (
            _patch_data_config(fake_data_repo),
            patch("magma_cycling.upload_workouts.WorkoutUploader", return_value=uploader),
        ):
            result = await handle_upload_workouts(
                {
                    "week_id": "S091",
                    "workouts_file_path": "data/week_planning/S091_workouts.txt",
                    "start_date": "2026-04-27",
                    "dry_run": True,
                }
            )

        uploader.upload_all.assert_not_called()
        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "error"
        assert "no workouts" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_partial_failure_status(self, fake_data_repo):
        """failed > 0 → status=partial_failure."""
        from magma_cycling.mcp_server import handle_upload_workouts

        uploader = MagicMock()
        uploader.parse_workouts_file.return_value = [
            {"name": "S091-01-END-X-V001"},
            {"name": "S091-02-INT-Y-V001"},
        ]
        uploader.upload_all.return_value = {"success": 1, "failed": 1, "total": 2}

        with (
            _patch_data_config(fake_data_repo),
            patch("magma_cycling.upload_workouts.WorkoutUploader", return_value=uploader),
        ):
            result = await handle_upload_workouts(
                {
                    "week_id": "S091",
                    "workouts_file_path": "data/week_planning/S091_workouts.txt",
                    "start_date": "2026-04-27",
                    "dry_run": True,
                }
            )

        data = json.loads(result[0].text.split("[meta]")[0].strip())
        assert data["status"] == "partial_failure"
        assert data["stats"]["failed"] == 1


class TestUploadWorkoutsWiring:
    """Verify the handler is properly wired into TOOL_HANDLERS dispatcher."""

    def test_handler_registered_in_dispatcher(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS, handle_upload_workouts

        assert "upload-workouts" in TOOL_HANDLERS
        assert TOOL_HANDLERS["upload-workouts"] is handle_upload_workouts

    def test_tool_count_includes_new_handler(self):
        from magma_cycling.mcp_server import TOOL_HANDLERS

        assert "upload-workouts" in TOOL_HANDLERS
        assert len(TOOL_HANDLERS) >= 63

    def test_tool_schema_exposed(self):
        from magma_cycling._mcp.schemas.workouts import get_tools

        names = [t.name for t in get_tools()]
        assert "upload-workouts" in names
