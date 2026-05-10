"""Backtest-related read tools."""

from __future__ import annotations

from uuid import UUID

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import BacktestRun, Page


def register(server: FastMCP, client: ZebuClient) -> None:
    """Register backtest tools on ``server``."""

    @server.tool(
        name="list_backtests",
        description=(
            "List the authenticated user's backtest runs with pagination. "
            "Optionally filter to a single strategy by passing strategy_id. "
            "Each item carries the run's metrics (total_return_pct, "
            "max_drawdown_pct, annualized_return_pct, total_trades) when the "
            "run completed; status='RUNNING' / 'PENDING' items have None "
            "metrics. Note: the strategy_id filter is currently applied "
            "client-side, so the returned 'total' reflects only the matched "
            "subset of the current page."
        ),
    )
    async def list_backtests(
        strategy_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[BacktestRun]:
        """List backtest runs."""
        return await client.list_backtests(
            strategy_id=strategy_id,
            limit=limit,
            offset=offset,
        )

    @server.tool(
        name="get_backtest_result",
        description=(
            "Get a backtest run by ID, with all its computed performance "
            "metrics. Use this to inspect the outcome of a backtest the "
            "agent (or the user) kicked off earlier — total_return_pct, "
            "max_drawdown_pct, annualized_return_pct, total_trades."
        ),
    )
    async def get_backtest_result(run_id: UUID) -> BacktestRun:
        """Get a backtest run by ID."""
        return await client.get_backtest(run_id)
