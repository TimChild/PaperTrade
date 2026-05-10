"""Strategy-related read tools."""

from __future__ import annotations

from uuid import UUID

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import Page, Strategy


def register(server: FastMCP, client: ZebuClient) -> None:
    """Register strategy tools on ``server``."""

    @server.tool(
        name="list_strategies",
        description=(
            "List the authenticated user's saved trading strategies with "
            "pagination. Use this to see what strategy templates already "
            "exist before designing a new one — the agent should reuse / "
            "iterate parameters on existing strategies rather than "
            "creating duplicates."
        ),
    )
    async def list_strategies(
        limit: int = 20,
        offset: int = 0,
    ) -> Page[Strategy]:
        """List the user's saved strategies."""
        return await client.list_strategies(limit=limit, offset=offset)

    @server.tool(
        name="get_strategy",
        description=(
            "Get the full definition of a single strategy by ID, including "
            "its strategy_type (BUY_AND_HOLD / DOLLAR_COST_AVERAGING / "
            "MOVING_AVERAGE_CROSSOVER), tickers, and parameter dict. The "
            "parameters shape varies by strategy_type — see the Zebu "
            "domain.value_objects.strategy_parameters module for the "
            "per-type contract."
        ),
    )
    async def get_strategy(strategy_id: UUID) -> Strategy:
        """Get a single strategy by ID."""
        return await client.get_strategy(strategy_id)
