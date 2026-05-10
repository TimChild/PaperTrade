"""Per-domain tool registration aggregator.

Each tool module exposes a ``register(server, client)`` function; the
aggregator simply calls them all in a stable order so the server's tool
list is deterministic. New tool domains plug in here.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.tools import (
    activations,
    backtests,
    exploration,
    portfolios,
    prices,
    strategies,
    tickers,
)


def register_all(server: FastMCP, client: ZebuClient) -> None:
    """Register every Wave 1 read tool on ``server``.

    Order is alphabetical-by-domain so the registered tool order is
    stable for diffs / docs / tests.

    Args:
        server: The FastMCP server to attach tools to.
        client: The shared :class:`ZebuClient` every tool will close over.
    """
    activations.register(server, client)
    backtests.register(server, client)
    exploration.register(server, client)
    portfolios.register(server, client)
    prices.register(server, client)
    strategies.register(server, client)
    tickers.register(server, client)
