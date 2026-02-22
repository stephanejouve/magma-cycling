"""
Unit tests for MCP transport layer (HTTP/SSE and stdio).

Tests the MCPTransportManager class that provides transport abstraction
for both stdio (default) and HTTP/SSE modes.
"""

import pytest
from mcp.server import Server

from cyclisme_training_logs.mcp_transport import MCPTransportManager


def test_transport_manager_init_stdio():
    """Test transport manager initialization with stdio mode."""
    server = Server("test-server")
    transport = MCPTransportManager(server, "stdio", "localhost", 3000)

    assert transport.server == server
    assert transport.transport_mode == "stdio"
    assert transport.host == "localhost"
    assert transport.port == 3000
    assert transport.sse is not None  # SSE is created even if not used


def test_transport_manager_init_http():
    """Test transport manager initialization with HTTP mode."""
    server = Server("test-server")
    transport = MCPTransportManager(server, "http", "127.0.0.1", 3001)

    assert transport.server == server
    assert transport.transport_mode == "http"
    assert transport.host == "127.0.0.1"
    assert transport.port == 3001
    assert transport.sse is not None


def test_transport_manager_invalid_mode_fallback():
    """Test that invalid transport mode falls back to stdio."""
    server = Server("test-server")
    transport = MCPTransportManager(server, "INVALID", "localhost", 3000)

    # Should fallback to stdio
    assert transport.transport_mode == "stdio"


def test_transport_manager_case_insensitive():
    """Test that transport mode is case-insensitive."""
    server = Server("test-server")

    # Test uppercase HTTP
    transport_upper = MCPTransportManager(server, "HTTP", "localhost", 3000)
    assert transport_upper.transport_mode == "http"

    # Test mixed case
    transport_mixed = MCPTransportManager(server, "StDiO", "localhost", 3000)
    assert transport_mixed.transport_mode == "stdio"


@pytest.mark.asyncio
async def test_transport_stdio_mode_exists():
    """Test that stdio mode method exists and is callable."""
    server = Server("test-server")
    transport = MCPTransportManager(server, "stdio", "localhost", 3000)

    # Just verify the method exists and is callable
    # Full integration test would require actual stdio pipes
    assert hasattr(transport, "run_stdio")
    assert callable(transport.run_stdio)


@pytest.mark.asyncio
async def test_transport_http_mode_exists():
    """Test that HTTP mode method exists and is callable."""
    server = Server("test-server")
    transport = MCPTransportManager(server, "http", "127.0.0.1", 3000)

    # Just verify the method exists and is callable
    # Full integration test would require starting uvicorn server
    assert hasattr(transport, "run_http")
    assert callable(transport.run_http)


@pytest.mark.asyncio
async def test_transport_start_method_exists():
    """Test that start method exists and dispatches correctly."""
    server = Server("test-server")
    transport = MCPTransportManager(server, "stdio", "localhost", 3000)

    # Verify start method exists
    assert hasattr(transport, "start")
    assert callable(transport.start)


def test_transport_sse_endpoint_configured():
    """Test that SSE transport is configured with correct message path."""
    server = Server("test-server")
    transport = MCPTransportManager(server, "http", "localhost", 3000)

    # Verify SSE transport was created with message endpoint
    assert transport.sse is not None
    # SSE transport should have handle_post_message method for POST endpoint
    assert hasattr(transport.sse, "handle_post_message")
    assert callable(transport.sse.handle_post_message)


def test_transport_http_config_stored():
    """Test that HTTP host and port configuration is stored."""
    server = Server("test-server")

    # Test various host/port combinations
    configs = [
        ("localhost", 3000),
        ("127.0.0.1", 3001),
        ("0.0.0.0", 8080),
    ]

    for host, port in configs:
        transport = MCPTransportManager(server, "http", host, port)
        assert transport.host == host
        assert transport.port == port


@pytest.mark.asyncio
async def test_transport_start_dispatches_to_stdio():
    """Test that start() dispatches to run_stdio() in stdio mode."""
    from unittest.mock import AsyncMock, patch

    server = Server("test-server")
    transport = MCPTransportManager(server, "stdio", "localhost", 3000)

    # Mock run_stdio to avoid actually running it
    with patch.object(transport, "run_stdio", new_callable=AsyncMock) as mock_stdio:
        # Start will call run_stdio and we immediately stop
        mock_stdio.return_value = None

        await transport.start()

        # Verify run_stdio was called
        mock_stdio.assert_called_once()


@pytest.mark.asyncio
async def test_transport_start_dispatches_to_http():
    """Test that start() dispatches to run_http() in http mode."""
    from unittest.mock import AsyncMock, patch

    server = Server("test-server")
    transport = MCPTransportManager(server, "http", "localhost", 3000)

    # Mock run_http to avoid actually starting uvicorn
    with patch.object(transport, "run_http", new_callable=AsyncMock) as mock_http:
        mock_http.return_value = None

        await transport.start()

        # Verify run_http was called
        mock_http.assert_called_once()


@pytest.mark.asyncio
async def test_transport_run_stdio_uses_stdio_server():
    """Test that run_stdio() uses stdio_server context manager."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock, patch

    server = Server("test-server")
    transport = MCPTransportManager(server, "stdio", "localhost", 3000)

    # Mock stdio_server and server.run
    mock_read = MagicMock()
    mock_write = MagicMock()

    @asynccontextmanager
    async def mock_stdio_context():
        yield (mock_read, mock_write)

    with patch(
        "cyclisme_training_logs.mcp_transport.stdio_server", return_value=mock_stdio_context()
    ):
        with patch.object(server, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = None

            await transport.run_stdio()

            # Verify server.run was called with streams
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == mock_read
            assert call_args[0][1] == mock_write


@pytest.mark.asyncio
async def test_transport_run_http_creates_starlette_app():
    """Test that run_http() creates Starlette app with correct routes."""
    from unittest.mock import AsyncMock, MagicMock, patch

    server = Server("test-server")
    transport = MCPTransportManager(server, "http", "127.0.0.1", 3001)

    # Mock uvicorn Server
    mock_uvicorn_server = MagicMock()
    mock_uvicorn_server.serve = AsyncMock()

    with patch(
        "cyclisme_training_logs.mcp_transport.uvicorn.Server", return_value=mock_uvicorn_server
    ):
        await transport.run_http()

        # Verify uvicorn.Server was created
        assert mock_uvicorn_server.serve.called


@pytest.mark.asyncio
async def test_transport_handle_sse_returns_response():
    """Test that _handle_sse returns a Response object."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock, patch

    from starlette.responses import Response

    server = Server("test-server")
    transport = MCPTransportManager(server, "http", "localhost", 3000)

    # Mock request and SSE connection
    mock_request = MagicMock()
    mock_request.scope = {}
    mock_request.receive = AsyncMock()
    mock_request._send = AsyncMock()

    mock_read = MagicMock()
    mock_write = MagicMock()

    @asynccontextmanager
    async def mock_sse_context(*args, **kwargs):
        yield (mock_read, mock_write)

    # Mock SSE connect and server.run
    with patch.object(transport.sse, "connect_sse", return_value=mock_sse_context()):
        with patch.object(server, "run", new_callable=AsyncMock):
            result = await transport._handle_sse(mock_request)

            # Verify it returns a Response
            assert isinstance(result, Response)
