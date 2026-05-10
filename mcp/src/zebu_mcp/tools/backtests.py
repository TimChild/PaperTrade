"""Backtest read + run tools."""

from __future__ import annotations

import asyncio
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import BacktestRun, Page, RunBacktestRequest

# Polling cadence for run_backtest's "wait for completion" path. The
# backend currently runs backtests synchronously in the request handler
# (see ``BacktestExecutor.execute``), so the response comes back
# already-complete and the polling loop exits on the first iteration.
# These constants only matter if the backend later switches to a
# background-job model.
_POLL_INTERVAL_SECS = 1.0
_DEFAULT_POLL_TIMEOUT_SECS = 60.0
_TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED"})


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

    @server.tool(
        name="run_backtest",
        description=(
            "Run a backtest for a saved strategy over a date range with a "
            "given starting cash. Dates are YYYY-MM-DD; date range must be "
            "<= 3 years and end_date <= today. initial_cash is a decimal "
            "string with at most 2 decimal places (e.g. '10000.00').\n\n"
            "Returns the BacktestRun, normally already in COMPLETED status "
            "(the backend runs synchronously today). When "
            "wait_for_completion=true (default), and the response status is "
            "not yet terminal, the tool polls get_backtest_result every "
            "second until status is COMPLETED or FAILED, or until "
            "poll_timeout_secs elapses (default 60s) — at which point the "
            "tool returns the latest still-RUNNING run rather than raising."
        ),
    )
    async def run_backtest(
        strategy_id: UUID,
        start_date: str,
        end_date: str,
        initial_cash: str,
        name: str | None = None,
        wait_for_completion: bool = True,
        poll_timeout_secs: float = _DEFAULT_POLL_TIMEOUT_SECS,
    ) -> BacktestRun:
        """Run a backtest, optionally polling until terminal."""
        request = RunBacktestRequest(
            strategy_id=strategy_id,
            backtest_name=name or f"agent run {start_date}..{end_date}",
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
        )
        run = await client.run_backtest(request)

        if not wait_for_completion or run.status in _TERMINAL_STATUSES:
            return run

        deadline = asyncio.get_running_loop().time() + poll_timeout_secs
        latest = run
        while latest.status not in _TERMINAL_STATUSES:
            now = asyncio.get_running_loop().time()
            if now >= deadline:
                # Out of budget — return the most-recent state. Caller can
                # poll get_backtest_result themselves.
                return latest
            # Sleep for the smaller of the poll interval and the time
            # remaining, so we don't oversleep past the deadline.
            await asyncio.sleep(min(_POLL_INTERVAL_SECS, max(deadline - now, 0.0)))
            latest = await client.get_backtest(latest.id)
        return latest
