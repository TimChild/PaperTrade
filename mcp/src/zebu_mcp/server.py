"""FastMCP server bootstrap.

Builds the MCP server, opens the shared :class:`ZebuClient` for its
lifetime, and registers every Wave 1 read tool on it. Lifetime is
managed by the FastMCP lifespan hook so the underlying httpx connection
pool is closed cleanly when the stdio transport ends.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from zebu_mcp._version import __version__
from zebu_mcp.client import ZebuClient
from zebu_mcp.config import ZebuMcpConfig
from zebu_mcp.tools import register_all


@dataclass(frozen=True)
class _LifespanContext:
    """Resources owned by the server for its full lifetime.

    The FastMCP lifespan API returns a typed context that's available to
    every tool call via the FastMCP request context. We don't currently
    read it inside tools (the tool closures already capture the client
    by reference), but the dataclass keeps a clear boundary if a future
    tool needs additional shared resources.
    """

    client: ZebuClient


def build_server(config: ZebuMcpConfig) -> FastMCP:
    """Construct a FastMCP server pre-loaded with every Wave 1 tool.

    The returned server is ready to ``run()``. The HTTP client is opened
    on lifespan-start and closed on lifespan-end so external resources
    line up with the stdio session boundary.

    Args:
        config: Resolved configuration.

    Returns:
        Configured :class:`FastMCP` instance.
    """
    # The client is constructed *outside* the lifespan so tool closures
    # captured at registration time can refer to a stable object. The
    # lifespan opens / closes its underlying httpx pool in step with the
    # server lifetime — `__aenter__` does the open, `__aexit__` the close.
    client = ZebuClient(config)

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncGenerator[_LifespanContext]:
        """Open the HTTP pool for the server's lifetime."""
        async with client:
            yield _LifespanContext(client=client)

    server = FastMCP(
        name="zebu",
        instructions=(
            "Zebu MCP server (read tools only — Phase D Wave 1).\n\n"
            "Exposes the Zebu paper-trading backend as named tools. Use "
            "list_supported_tickers / list_portfolios / list_strategies / "
            "list_backtests / list_active_strategies / list_exploration_tasks "
            "as starting points, then drill into specific entities with the "
            "get_* tools. Every list-returning tool is paginated — check "
            "has_more before assuming you've seen everything.\n\n"
            "Authentication: every request goes through a Zebu API key "
            "(set via ZEBU_API_KEY in the env). The server hashes the key "
            "and resolves it to the human user that minted it; everything "
            "you read is owner-scoped to that user.\n\n"
            "Write tools (create_strategy, run_backtest, activate_strategy, "
            "claim_exploration_task, etc.) ship in Wave 2."
        ),
        lifespan=lifespan,
        log_level="INFO",
    )

    register_all(server, client)
    return server


def run_stdio() -> None:
    """Read env config, build the server, run on stdio.

    This is the main entry point. Consumed by ``zebu_mcp.__main__`` and
    by the ``zebu-mcp`` console script declared in ``pyproject.toml``.

    Raises:
        ConfigError: If the env is missing required variables.
    """
    config = ZebuMcpConfig.from_env()
    server = build_server(config)
    # FastMCP's `run()` is sync (it sets up its own event loop). Stdio is
    # the only transport this server supports for Wave 1.
    server.run(transport="stdio")


__all__ = ["__version__", "build_server", "run_stdio"]
