#!/usr/bin/env python3
"""
MCP Transport Layer - HTTP/SSE and Stdio Support.

Provides transport abstraction for MCP server to support both:
- Stdio transport (default): for Claude Desktop local integration
- HTTP/SSE transport: for hot reload support with automatic reconnection

Usage:
    transport = MCPTransportManager(server, "http", "localhost", 3000)
    await transport.start()
"""

import sys

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route


class MCPTransportManager:
    """
    Manages MCP server transport layer.

    Supports two transport modes:
    - stdio: Standard input/output pipes (default, backward compatible)
    - http: HTTP/SSE for web clients with automatic reconnection
    """

    def __init__(self, server: Server, transport_mode: str, host: str, port: int):
        """
        Initialize transport manager.

        Args:
            server: MCP Server instance to run
            transport_mode: "stdio" or "http"
            host: HTTP server host (only used for http mode)
            port: HTTP server port (only used for http mode)
        """
        self.server = server
        self.transport_mode = transport_mode.lower()
        self.host = host
        self.port = port
        self.sse = SseServerTransport("/messages/")

        # Validate transport mode
        if self.transport_mode not in ("stdio", "http"):
            print(
                f"[MCP] Warning: Unknown transport mode '{transport_mode}', falling back to stdio",
                file=sys.stderr,
            )
            self.transport_mode = "stdio"

    async def run_stdio(self):
        """
        Run server with stdio transport (backward compatible).

        Uses stdin/stdout pipes for communication with Claude Desktop.
        This is the default mode for local process integration.
        """
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    async def _handle_sse(self, request: Request) -> Response:
        """
        Handle SSE endpoint - establishes Server-Sent Events stream.

        This endpoint creates a persistent connection for server-to-client messages.
        Claude Desktop connects here and maintains an SSE stream to receive responses.

        Args:
            request: Starlette Request object

        Returns:
            Response object (required by Starlette even though SSE stream handles sending)
        """
        async with self.sse.connect_sse(request.scope, request.receive, request._send) as (
            read_stream,
            write_stream,
        ):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )
        return Response()

    async def run_http(self):
        """
        Run server with HTTP/SSE transport.

        Creates a Starlette ASGI application with two endpoints:
        - GET /sse: Establishes SSE stream for server-to-client messages
        - POST /messages/: Receives client-to-server messages

        This mode supports automatic reconnection when the server restarts,
        making it ideal for development with hot reload (watchdog).
        """
        # Create Starlette app with SSE and message endpoints
        app = Starlette(
            routes=[
                Route("/sse", self._handle_sse, methods=["GET"]),
                Mount("/messages/", self.sse.handle_post_message),
            ]
        )

        # Configure uvicorn server
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False,  # Reduce log noise
        )

        # Run server
        server = uvicorn.Server(config)
        await server.serve()

    async def start(self):
        """
        Start MCP server with configured transport mode.

        Dispatches to appropriate transport implementation:
        - stdio: run_stdio() for local pipes
        - http: run_http() for HTTP/SSE
        """
        if self.transport_mode == "http":
            await self.run_http()
        else:
            await self.run_stdio()
