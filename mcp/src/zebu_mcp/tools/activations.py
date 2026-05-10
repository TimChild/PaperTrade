"""Strategy-activation read + lifecycle tools."""

from __future__ import annotations

from uuid import UUID

from mcp.server.fastmcp import FastMCP

from zebu_mcp.client import ZebuClient
from zebu_mcp.schemas import (
    ActivateStrategyRequest,
    DeactivateActivationRequest,
    Page,
    RunNowResponse,
    StrategyActivation,
)


def register(server: FastMCP, client: ZebuClient) -> None:
    """Register activation tools on ``server``."""

    @server.tool(
        name="list_active_strategies",
        description=(
            "List the user's currently ACTIVE strategy activations. An "
            "activation links a strategy to a portfolio for daily live "
            "execution by the scheduler. This tool is a convenience filter "
            "over list_activations(status=ACTIVE) — use it when you want "
            "to know 'what strategies are running right now?'. The status "
            "filter is applied client-side, so 'total' reflects ACTIVE "
            "activations within the current page only."
        ),
    )
    async def list_active_strategies(
        limit: int = 20,
        offset: int = 0,
    ) -> Page[StrategyActivation]:
        """List ACTIVE strategy activations."""
        return await client.list_active_activations(limit=limit, offset=offset)

    @server.tool(
        name="get_activation",
        description=(
            "Fetch a single strategy activation. Pass either strategy_id "
            "(returns 'the' activation for that strategy — note that a "
            "strategy can only have one activation at a time) OR the "
            "activation_id directly. Exactly one of the two must be "
            "supplied; supplying both is an error."
        ),
    )
    async def get_activation(
        strategy_id: UUID | None = None,
        activation_id: UUID | None = None,
    ) -> StrategyActivation:
        """Fetch one activation by strategy ID or activation ID.

        Phase D Wave 1: only the by-strategy lookup is exercised because
        the backend doesn't currently expose a per-activation GET. When
        ``activation_id`` is supplied, we list activations and find by
        ID — fine for Wave 1 volume, will warrant a real endpoint later.
        """
        if strategy_id is None and activation_id is None:
            raise ValueError(
                "get_activation requires either strategy_id or activation_id"
            )
        if strategy_id is not None and activation_id is not None:
            raise ValueError(
                "get_activation accepts only one of strategy_id or "
                "activation_id, not both"
            )
        if strategy_id is not None:
            return await client.get_strategy_activation(strategy_id)

        # activation_id path: paginate until we find it. Activation
        # volume is small per user (one per strategy) so this is fine.
        # When the backend exposes a per-activation GET endpoint, swap
        # to a single round-trip.
        assert activation_id is not None  # for the type checker
        offset = 0
        page_size = 100
        while True:
            page = await client.list_activations(limit=page_size, offset=offset)
            for activation in page.items:
                if activation.id == activation_id:
                    return activation
            if not page.has_more:
                break
            offset += page_size
        # Mimic the API's 404 by raising; the agent gets a clear failure.
        raise LookupError(f"Activation not found: {activation_id}")

    @server.tool(
        name="activate_strategy",
        description=(
            "Activate a strategy for live execution against a portfolio. "
            "The strategy and portfolio must both belong to the caller. "
            "frequency is the execution cadence — Phase C1 ships only "
            "DAILY_MARKET_CLOSE. Returns the new activation in ACTIVE "
            "status; subsequent scheduler ticks will execute it.\n\n"
            "Returns 409 if the strategy already has an ACTIVE activation "
            "(deactivate it first to re-activate against a different "
            "portfolio)."
        ),
    )
    async def activate_strategy(
        strategy_id: UUID,
        portfolio_id: UUID,
        frequency: str = "DAILY_MARKET_CLOSE",
    ) -> StrategyActivation:
        """Activate a strategy on a portfolio."""
        request = ActivateStrategyRequest(
            portfolio_id=portfolio_id,
            frequency=frequency,
        )
        return await client.activate_strategy(strategy_id, request)

    @server.tool(
        name="deactivate_activation",
        description=(
            "Pause an active activation. Sets status=PAUSED so the "
            "scheduler skips it on subsequent cycles. The optional reason "
            "is stored for UI display (currently piggybacks the entity's "
            "last_error field)."
        ),
    )
    async def deactivate_activation(
        activation_id: UUID,
        reason: str | None = None,
    ) -> StrategyActivation:
        """Pause an active strategy activation."""
        request = DeactivateActivationRequest(reason=reason)
        return await client.deactivate_activation(activation_id, request)

    @server.tool(
        name="run_activation_now",
        description=(
            "Trigger immediate execution of an activation outside its "
            "configured cadence. Useful for an agent that just created an "
            "activation and wants to see it execute immediately, or for "
            "ad-hoc one-off runs. Runs synchronously in the backend "
            "handler.\n\n"
            "Returns the post-run activation state plus the immediate "
            "outcome (succeeded, trades, error). Status may have flipped "
            "to ERROR if the run failed; trades reports the count of "
            "transactions written. Bypasses the activation's status — a "
            "PAUSED activation can be ad-hoc run; only the cron-driven "
            "scheduler respects status."
        ),
    )
    async def run_activation_now(activation_id: UUID) -> RunNowResponse:
        """Run an activation immediately."""
        return await client.run_activation_now(activation_id)
