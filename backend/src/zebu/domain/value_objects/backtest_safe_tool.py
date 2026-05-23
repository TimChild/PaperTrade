"""BacktestSafeTool value object — whitelist of tools the agent may call in backtest.

Phase L-2 (Task #218). The :class:`BacktestAgentInvocationAdapter` exposes
exactly this set of tools to the model during a simulated trigger fire.
Any other tool the agent attempts to invoke — ``web_search``,
``fetch_news``, ``get_current_price``, third-party MCP tools, etc. — is
not registered as a callable surface and (defence in depth) raises
:class:`BacktestSafetyViolationError` if the dispatch callback is reached
with an unknown name.

The wire-string values match the production MCP server's tool names so
the agent's behaviour is consistent across "live in-process tool use"
(L-2 future use) and "MCP backplane" (current desktop agent path).

References:
- ``docs/planning/agent-platform-next-steps.md`` §3.5 (BACKTEST_SAFE_TOOLS).
- ``mcp/src/zebu_mcp/tools/{prices, portfolios, exploration}.py`` for the
  live tool surface this list is a strict subset of.
"""

from __future__ import annotations

from enum import StrEnum


class BacktestSafeTool(StrEnum):
    """Whitelisted tools the agent may invoke inside a backtest replay.

    Values:
        GET_PRICE_HISTORY: Fetch historical price points for a ticker
            over a date range. Capped at ``end <= simulated_date`` —
            future-data leakage is the #1 backtest pitfall.
        GET_PORTFOLIO_STATE: Read the simulated backtest portfolio's
            balance + holdings ``as_of`` the simulated date. Capped at
            ``as_of <= simulated_date``.
        LIST_EXPLORATION_TASKS: List exploration tasks claimed on or
            before the simulated date. Capped at
            ``claimed_before <= simulated_date``. Status filter is
            restricted to ``DONE`` so the agent reads completed research
            artefacts rather than the live in-progress backlog.
    """

    GET_PRICE_HISTORY = "get_price_history"
    GET_PORTFOLIO_STATE = "get_portfolio_state"
    LIST_EXPLORATION_TASKS = "list_exploration_tasks"


# Frozen tuple form for callers that want a stable iteration order —
# StrEnum iteration is definition-order but a tuple is more explicit at
# the call site (e.g. when building the safety preamble's "available
# tools" list).
BACKTEST_SAFE_TOOL_NAMES: tuple[str, ...] = tuple(t.value for t in BacktestSafeTool)


__all__ = ["BACKTEST_SAFE_TOOL_NAMES", "BacktestSafeTool"]
