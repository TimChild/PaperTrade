"""Unit tests for :class:`BacktestAgentInvocationAdapter` (Phase L-2 / Task #218).

The wrapper IS-A :class:`AgentInvocationPort`. The tests exercise:

* The safety preamble structurally appears in the system prompt sent to
  the inner port (simulated date inlined; tool list present).
* Caller-supplied ``tools`` are ignored — the wrapper's
  ``BACKTEST_SAFE_TOOLS`` definitions reach the inner unchanged.
* The tool-dispatch callback enforces the whitelist + simulated-date cap.
  Out-of-bounds dates raise :class:`BacktestSafetyViolationError`;
  banned tool names raise the same.
* ``agent_temperature`` plumbs through with the constructor default and
  per-call override.
* The wrapper does NOT touch the Anthropic SDK directly — the inner
  port is the boundary. We inject a fake inner that captures the
  dispatch callback so the test can drive each tool call individually.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from zebu.adapters.outbound.anthropic.backtest_agent_invocation_adapter import (
    BacktestAgentInvocationAdapter,
    _build_safe_tool_definitions,
    _build_safety_preamble,
)
from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.ports.agent_invocation_port import (
    AgentInvocationResult,
    ToolDefinition,
    ToolDispatchCallback,
)
from zebu.application.ports.in_memory_exploration_task_repository import (
    InMemoryExplorationTaskRepository,
)
from zebu.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from zebu.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from zebu.application.queries.get_portfolio_balance import (
    GetPortfolioBalanceHandler,
)
from zebu.domain.entities.exploration_task import (
    ExplorationTask,
    ExplorationTaskStatus,
)
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.exceptions import BacktestSafetyViolationError
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.backtest_safe_tool import (
    BACKTEST_SAFE_TOOL_NAMES,
)
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.ticker import Ticker

# ---------------------------------------------------------------------------
# Fake inner adapter — driver for the tool-use loop
# ---------------------------------------------------------------------------


class _CapturingInnerPort:
    """Test inner :class:`AgentInvocationPort` that captures + replays.

    Holds a *script* of (tool_name, tool_input) calls that the model
    would emit. On :meth:`invoke`:

    * If the script is empty, returns the seeded :class:`AgentInvocationResult`
      immediately (single-shot path — no dispatch callback invoked).
    * If the script has entries, walks each entry by calling
      ``dispatch_tool_call(tool_name, tool_input)`` once per entry — so
      tests can assert the wrapper validated each call. After exhausting
      the script, returns the seeded result.

    This lets the test exercise the wrapper's enforcement WITHOUT
    actually wiring an Anthropic SDK mock — the wrapper's behaviour is
    "construct preamble + tool defs, invoke inner, route dispatches"
    and the boundary we care about is ``inner.invoke``.
    """

    def __init__(
        self,
        *,
        script: list[tuple[str, Mapping[str, object]]] | None = None,
        result: AgentInvocationResult | None = None,
    ) -> None:
        self._script = list(script) if script is not None else []
        self._result = result or AgentInvocationResult(
            decision=AgentDecision.HOLD,
            rationale="default",
            payload={"notes": "default"},
            invocation_id="msg_test",
            latency_ms=42,
            model="claude-test",
        )
        self.invocations: list[
            tuple[str, str, list[ToolDefinition] | None, float, float | None, bool]
        ] = []
        self.tool_results: list[str] = []

    async def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition] | None = None,
        timeout_secs: float = 60.0,
        agent_temperature: float | None = None,
        dispatch_tool_call: ToolDispatchCallback | None = None,
    ) -> AgentInvocationResult:
        self.invocations.append(
            (
                system_prompt,
                user_prompt,
                tools,
                timeout_secs,
                agent_temperature,
                dispatch_tool_call is not None,
            )
        )
        # Replay the script through the wrapper's dispatch callback.
        if self._script:
            if dispatch_tool_call is None:
                raise AssertionError(
                    "Script entries set but no dispatch_tool_call was provided "
                    "by the wrapper — the wrapper MUST supply a callback so "
                    "L-2's safety enforcement runs."
                )
            for name, tool_input in self._script:
                result = await dispatch_tool_call(name, tool_input)
                self.tool_results.append(result)
        return self._result


def _make_safe_balance_handler() -> GetPortfolioBalanceHandler:
    """Build a balance handler with empty repos.

    Sufficient for portfolio_id-not-found tests. Tests that exercise
    the GET_PORTFOLIO_STATE happy path seed a portfolio via the
    returned handler's underlying repos. Constructed once per test to
    keep state isolation.
    """
    portfolio_repo = InMemoryPortfolioRepository()
    transaction_repo = InMemoryTransactionRepository()
    market_data = InMemoryMarketDataAdapter()
    return GetPortfolioBalanceHandler(
        portfolio_repository=portfolio_repo,
        transaction_repository=transaction_repo,
        market_data=market_data,
    )


def _make_wrapper(
    *,
    inner: _CapturingInnerPort,
    simulated_date: date = date(2024, 3, 15),
    market_data: InMemoryMarketDataAdapter | None = None,
    balance_handler: GetPortfolioBalanceHandler | None = None,
    exploration_task_repo: InMemoryExplorationTaskRepository | None = None,
    agent_temperature: float | None = 0.0,
) -> BacktestAgentInvocationAdapter:
    """Assemble a wrapper with defaults appropriate for tests."""
    return BacktestAgentInvocationAdapter(
        inner=inner,
        simulated_date=simulated_date,
        market_data=market_data or InMemoryMarketDataAdapter(),
        portfolio_balance_handler=balance_handler or _make_safe_balance_handler(),
        exploration_task_repo=(
            exploration_task_repo or InMemoryExplorationTaskRepository()
        ),
        agent_temperature=agent_temperature,
    )


# ---------------------------------------------------------------------------
# Safety preamble structure
# ---------------------------------------------------------------------------


class TestSafetyPreambleBuilder:
    """``_build_safety_preamble`` is a pure helper — assert structural shape."""

    def test_preamble_includes_simulated_date_iso(self) -> None:
        text = _build_safety_preamble(date(2024, 3, 15))
        assert "2024-03-15" in text

    def test_preamble_includes_each_safe_tool_name(self) -> None:
        text = _build_safety_preamble(date(2024, 1, 1))
        for name in BACKTEST_SAFE_TOOL_NAMES:
            assert name in text

    def test_preamble_has_backtest_mode_section(self) -> None:
        text = _build_safety_preamble(date(2024, 1, 1))
        assert "BACKTEST MODE" in text

    def test_preamble_mentions_record_decision_terminator(self) -> None:
        text = _build_safety_preamble(date(2024, 1, 1))
        assert "record_decision" in text


class TestSafeToolDefinitionsBuilder:
    """``_build_safe_tool_definitions`` emits exactly the whitelist."""

    def test_exactly_three_tool_definitions(self) -> None:
        defs = _build_safe_tool_definitions(date(2024, 3, 15))
        assert len(defs) == 3

    def test_definitions_match_safe_tool_names(self) -> None:
        defs = _build_safe_tool_definitions(date(2024, 3, 15))
        names = [d.name for d in defs]
        assert names == list(BACKTEST_SAFE_TOOL_NAMES)

    def test_descriptions_mention_simulated_date(self) -> None:
        defs = _build_safe_tool_definitions(date(2024, 3, 15))
        for tool_def in defs:
            assert "2024-03-15" in tool_def.description


# ---------------------------------------------------------------------------
# invoke() — system prompt / tool surface plumbing
# ---------------------------------------------------------------------------


class TestInvokeSystemPromptAndTools:
    """Caller prompts get the safety preamble; caller tools are ignored."""

    async def test_safety_preamble_prepended_to_system_prompt(self) -> None:
        inner = _CapturingInnerPort()
        wrapper = _make_wrapper(inner=inner)

        await wrapper.invoke(
            system_prompt="You are the trading agent.",
            user_prompt="Decide for AAPL.",
        )

        system_prompt_sent = inner.invocations[0][0]
        assert "BACKTEST MODE" in system_prompt_sent
        assert "2024-03-15" in system_prompt_sent
        # Original caller prompt is preserved verbatim AFTER the preamble.
        assert "You are the trading agent." in system_prompt_sent
        assert system_prompt_sent.index("BACKTEST MODE") < system_prompt_sent.index(
            "You are the trading agent."
        )

    async def test_empty_system_prompt_still_receives_preamble(self) -> None:
        inner = _CapturingInnerPort()
        wrapper = _make_wrapper(inner=inner)

        await wrapper.invoke(system_prompt="", user_prompt="u")

        system_prompt_sent = inner.invocations[0][0]
        assert "BACKTEST MODE" in system_prompt_sent

    async def test_caller_supplied_tools_are_ignored(self) -> None:
        """Even if L-3 passed dangerous tools, the wrapper substitutes the whitelist."""
        inner = _CapturingInnerPort()
        wrapper = _make_wrapper(inner=inner)

        await wrapper.invoke(
            system_prompt="s",
            user_prompt="u",
            tools=[
                ToolDefinition(name="evil_tool", description="leaks future data"),
            ],
        )

        tools_sent = inner.invocations[0][2]
        assert tools_sent is not None
        sent_names = [t.name for t in tools_sent]
        assert "evil_tool" not in sent_names
        assert set(sent_names) == set(BACKTEST_SAFE_TOOL_NAMES)

    async def test_dispatch_callback_provided_to_inner(self) -> None:
        """The wrapper MUST supply a dispatch_tool_call so safety enforcement runs."""
        inner = _CapturingInnerPort()
        wrapper = _make_wrapper(inner=inner)

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        # The 6th element of the invocations tuple is dispatch_tool_call_present.
        dispatch_provided = inner.invocations[0][5]
        assert dispatch_provided is True


# ---------------------------------------------------------------------------
# agent_temperature plumbing
# ---------------------------------------------------------------------------


class TestAgentTemperaturePlumbing:
    async def test_constructor_default_temperature_is_zero(self) -> None:
        inner = _CapturingInnerPort()
        wrapper = _make_wrapper(inner=inner)  # default agent_temperature=0.0

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        temp_sent = inner.invocations[0][4]
        assert temp_sent == 0.0

    async def test_constructor_temperature_override(self) -> None:
        inner = _CapturingInnerPort()
        wrapper = _make_wrapper(inner=inner, agent_temperature=0.7)

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        assert inner.invocations[0][4] == 0.7

    async def test_per_call_temperature_override_wins_over_constructor(
        self,
    ) -> None:
        inner = _CapturingInnerPort()
        wrapper = _make_wrapper(inner=inner, agent_temperature=0.0)

        await wrapper.invoke(
            system_prompt="s",
            user_prompt="u",
            agent_temperature=0.4,
        )

        assert inner.invocations[0][4] == 0.4

    async def test_none_constructor_temperature_passes_none(self) -> None:
        """Constructor ``None`` means 'use inner's default'."""
        inner = _CapturingInnerPort()
        wrapper = _make_wrapper(inner=inner, agent_temperature=None)

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        assert inner.invocations[0][4] is None


# ---------------------------------------------------------------------------
# GET_PRICE_HISTORY dispatch
# ---------------------------------------------------------------------------


def _make_aapl_price(*, timestamp: datetime, amount: str = "150.00") -> PricePoint:
    """Build an AAPL daily PricePoint."""
    return PricePoint(
        ticker=Ticker("AAPL"),
        price=Money(Decimal(amount)),
        timestamp=timestamp,
        source="database",
        interval="1day",
    )


class TestDispatchGetPriceHistory:
    async def test_happy_path_within_simulated_date(self) -> None:
        """``end`` < ``simulated_date`` → market data is fetched and returned."""
        market_data = InMemoryMarketDataAdapter()
        market_data.seed_prices(
            [
                _make_aapl_price(
                    timestamp=datetime(2024, 3, 14, 21, 0, tzinfo=UTC),
                    amount="148.00",
                ),
                _make_aapl_price(
                    timestamp=datetime(2024, 3, 13, 21, 0, tzinfo=UTC),
                    amount="146.50",
                ),
            ]
        )
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_price_history",
                    {
                        "ticker": "AAPL",
                        "start": "2024-03-01",
                        "end": "2024-03-14",
                    },
                ),
            ]
        )
        wrapper = _make_wrapper(
            inner=inner,
            simulated_date=date(2024, 3, 15),
            market_data=market_data,
        )

        result = await wrapper.invoke(system_prompt="s", user_prompt="u")

        assert result.decision is AgentDecision.HOLD
        assert len(inner.tool_results) == 1
        parsed = json.loads(inner.tool_results[0])
        assert parsed["ticker"] == "AAPL"
        assert len(parsed["price_points"]) == 2
        # Prices come back in chronological order.
        assert parsed["price_points"][0]["price"] == "146.50"

    async def test_end_equal_to_simulated_date_is_allowed(self) -> None:
        """``end == simulated_date`` end-of-day is the freshest allowed value."""
        market_data = InMemoryMarketDataAdapter()
        market_data.seed_prices(
            [
                _make_aapl_price(
                    timestamp=datetime(2024, 3, 15, 21, 0, tzinfo=UTC),
                ),
            ]
        )
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_price_history",
                    {
                        "ticker": "AAPL",
                        "start": "2024-03-15",
                        "end": "2024-03-15",
                    },
                ),
            ]
        )
        wrapper = _make_wrapper(
            inner=inner,
            simulated_date=date(2024, 3, 15),
            market_data=market_data,
        )

        await wrapper.invoke(system_prompt="s", user_prompt="u")
        # No violation raised — happy path.
        assert len(inner.tool_results) == 1

    async def test_end_after_simulated_date_raises(self) -> None:
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_price_history",
                    {
                        "ticker": "AAPL",
                        "start": "2024-03-01",
                        "end": "2024-03-16",  # one day past simulated_date
                    },
                ),
            ]
        )
        wrapper = _make_wrapper(inner=inner, simulated_date=date(2024, 3, 15))

        with pytest.raises(BacktestSafetyViolationError) as exc_info:
            await wrapper.invoke(system_prompt="s", user_prompt="u")

        assert exc_info.value.tool_name == "get_price_history"
        assert exc_info.value.simulated_date == date(2024, 3, 15)
        assert "exceeds" in exc_info.value.reason.lower()

    async def test_end_omitted_defaults_to_simulated_eod(self) -> None:
        """No ``end`` arg → wrapper defaults to simulated_date end-of-day."""
        market_data = InMemoryMarketDataAdapter()
        market_data.seed_prices(
            [
                _make_aapl_price(
                    timestamp=datetime(2024, 3, 15, 21, 0, tzinfo=UTC),
                ),
            ]
        )
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_price_history",
                    {
                        "ticker": "AAPL",
                        "start": "2024-03-01",
                    },
                ),
            ]
        )
        wrapper = _make_wrapper(
            inner=inner,
            simulated_date=date(2024, 3, 15),
            market_data=market_data,
        )

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        parsed = json.loads(inner.tool_results[0])
        # End-of-day timestamp made it to the underlying adapter.
        assert parsed["end"].startswith("2024-03-15T23:59:59")

    async def test_missing_ticker_raises(self) -> None:
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_price_history",
                    {"start": "2024-03-01", "end": "2024-03-14"},
                ),
            ]
        )
        wrapper = _make_wrapper(inner=inner)

        with pytest.raises(BacktestSafetyViolationError) as exc_info:
            await wrapper.invoke(system_prompt="s", user_prompt="u")
        assert "ticker" in exc_info.value.reason.lower()

    async def test_missing_start_raises(self) -> None:
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_price_history",
                    {"ticker": "AAPL", "end": "2024-03-14"},
                ),
            ]
        )
        wrapper = _make_wrapper(inner=inner)

        with pytest.raises(BacktestSafetyViolationError) as exc_info:
            await wrapper.invoke(system_prompt="s", user_prompt="u")
        assert "start" in exc_info.value.reason.lower()


# ---------------------------------------------------------------------------
# GET_PORTFOLIO_STATE dispatch
# ---------------------------------------------------------------------------


async def _make_portfolio_with_handler(
    *, portfolio_id: UUID
) -> tuple[GetPortfolioBalanceHandler, Portfolio]:
    """Seed a balance handler with one cash-only portfolio."""
    portfolio_repo = InMemoryPortfolioRepository()
    transaction_repo = InMemoryTransactionRepository()
    market_data = InMemoryMarketDataAdapter()
    now = datetime(2024, 3, 15, tzinfo=UTC)
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=uuid4(),
        name="Test Backtest Portfolio",
        portfolio_type=PortfolioType.BACKTEST,
        created_at=now,
    )
    await portfolio_repo.save(portfolio)
    handler = GetPortfolioBalanceHandler(
        portfolio_repository=portfolio_repo,
        transaction_repository=transaction_repo,
        market_data=market_data,
    )
    return handler, portfolio


class TestDispatchGetPortfolioState:
    async def test_happy_path_within_simulated_date(self) -> None:
        portfolio_id = uuid4()
        handler, _portfolio = await _make_portfolio_with_handler(
            portfolio_id=portfolio_id
        )
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_portfolio_state",
                    {
                        "portfolio_id": str(portfolio_id),
                        "as_of": "2024-03-14",
                    },
                ),
            ]
        )
        wrapper = _make_wrapper(
            inner=inner,
            simulated_date=date(2024, 3, 15),
            balance_handler=handler,
        )

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        parsed = json.loads(inner.tool_results[0])
        assert parsed["portfolio_id"] == str(portfolio_id)
        # Cash-only portfolio has zero holdings.
        assert parsed["holdings_value"] == "0.00"

    async def test_as_of_omitted_defaults_to_simulated_eod(self) -> None:
        portfolio_id = uuid4()
        handler, _ = await _make_portfolio_with_handler(portfolio_id=portfolio_id)
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_portfolio_state",
                    {"portfolio_id": str(portfolio_id)},
                ),
            ]
        )
        wrapper = _make_wrapper(
            inner=inner,
            simulated_date=date(2024, 3, 15),
            balance_handler=handler,
        )

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        parsed = json.loads(inner.tool_results[0])
        assert parsed["as_of"].startswith("2024-03-15T23:59:59")

    async def test_as_of_after_simulated_date_raises(self) -> None:
        portfolio_id = uuid4()
        handler, _ = await _make_portfolio_with_handler(portfolio_id=portfolio_id)
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_portfolio_state",
                    {
                        "portfolio_id": str(portfolio_id),
                        "as_of": "2024-03-16",
                    },
                ),
            ]
        )
        wrapper = _make_wrapper(
            inner=inner,
            simulated_date=date(2024, 3, 15),
            balance_handler=handler,
        )

        with pytest.raises(BacktestSafetyViolationError) as exc_info:
            await wrapper.invoke(system_prompt="s", user_prompt="u")
        assert exc_info.value.tool_name == "get_portfolio_state"
        assert "as_of" in exc_info.value.reason.lower()

    async def test_invalid_portfolio_id_raises(self) -> None:
        inner = _CapturingInnerPort(
            script=[
                (
                    "get_portfolio_state",
                    {"portfolio_id": "not-a-uuid"},
                ),
            ]
        )
        wrapper = _make_wrapper(inner=inner)

        with pytest.raises(BacktestSafetyViolationError) as exc_info:
            await wrapper.invoke(system_prompt="s", user_prompt="u")
        assert "uuid" in exc_info.value.reason.lower()

    async def test_missing_portfolio_id_raises(self) -> None:
        inner = _CapturingInnerPort(
            script=[("get_portfolio_state", {})],
        )
        wrapper = _make_wrapper(inner=inner)

        with pytest.raises(BacktestSafetyViolationError) as exc_info:
            await wrapper.invoke(system_prompt="s", user_prompt="u")
        assert "portfolio_id" in exc_info.value.reason


# ---------------------------------------------------------------------------
# LIST_EXPLORATION_TASKS dispatch
# ---------------------------------------------------------------------------


def _make_done_task(
    *,
    claimed_at: datetime,
    created_at: datetime | None = None,
    prompt: str = "research idea",
) -> ExplorationTask:
    """Construct a DONE-status task with the supplied ``claimed_at``."""
    from zebu.domain.entities.exploration_task import (
        ExplorationFindings,
    )

    created = created_at or claimed_at
    findings = ExplorationFindings(
        summary="research summary",
        backtest_run_ids=[],
        strategy_ids=[],
        notes=None,
    )
    return ExplorationTask(
        id=uuid4(),
        created_by=uuid4(),
        prompt=prompt,
        status=ExplorationTaskStatus.DONE,
        created_at=created,
        updated_at=claimed_at,
        claimed_by="agent-x",
        claimed_at=claimed_at,
        findings=findings,
    )


class TestDispatchListExplorationTasks:
    async def test_happy_path_filters_to_claimed_before_cap(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        old = _make_done_task(claimed_at=datetime(2024, 3, 10, tzinfo=UTC))
        recent = _make_done_task(claimed_at=datetime(2024, 3, 14, tzinfo=UTC))
        future = _make_done_task(claimed_at=datetime(2024, 3, 20, tzinfo=UTC))
        for task in (old, recent, future):
            await repo.save(task)

        inner = _CapturingInnerPort(
            script=[("list_exploration_tasks", {})],
        )
        wrapper = _make_wrapper(
            inner=inner,
            simulated_date=date(2024, 3, 15),
            exploration_task_repo=repo,
        )

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        parsed = json.loads(inner.tool_results[0])
        # Default ``claimed_before`` is simulated_eod → filters out future.
        returned_ids = {t["id"] for t in parsed["tasks"]}
        assert str(future.id) not in returned_ids
        assert str(old.id) in returned_ids
        assert str(recent.id) in returned_ids
        assert parsed["status"] == "DONE"

    async def test_claimed_before_explicit_within_cap(self) -> None:
        repo = InMemoryExplorationTaskRepository()
        old = _make_done_task(claimed_at=datetime(2024, 3, 5, tzinfo=UTC))
        mid = _make_done_task(claimed_at=datetime(2024, 3, 10, tzinfo=UTC))
        await repo.save(old)
        await repo.save(mid)

        inner = _CapturingInnerPort(
            script=[
                (
                    "list_exploration_tasks",
                    {"claimed_before": "2024-03-08"},
                ),
            ]
        )
        wrapper = _make_wrapper(
            inner=inner,
            simulated_date=date(2024, 3, 15),
            exploration_task_repo=repo,
        )

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        parsed = json.loads(inner.tool_results[0])
        returned_ids = {t["id"] for t in parsed["tasks"]}
        assert str(old.id) in returned_ids
        assert str(mid.id) not in returned_ids

    async def test_claimed_before_after_simulated_date_raises(self) -> None:
        inner = _CapturingInnerPort(
            script=[
                (
                    "list_exploration_tasks",
                    {"claimed_before": "2024-03-16"},
                ),
            ]
        )
        wrapper = _make_wrapper(inner=inner, simulated_date=date(2024, 3, 15))

        with pytest.raises(BacktestSafetyViolationError) as exc_info:
            await wrapper.invoke(system_prompt="s", user_prompt="u")
        assert exc_info.value.tool_name == "list_exploration_tasks"
        assert "claimed_before" in exc_info.value.reason


# ---------------------------------------------------------------------------
# Banned tool rejection
# ---------------------------------------------------------------------------


class TestBannedToolRejection:
    """Tools NOT in BACKTEST_SAFE_TOOLS must raise on dispatch."""

    @pytest.mark.parametrize(
        "banned_name",
        [
            "web_search",
            "fetch_news",
            "get_current_price",  # real-time leak
            "create_strategy",  # write tool
            "run_backtest",  # write tool
            "this_does_not_exist",
        ],
    )
    async def test_banned_tool_raises(self, banned_name: str) -> None:
        inner = _CapturingInnerPort(
            script=[(banned_name, {"query": "anything"})],
        )
        wrapper = _make_wrapper(inner=inner)

        with pytest.raises(BacktestSafetyViolationError) as exc_info:
            await wrapper.invoke(system_prompt="s", user_prompt="u")

        assert exc_info.value.tool_name == banned_name
        assert "BACKTEST_SAFE_TOOLS" in exc_info.value.reason


# ---------------------------------------------------------------------------
# No-tool-call path + multi-call ordering
# ---------------------------------------------------------------------------


class TestEndToEndLoop:
    async def test_no_tool_calls_returns_unmodified(self) -> None:
        """Agent emits record_decision immediately → wrapper returns result intact."""
        seeded = AgentInvocationResult(
            decision=AgentDecision.BUY,
            rationale="confidence high",
            payload={"ticker": "AAPL", "quantity": "10", "notes": "buy"},
            invocation_id="msg_immediate",
            latency_ms=123,
            model="claude-test",
        )
        inner = _CapturingInnerPort(script=[], result=seeded)
        wrapper = _make_wrapper(inner=inner)

        result = await wrapper.invoke(system_prompt="s", user_prompt="u")

        # Result flows through unmodified.
        assert result is seeded
        assert result.decision is AgentDecision.BUY
        assert result.rationale == "confidence high"
        assert inner.tool_results == []

    async def test_multi_call_ordering_is_preserved(self) -> None:
        """Several safe tool calls dispatch in script order."""
        repo = InMemoryExplorationTaskRepository()
        market_data = InMemoryMarketDataAdapter()
        market_data.seed_prices(
            [
                _make_aapl_price(
                    timestamp=datetime(2024, 3, 14, 21, 0, tzinfo=UTC),
                ),
            ]
        )
        portfolio_id = uuid4()
        handler, _ = await _make_portfolio_with_handler(portfolio_id=portfolio_id)

        inner = _CapturingInnerPort(
            script=[
                (
                    "get_price_history",
                    {
                        "ticker": "AAPL",
                        "start": "2024-03-01",
                        "end": "2024-03-14",
                    },
                ),
                (
                    "get_portfolio_state",
                    {"portfolio_id": str(portfolio_id)},
                ),
                ("list_exploration_tasks", {}),
            ]
        )
        wrapper = _make_wrapper(
            inner=inner,
            simulated_date=date(2024, 3, 15),
            market_data=market_data,
            balance_handler=handler,
            exploration_task_repo=repo,
        )

        await wrapper.invoke(system_prompt="s", user_prompt="u")

        assert len(inner.tool_results) == 3
        prices = json.loads(inner.tool_results[0])
        balances = json.loads(inner.tool_results[1])
        tasks = json.loads(inner.tool_results[2])
        assert prices["ticker"] == "AAPL"
        assert balances["portfolio_id"] == str(portfolio_id)
        assert tasks["status"] == "DONE"

    async def test_violation_aborts_before_subsequent_calls(self) -> None:
        """A safety violation early in the loop blocks the remaining script.

        The wrapper must NOT silently continue past a violation — if the
        agent's first call is bad, the run fails and the rest of the
        script is discarded.
        """
        inner = _CapturingInnerPort(
            script=[
                ("web_search", {"query": "anything"}),  # violation
                # This second call should NEVER fire — the prior raise
                # propagates out of the wrapper.
                ("get_price_history", {"ticker": "AAPL", "start": "2024-03-01"}),
            ]
        )
        wrapper = _make_wrapper(inner=inner)

        with pytest.raises(BacktestSafetyViolationError):
            await wrapper.invoke(system_prompt="s", user_prompt="u")

        # Only one tool dispatch was attempted; the second was never reached.
        assert len(inner.tool_results) == 0
