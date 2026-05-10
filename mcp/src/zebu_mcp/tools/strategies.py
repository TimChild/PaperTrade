"""Strategy read + create tools."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import CreateStrategyRequest, Page, Strategy


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

    @server.tool(
        name="create_strategy",
        description=(
            "Create a new strategy template. The strategy_type discriminator "
            "selects the expected parameters shape:\n\n"
            "- BUY_AND_HOLD: {'allocation': {'<TICKER>': '<fraction>', ...}} "
            "where fractions are decimal strings summing to 1.0 (±0.001).\n"
            "- DOLLAR_COST_AVERAGING: {'frequency_days': <int 1-365>, "
            "'amount_per_period': '<decimal-str>', 'allocation': {...}}.\n"
            "- MOVING_AVERAGE_CROSSOVER: {'fast_window': <int 2-200>, "
            "'slow_window': <int 2-200, > fast_window>, "
            "'invest_fraction': '<decimal-str in (0, 1]>'}.\n\n"
            "Tickers must be in the supported set (use list_supported_tickers "
            "first). Backend validates parameters server-side; bad shapes "
            "come back as a typed 422 error with field-level detail."
        ),
    )
    async def create_strategy(
        name: str,
        strategy_type: str,
        tickers: list[str],
        parameters: dict[str, Any],
    ) -> Strategy:
        """Create a strategy template."""
        request = CreateStrategyRequest(
            name=name,
            strategy_type=strategy_type,
            tickers=tickers,
            parameters=parameters,
        )
        return await client.create_strategy(request)
