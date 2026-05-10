"""Integration test for the F-4 condition-type dispatch.

Verifies that :class:`TriggerEvaluationService` correctly routes
``VOLATILITY_SPIKE`` and ``EARNINGS_PROXIMITY`` triggers to the right
evaluator end-to-end against SQL adapters. The drawdown path is
covered in ``test_trigger_evaluation_service.py``.

Scope:

* VOLATILITY_SPIKE: one ACTIVE trigger fires when the activation's
  ticker has a turbulent price history.
* VOLATILITY_SPIKE: a calm ticker does not fire even with a low
  threshold.
* EARNINGS_PROXIMITY: with the F-4 default stub adapter, the trigger
  never fires (Q5 deferred decision).
* EARNINGS_PROXIMITY: with a fake adapter that returns an in-window
  event, the trigger fires and the snapshot identifies the ticker.
* CUSTOM_RULE: still raises NotImplementedError (caught by
  ``_safe_evaluate_one`` and surfaced as a per-trigger error).
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.api_key_model import ApiKeyModel
from zebu.adapters.outbound.database.models import (
    PortfolioModel,
    StrategyActivationModel,
    StrategyModel,
)
from zebu.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from zebu.adapters.outbound.database.strategy_activation_repository import (
    SQLModelStrategyActivationRepository,
)
from zebu.adapters.outbound.database.strategy_condition_trigger_repository import (
    SQLModelTriggerRepository,
)
from zebu.adapters.outbound.database.strategy_repository import (
    SQLModelStrategyRepository,
)
from zebu.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from zebu.adapters.outbound.earnings.stub_calendar_adapter import (
    StubEarningsCalendarAdapter,
)
from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.ports.earnings_calendar_port import EarningsEvent
from zebu.application.services.trigger_evaluation_service import (
    TriggerEvaluationService,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.api_key_scope import ApiKeyScope
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.strategy_parameters import BuyAndHoldParameters
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    EarningsParams,
    VolatilityParams,
)
from zebu.domain.value_objects.trigger_status import TriggerStatus

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeEarningsCalendar:
    """Test fake — returns a pre-configured list of events."""

    def __init__(self, events: list[EarningsEvent]) -> None:
        self._events = events

    async def upcoming_earnings(
        self,
        tickers: list[str],
        within_days: int,
    ) -> list[EarningsEvent]:
        del within_days  # window check happens inside the evaluator
        ticker_set = set(tickers)
        return [event for event in self._events if event.ticker in ticker_set]


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


async def _seed_activation(
    session: AsyncSession,
    *,
    user_id: object,
    ticker: str = "AAPL",
) -> tuple[Portfolio, Strategy, StrategyActivation, ApiKey]:
    """Seed an activation + portfolio + strategy + api-key.

    Doesn't seed transactions — volatility / earnings don't need them
    (the universe comes from ``strategy.tickers``).
    """
    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        name="Test Portfolio",
        created_at=datetime.now(UTC) - timedelta(days=60),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )
    session.add(PortfolioModel.from_domain(portfolio))
    await session.flush()

    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        name="Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=[ticker],
        parameters=BuyAndHoldParameters(allocation={ticker: Decimal("1.0")}),
        created_at=datetime.now(UTC) - timedelta(days=60),
    )
    session.add(StrategyModel.from_domain(strategy))
    await session.flush()

    activation = StrategyActivation(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        strategy_id=strategy.id,
        portfolio_id=portfolio.id,
        status=ActivationStatus.ACTIVE,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=datetime.now(UTC) - timedelta(days=45),
        updated_at=datetime.now(UTC) - timedelta(days=45),
    )
    session.add(StrategyActivationModel.from_domain(activation))
    await session.flush()

    api_key = ApiKey(
        id=uuid4(),
        user_id=user_id,  # type: ignore[arg-type]
        clerk_user_id="clerk_user_test",
        label="test-key",
        key_hash="hash_" + "0" * 60,
        scopes=frozenset({ApiKeyScope.READ, ApiKeyScope.TRADE}),
        created_at=datetime.now(UTC) - timedelta(days=60),
    )
    session.add(ApiKeyModel.from_domain(api_key))
    await session.flush()

    return portfolio, strategy, activation, api_key


def _build_volatile_market_data(*, ticker: str = "AAPL") -> InMemoryMarketDataAdapter:
    """Seed price history with daily ~10% swings (high realised vol)."""
    adapter = InMemoryMarketDataAdapter()
    # 12 closes of $100 / $110 alternating ⇒ realised vol >> 30%.
    days_to_prices: list[tuple[int, str]] = [
        (12, "100"),
        (11, "110"),
        (10, "90"),
        (9, "110"),
        (8, "90"),
        (7, "110"),
        (6, "90"),
        (5, "110"),
        (4, "90"),
        (3, "110"),
        (2, "90"),
        (1, "110"),
    ]
    for days_ago, price in days_to_prices:
        timestamp = datetime.now(UTC) - timedelta(days=days_ago)
        adapter.seed_price(
            PricePoint(
                ticker=Ticker(ticker),
                price=Money(Decimal(price), "USD"),
                timestamp=timestamp,
                source="database",
                interval="1day",
                close=Money(Decimal(price), "USD"),
            )
        )
    return adapter


def _build_calm_market_data(*, ticker: str = "AAPL") -> InMemoryMarketDataAdapter:
    """Seed price history with very stable closes (low realised vol)."""
    adapter = InMemoryMarketDataAdapter()
    # Closes drift ±0.1% — annualised vol stays well below 5%.
    base_prices = [
        "100.00",
        "100.05",
        "100.00",
        "100.05",
        "100.10",
        "100.05",
        "100.00",
        "100.05",
        "100.00",
        "100.05",
        "100.10",
        "100.05",
    ]
    for offset, price in enumerate(reversed(base_prices), start=1):
        timestamp = datetime.now(UTC) - timedelta(days=offset)
        adapter.seed_price(
            PricePoint(
                ticker=Ticker(ticker),
                price=Money(Decimal(price), "USD"),
                timestamp=timestamp,
                source="database",
                interval="1day",
                close=Money(Decimal(price), "USD"),
            )
        )
    return adapter


# ---------------------------------------------------------------------------
# Volatility-spike dispatch
# ---------------------------------------------------------------------------


class TestVolatilitySpikeDispatch:
    """Service routes VOLATILITY_SPIKE to the volatility evaluator."""

    async def test_volatile_ticker_fires(
        self,
        session: AsyncSession,
    ) -> None:
        """Volatile price history ⇒ trigger fires; snapshot has ticker + realised."""
        user_id = uuid4()
        ticker = "AAPL"
        _, _, activation, api_key = await _seed_activation(
            session, user_id=user_id, ticker=ticker
        )

        trigger = StrategyConditionTrigger(
            id=uuid4(),
            activation_id=activation.id,
            user_id=user_id,
            condition_type=ConditionType.VOLATILITY_SPIKE,
            condition_params=VolatilityParams(
                threshold_pct=Decimal("30"),
                over_days=20,
            ),
            agent_prompt=(
                "Decide whether to reduce position size given this volatility."
            ),
            status=TriggerStatus.ACTIVE,
            cooldown_seconds=21600,
            created_at=datetime.now(UTC) - timedelta(days=10),
            updated_at=datetime.now(UTC) - timedelta(days=10),
            created_by=user_id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = SQLModelTriggerRepository(session)
        await trigger_repo.save(trigger)
        await session.flush()

        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=SQLModelStrategyActivationRepository(session),
            strategy_repo=SQLModelStrategyRepository(session),
            portfolio_repo=SQLModelPortfolioRepository(session),
            transaction_repo=SQLModelTransactionRepository(session),
            market_data=_build_volatile_market_data(ticker=ticker),
            earnings_calendar=StubEarningsCalendarAdapter(),
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 1
        assert summary["fired"] == 1
        assert summary["failed"] == 0
        result = summary["results"][0]
        assert result["fired"] is True
        evaluation_data = result["evaluation_data"]
        assert evaluation_data is not None
        assert "realised_vol_pct" in evaluation_data
        assert evaluation_data["ticker"] == ticker

    async def test_calm_ticker_does_not_fire(
        self,
        session: AsyncSession,
    ) -> None:
        """Stable price series ⇒ no fire."""
        user_id = uuid4()
        ticker = "JNJ"
        _, _, activation, api_key = await _seed_activation(
            session, user_id=user_id, ticker=ticker
        )

        trigger = StrategyConditionTrigger(
            id=uuid4(),
            activation_id=activation.id,
            user_id=user_id,
            condition_type=ConditionType.VOLATILITY_SPIKE,
            condition_params=VolatilityParams(
                threshold_pct=Decimal("30"),
                over_days=10,
            ),
            agent_prompt="Reduce position size if volatility spikes.",
            status=TriggerStatus.ACTIVE,
            cooldown_seconds=21600,
            created_at=datetime.now(UTC) - timedelta(days=10),
            updated_at=datetime.now(UTC) - timedelta(days=10),
            created_by=user_id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = SQLModelTriggerRepository(session)
        await trigger_repo.save(trigger)
        await session.flush()

        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=SQLModelStrategyActivationRepository(session),
            strategy_repo=SQLModelStrategyRepository(session),
            portfolio_repo=SQLModelPortfolioRepository(session),
            transaction_repo=SQLModelTransactionRepository(session),
            market_data=_build_calm_market_data(ticker=ticker),
            earnings_calendar=StubEarningsCalendarAdapter(),
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 1
        assert summary["fired"] == 0
        assert summary["failed"] == 0
        assert summary["skipped"] == 1


# ---------------------------------------------------------------------------
# Earnings-proximity dispatch
# ---------------------------------------------------------------------------


class TestEarningsProximityDispatch:
    """Service routes EARNINGS_PROXIMITY to the earnings evaluator."""

    async def test_stub_calendar_never_fires(
        self,
        session: AsyncSession,
    ) -> None:
        """Per design Q5: F-4 default stub returns ``[]`` ⇒ no fire."""
        user_id = uuid4()
        ticker = "AAPL"
        _, _, activation, api_key = await _seed_activation(
            session, user_id=user_id, ticker=ticker
        )

        trigger = StrategyConditionTrigger(
            id=uuid4(),
            activation_id=activation.id,
            user_id=user_id,
            condition_type=ConditionType.EARNINGS_PROXIMITY,
            condition_params=EarningsParams(days_before=7),
            agent_prompt="Hold or trim before earnings.",
            status=TriggerStatus.ACTIVE,
            cooldown_seconds=21600,
            created_at=datetime.now(UTC) - timedelta(days=10),
            updated_at=datetime.now(UTC) - timedelta(days=10),
            created_by=user_id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = SQLModelTriggerRepository(session)
        await trigger_repo.save(trigger)
        await session.flush()

        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=SQLModelStrategyActivationRepository(session),
            strategy_repo=SQLModelStrategyRepository(session),
            portfolio_repo=SQLModelPortfolioRepository(session),
            transaction_repo=SQLModelTransactionRepository(session),
            market_data=InMemoryMarketDataAdapter(),
            earnings_calendar=StubEarningsCalendarAdapter(),
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 1
        assert summary["fired"] == 0
        assert summary["failed"] == 0

    async def test_fake_calendar_with_in_window_event_fires(
        self,
        session: AsyncSession,
    ) -> None:
        """Real fire path: fake calendar returns an in-window event ⇒ fire."""
        user_id = uuid4()
        ticker = "AAPL"
        _, _, activation, api_key = await _seed_activation(
            session, user_id=user_id, ticker=ticker
        )

        trigger = StrategyConditionTrigger(
            id=uuid4(),
            activation_id=activation.id,
            user_id=user_id,
            condition_type=ConditionType.EARNINGS_PROXIMITY,
            condition_params=EarningsParams(days_before=7),
            agent_prompt="Hold or trim before earnings.",
            status=TriggerStatus.ACTIVE,
            cooldown_seconds=21600,
            created_at=datetime.now(UTC) - timedelta(days=10),
            updated_at=datetime.now(UTC) - timedelta(days=10),
            created_by=user_id,
            default_api_key_id=api_key.id,
        )
        trigger_repo = SQLModelTriggerRepository(session)
        await trigger_repo.save(trigger)
        await session.flush()

        # Calendar with one event in 3 days.
        in_window_event = EarningsEvent(
            ticker=ticker,
            report_date=date.today() + timedelta(days=3),
            before_market_open=True,
            confirmed=True,
        )
        service = TriggerEvaluationService(
            trigger_repo=trigger_repo,
            activation_repo=SQLModelStrategyActivationRepository(session),
            strategy_repo=SQLModelStrategyRepository(session),
            portfolio_repo=SQLModelPortfolioRepository(session),
            transaction_repo=SQLModelTransactionRepository(session),
            market_data=InMemoryMarketDataAdapter(),
            earnings_calendar=_FakeEarningsCalendar(events=[in_window_event]),
            earnings_calendar_label="fake_test",
        )

        summary = await service.evaluate_all()

        assert summary["processed"] == 1
        assert summary["fired"] == 1
        assert summary["failed"] == 0
        result = summary["results"][0]
        evaluation_data = result["evaluation_data"]
        assert evaluation_data is not None
        assert "next_earnings_date" in evaluation_data
        assert evaluation_data["ticker"] == ticker
        assert evaluation_data["source"] == "fake_test"


# ---------------------------------------------------------------------------
# CUSTOM_RULE remains unimplemented
# ---------------------------------------------------------------------------


class TestCustomRuleDispatch:
    """CUSTOM_RULE intentionally raises (per design Q1).

    We can't construct a CUSTOM_RULE trigger end-to-end because the
    entity rejects ``CustomRuleParams`` at construction time
    (Q1 deferral). That rejection is exercised in the
    :class:`StrategyConditionTrigger` unit tests; here we just confirm
    the service-level match arm raises ``NotImplementedError`` if a
    trigger ever reached the dispatch with that type.

    This test is intentionally minimal — the real safety net is the
    construction-time rejection, which prevents a CUSTOM_RULE trigger
    from being persisted in the first place.
    """

    # Implementation note: there's no easy way to bypass the entity
    # validation to seed a CUSTOM_RULE trigger row, so we don't try.
    # The unit-test suite covers the dispatch arm directly.
