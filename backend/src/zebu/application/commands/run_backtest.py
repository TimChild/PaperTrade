"""RunBacktestCommand - Command for triggering a backtest execution."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)


@dataclass(frozen=True)
class RunBacktestCommand:
    """Command to run a backtest simulation.

    Attributes:
        user_id: ID of the user requesting the backtest
        strategy_id: ID of the strategy to backtest
        backtest_name: Human-readable name for this run
        start_date: First day of the simulation (inclusive)
        end_date: Last day of the simulation (inclusive)
        initial_cash: Starting cash balance in USD
        api_key_id: Phase H2 — ID of the API key that authenticated the
            triggering request, or ``None`` for Clerk Bearer (human via UI).
            Stamped onto the BacktestRun row + the synthetic portfolio +
            its trades so the recent-activity feed can resolve actor
            identity end-to-end.
        agent_invocation_mode: Phase L-1 (Task #217) — operator's choice
            of whether the executor invokes the agent on simulated
            trigger fires. ``NONE`` (default) preserves the pre-Phase-L
            behavior (no agent, no audit rows). ``MOCK`` evaluates
            triggers with a deterministic no-op agent. ``LIVE`` calls
            the real Anthropic adapter via the L-2 backtest-safe
            wrapper. The mode is stamped onto the resulting
            :class:`BacktestRun` row.
    """

    user_id: UUID
    strategy_id: UUID
    backtest_name: str
    start_date: date
    end_date: date
    initial_cash: Decimal
    api_key_id: UUID | None = None
    agent_invocation_mode: BacktestAgentInvocationMode = (
        BacktestAgentInvocationMode.NONE
    )
