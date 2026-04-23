"""Tests for MCP server logging configuration."""

import logging
import os
from logging.handlers import RotatingFileHandler
from unittest.mock import AsyncMock, patch

import pytest

from magma_cycling.config.logging_config import setup_logging, setup_mcp_logging


@pytest.fixture(autouse=True)
def _clean_root_handlers():
    """Remove any file handlers added during tests."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    yield
    for h in root.handlers[:]:
        if h not in original_handlers:
            h.close()
            root.removeHandler(h)


class TestSetupLoggingFileHandler:
    """Tests for the file_path parameter of setup_logging()."""

    def test_file_handler_created(self, tmp_path):
        """setup_logging(file_path=...) creates a RotatingFileHandler."""
        log_file = str(tmp_path / "test.log")
        setup_logging(file_path=log_file, force=True)

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) >= 1
        assert any(h.baseFilename == log_file for h in file_handlers)

    def test_no_file_handler_without_file_path(self):
        """setup_logging() without file_path does not create a FileHandler."""
        setup_logging(force=True)

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 0

    def test_file_handler_creates_parent_directory(self, tmp_path):
        """setup_logging(file_path=...) creates parent directories."""
        log_file = str(tmp_path / "nested" / "dir" / "test.log")
        setup_logging(file_path=log_file, force=True)

        assert os.path.isdir(str(tmp_path / "nested" / "dir"))

    def test_file_handler_respects_max_bytes(self, tmp_path):
        """RotatingFileHandler uses the max_bytes parameter."""
        log_file = str(tmp_path / "test.log")
        setup_logging(file_path=log_file, max_bytes=1_000_000, backup_count=2, force=True)

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        handler = next(h for h in file_handlers if h.baseFilename == log_file)
        assert handler.maxBytes == 1_000_000
        assert handler.backupCount == 2


class TestSetupMcpLogging:
    """Tests for setup_mcp_logging()."""

    def test_configures_file_logging(self, tmp_path, monkeypatch):
        """setup_mcp_logging() reads MCP_LOG_FILE and configures file handler."""
        log_file = str(tmp_path / "mcp.log")
        monkeypatch.setenv("MCP_LOG_FILE", log_file)

        result = setup_mcp_logging()

        assert result == log_file
        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert any(h.baseFilename == log_file for h in file_handlers)

    def test_disabled_with_empty_string(self, monkeypatch):
        """MCP_LOG_FILE="" disables file logging."""
        monkeypatch.setenv("MCP_LOG_FILE", "")

        result = setup_mcp_logging()

        assert result is None
        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 0

    def test_reads_mcp_log_level(self, tmp_path, monkeypatch):
        """setup_mcp_logging() reads MCP_LOG_LEVEL."""
        log_file = str(tmp_path / "mcp.log")
        monkeypatch.setenv("MCP_LOG_FILE", log_file)
        monkeypatch.setenv("MCP_LOG_LEVEL", "DEBUG")

        setup_mcp_logging()

        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_reads_custom_rotation_params(self, tmp_path, monkeypatch):
        """setup_mcp_logging() reads MCP_LOG_MAX_BYTES and MCP_LOG_BACKUP_COUNT."""
        log_file = str(tmp_path / "mcp.log")
        monkeypatch.setenv("MCP_LOG_FILE", log_file)
        monkeypatch.setenv("MCP_LOG_MAX_BYTES", "1048576")
        monkeypatch.setenv("MCP_LOG_BACKUP_COUNT", "5")

        setup_mcp_logging()

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        handler = next(h for h in file_handlers if h.baseFilename == log_file)
        assert handler.maxBytes == 1_048_576
        assert handler.backupCount == 5


class TestDispatcherLogging:
    """Tests for tool call logging in the dispatcher."""

    @pytest.mark.asyncio
    async def test_dispatcher_logs_success(self, caplog):
        """dispatch_tool() logs tool name and duration on success."""
        from mcp.types import TextContent

        from magma_cycling.mcp_server import TOOL_HANDLERS, dispatch_tool

        mock_handler = AsyncMock(return_value=[TextContent(type="text", text="ok")])
        with (
            patch.dict(TOOL_HANDLERS, {"test-tool": mock_handler}),
            caplog.at_level(logging.INFO, logger="magma_cycling.mcp_server"),
        ):
            await dispatch_tool("test-tool", {})

        messages = caplog.text
        assert "tool_call_start: test-tool" in messages
        assert "tool_call_ok: test-tool" in messages
        mock_handler.assert_awaited_once_with({})

    @pytest.mark.asyncio
    async def test_dispatcher_logs_error(self, caplog):
        """dispatch_tool() logs errors for unknown tools."""
        from magma_cycling.mcp_server import dispatch_tool

        with caplog.at_level(logging.INFO, logger="magma_cycling.mcp_server"):
            await dispatch_tool("nonexistent-tool", {})

        messages = caplog.text
        assert "tool_call_start: nonexistent-tool" in messages
        assert "tool_call_error: nonexistent-tool" in messages


class TestServerTimeMeta:
    """Tests for the server_time meta block appended to tool responses."""

    @pytest.mark.asyncio
    async def test_dispatcher_appends_server_time_on_success(self):
        """Successful tool calls end with a [meta] server_time= line."""
        from mcp.types import TextContent

        from magma_cycling.mcp_server import TOOL_HANDLERS, dispatch_tool

        mock_handler = AsyncMock(return_value=[TextContent(type="text", text="ok")])
        with patch.dict(TOOL_HANDLERS, {"test-tool": mock_handler}):
            result = await dispatch_tool("test-tool", {})

        assert len(result) == 2
        assert result[0].text == "ok"
        assert result[1].text.startswith("[meta] server_time=")

    @pytest.mark.asyncio
    async def test_dispatcher_appends_server_time_on_error(self):
        """Failed tool calls also end with a [meta] server_time= line."""
        from magma_cycling.mcp_server import dispatch_tool

        result = await dispatch_tool("nonexistent-tool", {})

        assert len(result) == 2
        assert "error" in result[0].text
        assert result[1].text.startswith("[meta] server_time=")
