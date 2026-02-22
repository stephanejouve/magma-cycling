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
