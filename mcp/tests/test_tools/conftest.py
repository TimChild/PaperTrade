"""Shared fixtures for per-tool tests.

Each test wires up a real :class:`ZebuClient` (talking to a respx mock)
and a real FastMCP server with all Wave 1 tools registered, then calls
the tool through ``server.call_tool(name, arguments)`` — the same path
Claude Code drives.

This level of test catches integration issues the pure-client tests
miss: tool name mismatches, decorator wiring bugs, MCP serialisation
quirks.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import respx
from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.config import ZebuMcpConfig
from zebu_mcp.tools import register_all


@pytest.fixture
async def server(
    config: ZebuMcpConfig,
    respx_mock_session: respx.MockRouter,
) -> AsyncIterator[FastMCP]:
    """A FastMCP server with every Wave 1 tool registered.

    The server is real; only the network layer is mocked via respx. Tool
    invocations go through the same dispatch the stdio transport uses.
    """
    _ = respx_mock_session  # ensure mock is up before httpx opens
    client = ZebuClient(config)
    async with client:
        srv = FastMCP(name="zebu-test")
        register_all(srv, client)
        yield srv
