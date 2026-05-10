"""Portfolio-related read tools."""

from __future__ import annotations

from uuid import UUID

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import Page, Portfolio, PortfolioState


def register(server: FastMCP, client: ZebuClient) -> None:
    """Register portfolio tools on ``server``."""

    @server.tool(
        name="list_portfolios",
        description=(
            "List the authenticated user's paper-trading portfolios with "
            "pagination. By default BACKTEST-type portfolios are excluded "
            "(those are scratch portfolios created by backtest runs). Set "
            "include_backtest=true to include them."
        ),
    )
    async def list_portfolios(
        limit: int = 20,
        offset: int = 0,
        include_backtest: bool = False,
    ) -> Page[Portfolio]:
        """List the user's portfolios."""
        return await client.list_portfolios(
            limit=limit,
            offset=offset,
            include_backtest=include_backtest,
        )

    @server.tool(
        name="get_portfolio_state",
        description=(
            "Get a portfolio's full live state in one call: the portfolio "
            "metadata, the current cash + holdings + total value balance, "
            "and the per-ticker holdings list with cost basis and unrealized "
            "P/L. Prefer this over calling list_portfolios + balance + "
            "holdings separately — it's the canonical 'what's in this "
            "portfolio right now' read."
        ),
    )
    async def get_portfolio_state(portfolio_id: UUID) -> PortfolioState:
        """Composite read of a portfolio (metadata + balance + holdings)."""
        return await client.get_portfolio_state(portfolio_id)
