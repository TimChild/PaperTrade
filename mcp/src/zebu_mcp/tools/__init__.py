"""MCP tool registrations.

Tools are organised by domain (prices, portfolios, strategies, etc.).
Each module exposes a single ``register(server, client)`` function that
attaches its tools to the FastMCP server instance.

This shape (registration function instead of decorator-at-import-time) is
deliberate: tools need access to the per-process :class:`ZebuClient`,
which is built in :mod:`zebu_mcp.server` after env config is read. Pulling
registration into a function lets us keep the client out of module-level
globals and lets tests construct a server with a mock client.
"""

from zebu_mcp.tools import (
    activations,
    backtests,
    exploration,
    portfolios,
    prices,
    strategies,
    tickers,
)
from zebu_mcp.tools._registry import register_all

__all__ = [
    "activations",
    "backtests",
    "exploration",
    "portfolios",
    "prices",
    "register_all",
    "strategies",
    "tickers",
]
