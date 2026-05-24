"""RunBacktestCommand - Command for triggering a backtest execution."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from zebu.domain.exceptions import InvalidBacktestCommandError
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
        agent_temperature: Phase L-3 — optional sampling-temperature
            override forwarded to the agent invocation port (and, via
            the L-2 wrapper, to the Anthropic SDK). ``None`` means "use
            the adapter / wrapper default" — the L-2 wrapper defaults
            to ``0.0`` for deterministic-ish replays. Ignored when
            ``agent_invocation_mode`` is ``NONE`` (no agent calls) or
            ``MOCK`` (the mock port is sampling-free).
        agent_max_cost_usd: Phase L-6 — optional per-run USD budget cap
            on LIVE-mode agent invocations. ``None`` (default) preserves
            the L-3 behaviour — no cap, unlimited spend. When set, must
            be ``> 0``. The executor accumulates the dollar cost of each
            LIVE invocation (via the L-6 pricing table) and, once the
            accumulator reaches or exceeds this cap, downgrades all
            subsequent fires in the same run to MOCK so the run
            completes without unbounded further spend. A synthetic
            "BUDGET_EXHAUSTED" audit row is logged at the moment of
            exhaustion so the UI / activity feed can render the
            transition. Ignored when ``agent_invocation_mode`` is not
            ``LIVE`` (MOCK / NONE never incur cost).
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
    agent_temperature: float | None = None
    agent_max_cost_usd: Decimal | None = None

    def __post_init__(self) -> None:
        """Validate cross-field domain invariants.

        ``agent_max_cost_usd`` MUST be strictly positive when set —
        zero or negative caps are nonsensical (zero would halt before
        the first fire; negative is meaningless). ``None`` is the
        documented "no cap" sentinel.
        """
        if self.agent_max_cost_usd is not None and self.agent_max_cost_usd <= 0:
            raise InvalidBacktestCommandError(
                "agent_max_cost_usd must be > 0 (or None for no cap); "
                f"got {self.agent_max_cost_usd}"
            )
