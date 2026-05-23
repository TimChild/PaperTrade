"""Production :class:`BacktestAgentInvocationFactory` (Anthropic-backed).

Phase L-3 (Task #219). Builds the per-simulated-day
:class:`AgentInvocationPort` instances the :class:`BacktestExecutor`
uses on simulated trigger fires.

For ``LIVE`` mode, the factory constructs a fresh
:class:`BacktestAgentInvocationAdapter` (L-2 wrapper) pinned to
``simulated_date`` around the shared inner
:class:`AnthropicAgentInvocationAdapter`. For ``MOCK`` mode, it returns
a single shared :class:`MockBacktestAgentInvocationPort` (it's stateless
so sharing is safe — each call is a no-op). ``NONE`` is a programming
error from this factory's perspective: the executor should never have
gotten here.

The factory lives in adapters/outbound/anthropic because it owns the
production wiring decision (which SDK adapter to use, which downstream
ports to inject). The executor only sees the
:class:`BacktestAgentInvocationFactory` Protocol.
"""

from __future__ import annotations

from datetime import date

from zebu.adapters.outbound.anthropic.agent_invocation_adapter import (
    AnthropicAgentInvocationAdapter,
)
from zebu.adapters.outbound.anthropic.backtest_agent_invocation_adapter import (
    BacktestAgentInvocationAdapter,
)
from zebu.application.ports.agent_invocation_port import AgentInvocationPort
from zebu.application.ports.exploration_task_repository import (
    ExplorationTaskRepository,
)
from zebu.application.ports.in_memory_agent_invocation_port import (
    MockBacktestAgentInvocationPort,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.queries.get_portfolio_balance import (
    GetPortfolioBalanceHandler,
)
from zebu.domain.value_objects.backtest_agent_invocation_mode import (
    BacktestAgentInvocationMode,
)


class AnthropicBacktestAgentInvocationFactory:
    """Production :class:`BacktestAgentInvocationFactory` implementation.

    Builds the L-2 backtest-safe wrapper for LIVE mode and reuses a
    single :class:`MockBacktestAgentInvocationPort` for MOCK mode.
    NONE raises (the executor should short-circuit before calling).

    Construction-time dependencies:

    Attributes:
        _inner: The shared :class:`AnthropicAgentInvocationAdapter`
            that the L-2 wrapper delegates to. One instance is reused
            across every LIVE-mode simulated fire — the SDK's async
            client is connection-pooled so this is the right shape.
        _market_data: Forwarded into the L-2 wrapper for
            ``GET_PRICE_HISTORY`` dispatch.
        _portfolio_balance_handler: Forwarded into the L-2 wrapper for
            ``GET_PORTFOLIO_STATE`` dispatch.
        _exploration_task_repo: Forwarded into the L-2 wrapper for
            ``LIST_EXPLORATION_TASKS`` dispatch.
        _mock_port: Reused singleton for MOCK-mode callers; the port
            is stateless, so a single instance is fine.
    """

    def __init__(
        self,
        *,
        inner: AnthropicAgentInvocationAdapter,
        market_data: MarketDataPort,
        portfolio_balance_handler: GetPortfolioBalanceHandler,
        exploration_task_repo: ExplorationTaskRepository,
    ) -> None:
        """Initialise the production factory.

        Args:
            inner: Shared :class:`AnthropicAgentInvocationAdapter` —
                typically the one already used by the live trigger
                orchestrator (so prompt-caching tokens are shared).
            market_data: Market-data adapter for tool dispatch.
            portfolio_balance_handler: Balance-query handler for tool
                dispatch.
            exploration_task_repo: Exploration-task repo for tool
                dispatch.
        """
        self._inner = inner
        self._market_data = market_data
        self._portfolio_balance_handler = portfolio_balance_handler
        self._exploration_task_repo = exploration_task_repo
        self._mock_port = MockBacktestAgentInvocationPort()

    def for_simulated_date(
        self,
        *,
        simulated_date: date,
        mode: BacktestAgentInvocationMode,
        agent_temperature: float | None,
    ) -> AgentInvocationPort:
        """Build the per-fire port based on ``mode``.

        Args:
            simulated_date: Bound onto the L-2 wrapper for LIVE so the
                wrapper rejects tool calls outside the simulated-date
                cap.
            mode: ``LIVE`` constructs a fresh L-2 wrapper, ``MOCK``
                returns the singleton mock port, ``NONE`` raises.
            agent_temperature: Forwarded to the L-2 wrapper for LIVE
                (``None`` defers to the wrapper's default 0.0).
                Ignored on MOCK.

        Returns:
            The :class:`AgentInvocationPort` for this fire.

        Raises:
            ValueError: If ``mode`` is
                :class:`BacktestAgentInvocationMode.NONE`. The
                executor should never reach the factory in NONE mode;
                a raise here flags a wiring bug loudly.
        """
        if mode is BacktestAgentInvocationMode.LIVE:
            # Fresh wrapper per fire — binds ``simulated_date`` at
            # construction time so the L-2 enforcement is per-call
            # accurate. Reusing across days would entangle date
            # semantics with instance lifecycle.
            return BacktestAgentInvocationAdapter(
                inner=self._inner,
                simulated_date=simulated_date,
                market_data=self._market_data,
                portfolio_balance_handler=self._portfolio_balance_handler,
                exploration_task_repo=self._exploration_task_repo,
                agent_temperature=agent_temperature
                if agent_temperature is not None
                else 0.0,
            )
        if mode is BacktestAgentInvocationMode.MOCK:
            # Stateless — share the singleton.
            return self._mock_port
        raise ValueError(
            "BacktestAgentInvocationFactory.for_simulated_date called "
            f"with mode={mode.value}; callers MUST short-circuit on NONE."
        )


__all__ = ["AnthropicBacktestAgentInvocationFactory"]
