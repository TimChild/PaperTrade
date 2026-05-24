"""Tests for BacktestExecutor."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.commands.run_backtest import RunBacktestCommand
from zebu.application.ports.in_memory_backtest_agent_invocation_factory import (
    InMemoryBacktestAgentInvocationFactory,
)
from zebu.application.ports.in_memory_backtest_agent_invocation_repository import (
    InMemoryBacktestAgentInvocationRepository,
)
from zebu.application.ports.in_memory_backtest_run_repository import (
    InMemoryBacktestRunRepository,
)
from zebu.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from zebu.application.ports.in_memory_snapshot_repository import (
    InMemorySnapshotRepository,
)
from zebu.application.ports.in_memory_strategy_activation_repository import (
    InMemoryStrategyActivationRepository,
)
from zebu.application.ports.in_memory_strategy_repository import (
    InMemoryStrategyRepository,
)
from zebu.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from zebu.application.ports.in_memory_trigger_repository import (
    InMemoryTriggerRepository,
)
from zebu.application.services.backtest_executor import BacktestExecutor
from zebu.application.services.historical_data_preparer import HistoricalDataPreparer
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.domain.entities.strategy import Strategy
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.backtest_status import BacktestStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.strategy_parameters import BuyAndHoldParameters
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker


def _make_strategy(user_id, tickers=None, allocation=None):
    tickers = tickers or ["AAPL"]
    raw_allocation = allocation or {"AAPL": 1.0}
    decimal_allocation = {k: Decimal(str(v)) for k, v in raw_allocation.items()}
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=tickers,
        parameters=BuyAndHoldParameters(allocation=decimal_allocation),
        created_at=datetime.now(UTC),
    )


def _seed_daily_prices(
    adapter: InMemoryMarketDataAdapter,
    ticker: str,
    start: date,
    end: date,
    price: Decimal = Decimal("100.00"),
) -> None:
    current = start
    while current <= end:
        ts = datetime(current.year, current.month, current.day, 12, 0, 0, tzinfo=UTC)
        adapter.seed_price(
            PricePoint(
                ticker=Ticker(ticker),
                price=Money(price, "USD"),
                timestamp=ts,
                source="database",
                interval="1day",
            )
        )
        current += timedelta(days=1)


def _build_executor(
    strategy_repo,
    backtest_run_repo,
    portfolio_repo=None,
    transaction_repo=None,
    snapshot_repo=None,
    market_data=None,
    activation_repo=None,
    trigger_repo=None,
    backtest_agent_invocation_repo=None,
    agent_invocation_factory=None,
):
    portfolio_repo = portfolio_repo or InMemoryPortfolioRepository()
    transaction_repo = transaction_repo or InMemoryTransactionRepository()
    snapshot_repo = snapshot_repo or InMemorySnapshotRepository()
    market_data = market_data or InMemoryMarketDataAdapter()
    activation_repo = activation_repo or InMemoryStrategyActivationRepository()
    trigger_repo = trigger_repo or InMemoryTriggerRepository()
    backtest_agent_invocation_repo = (
        backtest_agent_invocation_repo or InMemoryBacktestAgentInvocationRepository()
    )
    # Default factory has no live port — happy-path tests run with
    # mode=NONE and never hit it; the MOCK branch is still callable.
    agent_invocation_factory = (
        agent_invocation_factory or InMemoryBacktestAgentInvocationFactory()
    )

    snapshot_service = SnapshotJobService(
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        snapshot_repo=snapshot_repo,
        market_data=market_data,
    )
    data_preparer = HistoricalDataPreparer(market_data=market_data)

    return BacktestExecutor(
        portfolio_repo=portfolio_repo,
        transaction_repo=transaction_repo,
        strategy_repo=strategy_repo,
        backtest_run_repo=backtest_run_repo,
        snapshot_service=snapshot_service,
        snapshot_repo=snapshot_repo,
        data_preparer=data_preparer,
        activation_repo=activation_repo,
        trigger_repo=trigger_repo,
        backtest_agent_invocation_repo=backtest_agent_invocation_repo,
        agent_invocation_factory=agent_invocation_factory,
    )


class TestBacktestExecutor:
    """Tests for BacktestExecutor.execute()."""

    async def test_completed_backtest_has_completed_status(self) -> None:
        """Successful backtest ends with COMPLETED status."""
        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 5)
        _seed_daily_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Test Backtest",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        assert result.total_trades is not None
        assert result.completed_at is not None

    async def test_missing_strategy_raises_error(self) -> None:
        """Backtest with missing strategy raises InvalidStrategyError."""
        from zebu.domain.exceptions import InvalidStrategyError

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=uuid4(),  # non-existent
            backtest_name="Test",
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 5),
            initial_cash=Decimal("10000"),
        )

        with pytest.raises(InvalidStrategyError):
            await executor.execute(command)

    async def test_backtest_creates_portfolio(self) -> None:
        """Backtest creates a BACKTEST-type portfolio."""
        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        portfolio_repo = InMemoryPortfolioRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 3)
        _seed_daily_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            portfolio_repo=portfolio_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Test",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("5000"),
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        portfolio = await portfolio_repo.get(result.portfolio_id)
        assert portfolio is not None
        from zebu.domain.value_objects.portfolio_type import PortfolioType

        assert portfolio.portfolio_type == PortfolioType.BACKTEST

    async def test_buy_and_hold_executes_trade_on_day1(self) -> None:
        """Buy and hold strategy executes at least one trade."""
        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        transaction_repo = InMemoryTransactionRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 5)
        _seed_daily_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            transaction_repo=transaction_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Test",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        assert result.total_trades is not None
        assert result.total_trades >= 1


# --------------------------------------------------------------------------- #
# Phase L-3 — agent-invocation pipeline integration                           #
# --------------------------------------------------------------------------- #


def _seed_dropping_prices(
    adapter: InMemoryMarketDataAdapter,
    ticker: str,
    start: date,
    end: date,
    start_price: Decimal = Decimal("100.00"),
    drop_per_day: Decimal = Decimal("2.00"),
) -> None:
    """Seed prices that drop linearly so a drawdown trigger can fire.

    Used by L-3 tests that need the PER_TICKER drawdown evaluator to
    see a drawdown crossing the threshold.
    """
    current = start
    current_price = start_price
    while current <= end:
        ts = datetime(current.year, current.month, current.day, 12, 0, 0, tzinfo=UTC)
        adapter.seed_price(
            PricePoint(
                ticker=Ticker(ticker),
                price=Money(current_price, "USD"),
                timestamp=ts,
                source="database",
                interval="1day",
            )
        )
        current += timedelta(days=1)
        current_price -= drop_per_day


def _make_dca_strategy(user_id):
    """Build a DCA strategy whose buys leave cash for the agent to act on.

    Default: $100 per period, every 30 days — over a 9-day backtest
    only one DCA buy fires, leaving plenty of cash for an agent BUY
    to land.
    """
    from zebu.domain.value_objects.strategy_parameters import DcaParameters

    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="DCA AAPL",
        strategy_type=StrategyType.DOLLAR_COST_AVERAGING,
        tickers=["AAPL"],
        parameters=DcaParameters(
            frequency_days=30,
            amount_per_period=Decimal("100"),
            allocation={"AAPL": Decimal("1.0")},
        ),
        created_at=datetime.now(UTC),
    )


def _make_drawdown_trigger(
    user_id,
    activation_id,
    *,
    threshold_pct: str = "5",
    lookback_days: int = 30,
    cooldown_seconds: int = 86400,
    priority: int = 0,
):
    """Build a PER_TICKER drawdown trigger for L-3 tests."""
    from zebu.domain.entities.strategy_condition_trigger import (
        StrategyConditionTrigger,
    )
    from zebu.domain.value_objects.trigger_condition import (
        ConditionType,
        DrawdownMetric,
        DrawdownParams,
    )
    from zebu.domain.value_objects.trigger_status import TriggerStatus

    when = datetime.now(UTC) - timedelta(days=10)
    return StrategyConditionTrigger(
        id=uuid4(),
        activation_id=activation_id,
        user_id=user_id,
        condition_type=ConditionType.DRAWDOWN_THRESHOLD,
        condition_params=DrawdownParams(
            threshold_pct=Decimal(threshold_pct),
            lookback_days=lookback_days,
            metric=DrawdownMetric.PER_TICKER,
        ),
        agent_prompt=("A meaningful drawdown was detected. Decide what to do next."),
        status=TriggerStatus.ACTIVE,
        priority=priority,
        cooldown_seconds=cooldown_seconds,
        last_fired_at=None,
        created_at=when,
        updated_at=when,
        created_by=user_id,
    )


def _make_active_activation(user_id, strategy_id, portfolio_id):
    """Build an ACTIVE StrategyActivation for L-3 tests."""
    from zebu.domain.entities.strategy_activation import StrategyActivation
    from zebu.domain.value_objects.activation_frequency import ActivationFrequency

    when = datetime.now(UTC) - timedelta(days=5)
    return StrategyActivation(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy_id,
        portfolio_id=portfolio_id,
        status=ActivationStatus.ACTIVE,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=when,
        updated_at=when,
    )


class TestBacktestExecutorAgentInvocation:
    """Phase L-3 tests for the agent-invocation pipeline integration."""

    async def test_none_mode_skips_trigger_evaluation_entirely(self) -> None:
        """With mode=NONE (default), no audit rows are written even if triggers exist.

        A strategy with an attached trigger should behave identically to
        the pre-L-3 executor when the run is configured for NONE mode.
        """
        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 10)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)

        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id)
        await trigger_repo.save(trigger)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="None-mode",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            # agent_invocation_mode defaults to NONE
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        # No audit rows written for the run.
        rows = await invocation_repo.list_for_backtest_run(result.id)
        assert rows == []

    async def test_mock_mode_persists_audit_rows_with_hold_decisions(self) -> None:
        """MOCK mode evaluates triggers, dispatches mock port, persists HOLD rows."""
        from zebu.domain.value_objects.agent_decision import AgentDecision
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 12)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)

        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(
            user_id, activation.id, threshold_pct="3", cooldown_seconds=86400
        )
        await trigger_repo.save(trigger)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Mock-mode",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.MOCK,
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        assert len(rows) >= 1, (
            "Drawdown trigger should have fired at least once with a 3% "
            "threshold and prices dropping 2%/day."
        )
        for row in rows:
            assert row.invocation_mode is BacktestAgentInvocationMode.MOCK
            assert row.agent_decision is AgentDecision.HOLD
            assert row.decision_executed is False
            assert row.simulated_trade_id is None
            assert row.rationale == ""
            assert row.model == ""

    async def test_mock_mode_byte_stable_across_two_runs(self) -> None:
        """Same backtest run twice with mode=MOCK produces identical totals."""
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 8)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        executor1 = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=InMemoryBacktestAgentInvocationRepository(),
            market_data=adapter,
        )
        executor2 = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=InMemoryBacktestAgentInvocationRepository(),
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Byte-stability",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.MOCK,
        )

        result1 = await executor1.execute(command)
        result2 = await executor2.execute(command)

        # MOCK mode is byte-stable per design — only the run IDs differ.
        assert result1.total_trades == result2.total_trades
        assert result1.total_return_pct == result2.total_return_pct
        assert result1.max_drawdown_pct == result2.max_drawdown_pct

    async def test_live_buy_decision_produces_simulated_trade(self) -> None:
        """LIVE mode + scripted BUY produces a simulated trade + executed audit row.

        Uses a DCA strategy (sparse, $100 / 30d) so the builder retains
        cash for the agent's BUY to land. Buy-and-hold consumes all
        cash on day 1, which would make the agent's BUY fail by
        insufficient funds — that's the SELL-rejection test scenario,
        not the executable-BUY scenario.
        """
        from zebu.application.ports.in_memory_agent_invocation_port import (
            StaticAgentInvocationPort,
            make_result,
        )
        from zebu.domain.value_objects.agent_decision import AgentDecision
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        transaction_repo = InMemoryTransactionRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 12)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_dca_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        buy_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.BUY,
                rationale="Drawdown looked recoverable; buying the dip.",
                payload={"ticker": "AAPL", "quantity": "1", "notes": "Test BUY"},
            )
        )
        factory = InMemoryBacktestAgentInvocationFactory(
            live_port_factory=lambda: buy_port
        )

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            transaction_repo=transaction_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Live-buy",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        assert len(rows) >= 1
        # At least one row should be an executed BUY referencing a transaction.
        executed_buys = [
            r
            for r in rows
            if r.agent_decision is AgentDecision.BUY and r.decision_executed
        ]
        assert len(executed_buys) >= 1
        first_buy = executed_buys[0]
        assert first_buy.simulated_trade_id is not None
        assert first_buy.invocation_mode is BacktestAgentInvocationMode.LIVE
        assert first_buy.model != ""
        # The agent's port was actually called.
        assert len(buy_port.invocations) >= 1

    async def test_live_sell_on_empty_holdings_downgrades_to_hold(self) -> None:
        """LIVE mode SELL exceeding holdings is downgraded to HOLD."""
        from zebu.application.ports.in_memory_agent_invocation_port import (
            StaticAgentInvocationPort,
            make_result,
        )
        from zebu.domain.value_objects.agent_decision import AgentDecision
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 10)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        # DCA-like strategy that doesn't auto-buy on day 1 — but easier:
        # use a buy-and-hold but SELL a quantity that exceeds holdings.
        # Actually simpler: use a SELL of 100 shares (will fail).
        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        # SELL 1000 shares — buy-and-hold buys ~100 shares of AAPL at $100,
        # so 1000-share SELL will be insufficient.
        sell_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.SELL,
                rationale="Locking in profits early.",
                payload={"ticker": "AAPL", "quantity": "1000", "notes": "Test SELL"},
            )
        )
        factory = InMemoryBacktestAgentInvocationFactory(
            live_port_factory=lambda: sell_port
        )

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Live-sell-fail",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        # All SELL attempts should have been downgraded to HOLD audit rows.
        sell_rows = [r for r in rows if r.agent_decision is AgentDecision.SELL]
        hold_rows = [r for r in rows if r.agent_decision is AgentDecision.HOLD]
        assert sell_rows == []
        assert len(hold_rows) >= 1
        # Rationale should record the downgrade reason.
        assert any("SELL downgraded to HOLD" in r.rationale for r in hold_rows)

    async def test_live_modify_strategy_records_audit_only(self) -> None:
        """MODIFY_STRATEGY is record-only in backtest — no strategy mutation."""
        from zebu.application.ports.in_memory_agent_invocation_port import (
            StaticAgentInvocationPort,
            make_result,
        )
        from zebu.domain.value_objects.agent_decision import AgentDecision
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 10)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        original_params = strategy.parameters
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        modify_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.MODIFY_STRATEGY,
                rationale="Want to change the allocation.",
                payload={
                    "parameter_overrides": {"allocation": {"AAPL": "0.5"}},
                    "notes": "Test MODIFY",
                },
            )
        )
        factory = InMemoryBacktestAgentInvocationFactory(
            live_port_factory=lambda: modify_port
        )

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Live-modify",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        modify_rows = [
            r for r in rows if r.agent_decision is AgentDecision.MODIFY_STRATEGY
        ]
        assert len(modify_rows) >= 1
        for row in modify_rows:
            # Record-only — never executed in backtest.
            assert row.decision_executed is False
            assert row.simulated_trade_id is None

        # Strategy must NOT have been mutated by the backtest.
        reloaded = await strategy_repo.get(strategy.id)
        assert reloaded is not None
        assert reloaded.parameters == original_params

    async def test_live_safety_violation_records_invocation_failed(self) -> None:
        """BacktestSafetyViolationError surfaces as an INVOCATION_FAILED audit row."""
        from zebu.application.ports.agent_invocation_port import (
            AgentInvocationResult,
            ToolDefinition,
            ToolDispatchCallback,
        )
        from zebu.domain.exceptions import BacktestSafetyViolationError
        from zebu.domain.value_objects.agent_decision import AgentDecision
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        class _ViolatingPort:
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
                del system_prompt, user_prompt, tools
                del timeout_secs, agent_temperature, dispatch_tool_call
                raise BacktestSafetyViolationError(
                    tool_name="get_current_price",
                    simulated_date=date(2024, 1, 5),
                    reason="banned tool surfaced to the agent",
                )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 8)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        factory = InMemoryBacktestAgentInvocationFactory(
            live_port_factory=lambda: _ViolatingPort()
        )

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Live-safety-violation",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        assert len(rows) >= 1
        for row in rows:
            assert row.agent_decision is AgentDecision.INVOCATION_FAILED
            assert row.decision_executed is False
            assert "BacktestSafetyViolationError" in row.rationale

    async def test_cooldown_blocks_consecutive_fires(self) -> None:
        """A trigger fires once, then is cooldown-blocked on the next eligible day."""
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        # Need ~7 days of dropping prices so multiple days satisfy the
        # drawdown threshold; with 86400s cooldown only every other day
        # is eligible.
        start = date(2024, 1, 2)
        end = date(2024, 1, 10)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        # 3-day cooldown (259200s) — over a 9-day window the trigger
        # can fire at most 3 times.
        trigger = _make_drawdown_trigger(
            user_id, activation.id, threshold_pct="3", cooldown_seconds=259200
        )
        await trigger_repo.save(trigger)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Cooldown",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.MOCK,
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        # 9 calendar days / 3-day cooldown = at most 3 fires.
        # And each fire's simulated_date should be at least 3 days apart.
        assert len(rows) <= 4, (
            f"Expected at most ~3-4 fires under 3-day cooldown over a "
            f"9-day window, got {len(rows)}"
        )
        if len(rows) >= 2:
            # Check fires are spaced.
            ordered = sorted(rows, key=lambda r: r.simulated_date)
            for prev, current in zip(ordered, ordered[1:], strict=False):
                gap_days = (current.simulated_date - prev.simulated_date).days
                assert gap_days >= 3, (
                    f"Cooldown violated: fires {gap_days} days apart "
                    "(min 3 days required)"
                )

    async def test_inactive_activation_excluded_from_universe(self) -> None:
        """A PAUSED activation's triggers are NOT evaluated in backtest."""
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 10)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()

        # PAUSED activation — its triggers should be excluded.
        from zebu.domain.entities.strategy_activation import StrategyActivation
        from zebu.domain.value_objects.activation_frequency import ActivationFrequency

        when = datetime.now(UTC) - timedelta(days=5)
        paused_activation = StrategyActivation(
            id=uuid4(),
            user_id=user_id,
            strategy_id=strategy.id,
            portfolio_id=portfolio_id,
            status=ActivationStatus.PAUSED,
            frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
            created_at=when,
            updated_at=when,
        )
        await activation_repo.save(paused_activation)

        trigger = _make_drawdown_trigger(
            user_id, paused_activation.id, threshold_pct="3"
        )
        await trigger_repo.save(trigger)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Paused-activation",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.MOCK,
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        assert rows == [], (
            "Triggers on PAUSED activations must not be evaluated; "
            f"got {len(rows)} rows."
        )

    async def test_earnings_proximity_trigger_is_skipped_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Earnings-proximity triggers log a warning and don't produce audit rows."""
        from zebu.domain.entities.strategy_condition_trigger import (
            StrategyConditionTrigger,
        )
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )
        from zebu.domain.value_objects.trigger_condition import (
            ConditionType,
            EarningsParams,
        )
        from zebu.domain.value_objects.trigger_status import TriggerStatus

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 8)
        _seed_daily_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)

        when = datetime.now(UTC) - timedelta(days=10)
        earnings_trigger = StrategyConditionTrigger(
            id=uuid4(),
            activation_id=activation.id,
            user_id=user_id,
            condition_type=ConditionType.EARNINGS_PROXIMITY,
            condition_params=EarningsParams(days_before=5),
            agent_prompt="Earnings approaching — review the position.",
            status=TriggerStatus.ACTIVE,
            priority=0,
            cooldown_seconds=21600,
            created_at=when,
            updated_at=when,
            created_by=user_id,
        )
        await trigger_repo.save(earnings_trigger)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Earnings-skip",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.MOCK,
        )

        with caplog.at_level("WARNING"):
            result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        assert rows == [], (
            "Earnings-proximity triggers should be skipped in backtest "
            f"(stub calendar), but {len(rows)} audit rows were written."
        )
        # At least one warning should mention earnings-proximity skip.
        assert any(
            "Earnings-proximity" in record.getMessage() for record in caplog.records
        ), "Expected a WARNING log when an earnings-proximity trigger is skipped."

    async def test_agent_buy_applies_before_strategy_signals(self) -> None:
        """Agent BUY reduces cash before the strategy's signal-generator runs.

        Uses DCA at 1-day frequency so the strategy fires on every
        simulated trading day. Sets the drawdown threshold low (1%) so
        the agent's trigger fires on day 2 onwards as prices drop. On
        any day where both the agent fires (qty=1) AND DCA fires
        (qty resolved from $100 amount), the agent's qty=1 transaction
        should appear ahead of DCA's amount-based transaction in the
        ledger (the builder appends in order).
        """
        from zebu.application.ports.in_memory_agent_invocation_port import (
            StaticAgentInvocationPort,
            make_result,
        )
        from zebu.domain.value_objects.agent_decision import AgentDecision
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )
        from zebu.domain.value_objects.strategy_parameters import DcaParameters

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        transaction_repo = InMemoryTransactionRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 10)
        _seed_dropping_prices(adapter, "AAPL", start, end, start_price=Decimal("100"))

        # DCA at 1-day frequency with a tiny amount so cash is not
        # exhausted; the trigger fires later than day 1, ensuring at
        # least one day has both fires.
        strategy = Strategy(
            id=uuid4(),
            user_id=user_id,
            name="DCA daily",
            strategy_type=StrategyType.DOLLAR_COST_AVERAGING,
            tickers=["AAPL"],
            parameters=DcaParameters(
                frequency_days=1,
                amount_per_period=Decimal("100"),
                allocation={"AAPL": Decimal("1.0")},
            ),
            created_at=datetime.now(UTC),
        )
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        # Drawdown threshold = 1% → fires from day 2 onwards once
        # prices drop 2% below start.
        trigger = _make_drawdown_trigger(
            user_id, activation.id, threshold_pct="1", cooldown_seconds=0
        )
        await trigger_repo.save(trigger)

        buy_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.BUY,
                payload={"ticker": "AAPL", "quantity": "1", "notes": "Agent BUY"},
            )
        )
        factory = InMemoryBacktestAgentInvocationFactory(
            live_port_factory=lambda: buy_port
        )

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            transaction_repo=transaction_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Agent-first",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        # The agent's BUY must be recorded as executed in the audit log
        # (which would not be possible if DCA ran first and consumed all
        # cash — though DCA at $100/period leaves plenty regardless).
        rows = await invocation_repo.list_for_backtest_run(result.id)
        executed_buys = [
            r
            for r in rows
            if r.agent_decision is AgentDecision.BUY and r.decision_executed
        ]
        assert len(executed_buys) >= 1, (
            "Agent BUYs should land successfully when the trigger fires "
            "(DCA leaves cash; agent runs first on each simulated day)."
        )

        # Pull transactions and assert that on at least one simulated day,
        # an agent BUY (qty=1 exactly) comes before a DCA BUY (qty resolved
        # from $100 amount) in the per-day ordering.
        txns = await transaction_repo.get_by_portfolio(result.portfolio_id)
        buys = sorted(
            (t for t in txns if t.transaction_type.value == "BUY"),
            key=lambda t: t.timestamp,
        )
        # Group by date.
        from collections import defaultdict

        by_day: dict[date, list[object]] = defaultdict(list)
        for txn in buys:
            by_day[txn.timestamp.date()].append(txn)
        # Find a day with at least 2 BUYs. If the agent ran first the
        # qty=1 BUY appears before any other.
        days_with_two = [day for day, lst in by_day.items() if len(lst) >= 2]
        assert days_with_two, (
            "Expected at least one day with both agent and DCA BUYs, but "
            f"got days: {sorted(by_day.keys())}"
        )
        for day in days_with_two:
            day_buys = by_day[day]
            first_buy = day_buys[0]
            # Type guard via attribute access.
            qty = getattr(first_buy, "quantity", None)
            assert qty is not None
            assert qty.shares == Decimal("1"), (
                f"On day {day}, the first BUY should be the agent's qty=1 "
                f"BUY; got qty={qty.shares} first (then "
                f"{[getattr(t, 'quantity', None) for t in day_buys[1:]]})."
            )

    async def test_live_buy_with_empty_rationale_is_padded(self) -> None:
        """LIVE port returning empty rationale satisfies entity invariants.

        Defence: the L-1 entity rejects empty rationale on LIVE non-
        INVOCATION_FAILED rows. The production Anthropic adapter never
        returns an empty rationale, but a misbehaving test fake (or a
        transport edge case) could — and the audit row construction
        would crash. The executor pads the empty rationale with a
        decision-stamp so the row is constructible.
        """
        from zebu.application.ports.in_memory_agent_invocation_port import (
            StaticAgentInvocationPort,
            make_result,
        )
        from zebu.domain.value_objects.agent_decision import AgentDecision
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 10)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_dca_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        # rationale="" — would violate the L-1 invariant if it landed
        # on the audit row directly.
        empty_port = StaticAgentInvocationPort(
            result=make_result(
                decision=AgentDecision.BUY,
                rationale="",
                payload={"ticker": "AAPL", "quantity": "1", "notes": ""},
            )
        )
        factory = InMemoryBacktestAgentInvocationFactory(
            live_port_factory=lambda: empty_port
        )

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Empty-rationale",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
        )

        # Should not raise — the executor pads the empty rationale.
        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        assert len(rows) >= 1
        # Padded rationale should be non-empty for every LIVE row.
        for row in rows:
            assert row.rationale != "", (
                "LIVE row's rationale should be padded to non-empty when "
                "the upstream port returned an empty rationale."
            )


# --------------------------------------------------------------------------- #
# Phase L-6 — per-backtest budget guardrails                                  #
# --------------------------------------------------------------------------- #


def _make_live_buy_port_with_tokens(
    *,
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-haiku-4-5-20251001",
):
    """Build a :class:`StaticAgentInvocationPort` whose result reports given tokens."""
    from zebu.application.ports.in_memory_agent_invocation_port import (
        StaticAgentInvocationPort,
        make_result,
    )
    from zebu.domain.value_objects.agent_decision import AgentDecision

    return StaticAgentInvocationPort(
        result=make_result(
            decision=AgentDecision.BUY,
            rationale="Buying the dip.",
            payload={"ticker": "AAPL", "quantity": "1", "notes": "L-6 cost test"},
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    )


class TestBacktestExecutorBudgetGuardrails:
    """Phase L-6 tests for per-backtest agent cost caps."""

    async def test_no_cap_completes_without_marker_row(self) -> None:
        """With ``agent_max_cost_usd=None`` no BUDGET_EXHAUSTED row is ever emitted."""
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 12)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_dca_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        # Result has tokens — would accumulate cost if cap were set.
        port = _make_live_buy_port_with_tokens(
            input_tokens=500_000, output_tokens=100_000
        )
        factory = InMemoryBacktestAgentInvocationFactory(live_port_factory=lambda: port)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="No-cap",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
            agent_max_cost_usd=None,  # explicit
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        # No row should carry the BUDGET_EXHAUSTED marker.
        for row in rows:
            payload = row.decision_payload or {}
            assert payload.get("reason") != "BUDGET_EXHAUSTED"

    async def test_cap_above_total_cost_no_marker_row(self) -> None:
        """Cap larger than actual spend → no downgrade, no marker row."""
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 12)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_dca_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        # Tiny invocation cost — 1k input + 500 output @ Haiku ≈ $0.0028.
        port = _make_live_buy_port_with_tokens(input_tokens=1000, output_tokens=500)
        factory = InMemoryBacktestAgentInvocationFactory(live_port_factory=lambda: port)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Cap-above-cost",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
            agent_max_cost_usd=Decimal("100.00"),  # way above $0.0028/fire
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        # No BUDGET_EXHAUSTED marker; every LIVE row should still be LIVE.
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode as _Mode,
        )

        for row in rows:
            payload = row.decision_payload or {}
            assert payload.get("reason") != "BUDGET_EXHAUSTED"
        # At least one fire happened.
        assert len(rows) >= 1
        # All rows are LIVE — no downgrade.
        assert all(r.invocation_mode is _Mode.LIVE for r in rows)

    async def test_cap_below_first_invocation_triggers_marker_and_downgrade(
        self,
    ) -> None:
        """Cap so small that first fire exhausts → marker + subsequent MOCK rows."""
        from zebu.domain.value_objects.agent_decision import AgentDecision
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        # Need ~10 days w/ short cooldown so multiple fires occur.
        end = date(2024, 1, 15)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_dca_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        # 1-day cooldown so multiple fires possible.
        trigger = _make_drawdown_trigger(
            user_id,
            activation.id,
            threshold_pct="3",
            cooldown_seconds=86400,
        )
        await trigger_repo.save(trigger)

        # Big tokens → meaningful per-fire cost ($0.40 on first fire).
        # Cap at $0.10 so the first fire alone exhausts it.
        port = _make_live_buy_port_with_tokens(input_tokens=500_000, output_tokens=0)
        factory = InMemoryBacktestAgentInvocationFactory(live_port_factory=lambda: port)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Cap-exhausts-first-fire",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
            agent_max_cost_usd=Decimal("0.10"),  # well below $0.40 per fire
        )

        result = await executor.execute(command)

        # Run must complete successfully — budget exhaustion is NOT a failure.
        assert result.status == BacktestStatus.COMPLETED

        rows = await invocation_repo.list_for_backtest_run(result.id)
        assert len(rows) >= 2, "Need at least 1 LIVE fire + 1 marker + 0+ MOCK fires"

        # Exactly one BUDGET_EXHAUSTED marker.
        marker_rows = [
            r
            for r in rows
            if (r.decision_payload or {}).get("reason") == "BUDGET_EXHAUSTED"
        ]
        assert len(marker_rows) == 1, (
            f"Expected exactly 1 BUDGET_EXHAUSTED marker, got {len(marker_rows)}"
        )
        marker = marker_rows[0]
        assert marker.agent_decision is AgentDecision.HOLD
        assert marker.decision_executed is False
        # Marker carries the cap + the cumulative cost at exhaustion.
        marker_payload = marker.decision_payload or {}
        assert marker_payload.get("cap_usd") == 0.10
        cumulative = marker_payload.get("cumulative_cost_usd")
        assert isinstance(cumulative, float)
        assert cumulative >= 0.10  # at or above the cap

    async def test_post_exhaustion_subsequent_fires_are_mock(self) -> None:
        """After the marker is emitted, subsequent rows are MOCK-mode."""
        from zebu.domain.value_objects.agent_decision import AgentDecision
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        # Long window + short cooldown to guarantee multiple fires.
        start = date(2024, 1, 2)
        end = date(2024, 1, 20)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_dca_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(
            user_id, activation.id, threshold_pct="3", cooldown_seconds=86400
        )
        await trigger_repo.save(trigger)

        # First fire crosses cap immediately.
        port = _make_live_buy_port_with_tokens(input_tokens=1_000_000, output_tokens=0)
        factory = InMemoryBacktestAgentInvocationFactory(live_port_factory=lambda: port)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Post-exhaustion-mock",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
            agent_max_cost_usd=Decimal("0.50"),  # exhausted on first $0.80 fire
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = sorted(
            await invocation_repo.list_for_backtest_run(result.id),
            key=lambda r: (r.simulated_date, r.created_at),
        )
        # First row: LIVE BUY (the fire that crossed the threshold).
        # Second row: BUDGET_EXHAUSTED marker (LIVE, decision HOLD).
        # Subsequent rows: MOCK (HOLD, empty model).
        assert rows[0].invocation_mode is BacktestAgentInvocationMode.LIVE
        assert rows[0].agent_decision is AgentDecision.BUY

        marker = rows[1]
        assert (marker.decision_payload or {}).get("reason") == "BUDGET_EXHAUSTED"

        # All subsequent fires (rows[2:]) are MOCK.
        for row in rows[2:]:
            assert row.invocation_mode is BacktestAgentInvocationMode.MOCK, (
                f"Row at {row.simulated_date} should be MOCK after budget "
                f"exhaustion; got {row.invocation_mode}"
            )
            assert row.agent_decision is AgentDecision.HOLD
            assert row.model == ""
            assert row.rationale == ""

    async def test_exhaustion_emits_exactly_one_marker_even_with_many_remaining_fires(
        self,
    ) -> None:
        """Only one marker row per run regardless of how many fires would occur."""
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 30)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_dca_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(
            user_id, activation.id, threshold_pct="3", cooldown_seconds=86400
        )
        await trigger_repo.save(trigger)

        port = _make_live_buy_port_with_tokens(input_tokens=1_000_000, output_tokens=0)
        factory = InMemoryBacktestAgentInvocationFactory(live_port_factory=lambda: port)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Single-marker-only",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
            agent_max_cost_usd=Decimal("0.50"),
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        marker_rows = [
            r
            for r in rows
            if (r.decision_payload or {}).get("reason") == "BUDGET_EXHAUSTED"
        ]
        assert len(marker_rows) == 1

    async def test_mock_mode_with_cap_set_does_not_emit_marker(self) -> None:
        """Cap is ignored in MOCK mode (MOCK incurs zero cost by definition)."""
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 12)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            market_data=adapter,
        )

        # Tiny cap, but MOCK mode is free → no exhaustion.
        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Mock-cap-set",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.MOCK,
            agent_max_cost_usd=Decimal("0.01"),  # would exhaust LIVE instantly
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        marker_rows = [
            r
            for r in rows
            if (r.decision_payload or {}).get("reason") == "BUDGET_EXHAUSTED"
        ]
        assert marker_rows == [], (
            "MOCK mode should never trigger budget exhaustion — MOCK is free."
        )
        # All rows are MOCK-mode.
        assert all(r.invocation_mode is BacktestAgentInvocationMode.MOCK for r in rows)

    async def test_invalid_cap_zero_rejected_at_command_construction(self) -> None:
        """``agent_max_cost_usd=0`` raises :class:`InvalidBacktestCommandError`."""
        from zebu.domain.exceptions import InvalidBacktestCommandError

        with pytest.raises(InvalidBacktestCommandError):
            RunBacktestCommand(
                user_id=uuid4(),
                strategy_id=uuid4(),
                backtest_name="Bad-cap",
                start_date=date(2024, 1, 2),
                end_date=date(2024, 1, 12),
                initial_cash=Decimal("10000"),
                agent_max_cost_usd=Decimal("0"),
            )

    async def test_invalid_cap_negative_rejected_at_command_construction(self) -> None:
        """``agent_max_cost_usd=-1`` raises :class:`InvalidBacktestCommandError`."""
        from zebu.domain.exceptions import InvalidBacktestCommandError

        with pytest.raises(InvalidBacktestCommandError):
            RunBacktestCommand(
                user_id=uuid4(),
                strategy_id=uuid4(),
                backtest_name="Bad-cap-neg",
                start_date=date(2024, 1, 2),
                end_date=date(2024, 1, 12),
                initial_cash=Decimal("10000"),
                agent_max_cost_usd=Decimal("-1.00"),
            )

    async def test_marker_row_carries_model_from_exhausting_fire(self) -> None:
        """The marker row's model matches the model that crossed the cap."""
        from zebu.domain.value_objects.backtest_agent_invocation_mode import (
            BacktestAgentInvocationMode,
        )

        user_id = uuid4()
        strategy_repo = InMemoryStrategyRepository()
        backtest_run_repo = InMemoryBacktestRunRepository()
        activation_repo = InMemoryStrategyActivationRepository()
        trigger_repo = InMemoryTriggerRepository()
        invocation_repo = InMemoryBacktestAgentInvocationRepository()
        adapter = InMemoryMarketDataAdapter()

        start = date(2024, 1, 2)
        end = date(2024, 1, 12)
        _seed_dropping_prices(adapter, "AAPL", start, end)

        strategy = _make_dca_strategy(user_id)
        await strategy_repo.save(strategy)
        portfolio_id = uuid4()
        activation = _make_active_activation(user_id, strategy.id, portfolio_id)
        await activation_repo.save(activation)
        trigger = _make_drawdown_trigger(user_id, activation.id, threshold_pct="3")
        await trigger_repo.save(trigger)

        sonnet_model = "claude-sonnet-4-5-20250929"
        port = _make_live_buy_port_with_tokens(
            input_tokens=1_000_000,
            output_tokens=0,
            model=sonnet_model,
        )
        factory = InMemoryBacktestAgentInvocationFactory(live_port_factory=lambda: port)

        executor = _build_executor(
            strategy_repo=strategy_repo,
            backtest_run_repo=backtest_run_repo,
            activation_repo=activation_repo,
            trigger_repo=trigger_repo,
            backtest_agent_invocation_repo=invocation_repo,
            agent_invocation_factory=factory,
            market_data=adapter,
        )

        command = RunBacktestCommand(
            user_id=user_id,
            strategy_id=strategy.id,
            backtest_name="Marker-model",
            start_date=start,
            end_date=end,
            initial_cash=Decimal("10000"),
            agent_invocation_mode=BacktestAgentInvocationMode.LIVE,
            agent_max_cost_usd=Decimal("1.00"),  # Sonnet 1M input = $3 — exhausted
        )

        result = await executor.execute(command)

        assert result.status == BacktestStatus.COMPLETED
        rows = await invocation_repo.list_for_backtest_run(result.id)
        marker_rows = [
            r
            for r in rows
            if (r.decision_payload or {}).get("reason") == "BUDGET_EXHAUSTED"
        ]
        assert len(marker_rows) == 1
        # The marker's model should be the model that crossed the threshold.
        assert marker_rows[0].model == sonnet_model
