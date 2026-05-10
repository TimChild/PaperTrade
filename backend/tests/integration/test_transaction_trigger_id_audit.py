"""Integration tests for the ``trigger_id`` audit column on ``transactions``.

Phase F-5 — verifies:

* ``TransactionRepository.save(..., trigger_id=...)`` stamps the column.
* ``TransactionRepository.save_all(..., trigger_id=...)`` stamps the
  column uniformly on every row in the batch.
* The default (``trigger_id=None``) leaves the column null — the existing
  call sites that don't pass ``trigger_id`` keep working unchanged.
* The FK is enforced (``ON DELETE SET NULL``) — deleting the trigger
  detaches the reference but does not erase the transaction row.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlmodel.ext.asyncio.session import AsyncSession

from zebu.adapters.outbound.database.api_key_model import ApiKeyModel
from zebu.adapters.outbound.database.models import (
    PortfolioModel,
    StrategyActivationModel,
    StrategyConditionTriggerModel,
    StrategyModel,
    TransactionModel,
)
from zebu.adapters.outbound.database.transaction_repository import (
    SQLModelTransactionRepository,
)
from zebu.domain.entities.api_key import ApiKey
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.api_key_scope import ApiKeyScope
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.strategy_parameters import BuyAndHoldParameters
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    DrawdownMetric,
    DrawdownParams,
)
from zebu.domain.value_objects.trigger_status import TriggerStatus


@pytest_asyncio.fixture
async def seeded_trigger(session: AsyncSession) -> StrategyConditionTrigger:
    """Insert the FK chain (portfolio → strategy → activation → trigger).

    Returns the trigger entity so tests can stamp transactions with its
    ID and assert the FK + ``ON DELETE SET NULL`` behaviour.
    """
    user_id = uuid4()

    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="Audit Column Test Portfolio",
        created_at=datetime.now(UTC) - timedelta(days=1),
        portfolio_type=PortfolioType.PAPER_TRADING,
    )
    session.add(PortfolioModel.from_domain(portfolio))
    await session.flush()

    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="Audit Column Test Strategy",
        strategy_type=StrategyType.BUY_AND_HOLD,
        tickers=["AAPL"],
        parameters=BuyAndHoldParameters(allocation={"AAPL": Decimal("1.0")}),
        created_at=datetime.now(UTC) - timedelta(days=1),
    )
    session.add(StrategyModel.from_domain(strategy))
    await session.flush()

    activation = StrategyActivation(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy.id,
        portfolio_id=portfolio.id,
        status=ActivationStatus.ACTIVE,
        frequency=ActivationFrequency.DAILY_MARKET_CLOSE,
        created_at=datetime.now(UTC) - timedelta(hours=2),
        updated_at=datetime.now(UTC) - timedelta(hours=2),
    )
    session.add(StrategyActivationModel.from_domain(activation))
    await session.flush()

    api_key = ApiKey(
        id=uuid4(),
        user_id=user_id,
        clerk_user_id="clerk_user_audit_test",
        label="audit-test-key",
        key_hash="hash_" + "0" * 60,
        scopes=frozenset({ApiKeyScope.TRADE}),
        created_at=datetime.now(UTC) - timedelta(hours=3),
    )
    session.add(ApiKeyModel.from_domain(api_key))
    await session.flush()

    trigger = StrategyConditionTrigger(
        id=uuid4(),
        activation_id=activation.id,
        user_id=user_id,
        condition_type=ConditionType.DRAWDOWN_THRESHOLD,
        condition_params=DrawdownParams(
            threshold_pct=Decimal("5"),
            lookback_days=30,
            metric=DrawdownMetric.PORTFOLIO_TOTAL,
        ),
        agent_prompt=(
            "Decide whether to hold the position based on context. "
            "Use the read tools to gather news data."
        ),
        status=TriggerStatus.ACTIVE,
        created_at=datetime.now(UTC) - timedelta(hours=1),
        updated_at=datetime.now(UTC) - timedelta(hours=1),
        created_by=user_id,
    )
    session.add(StrategyConditionTriggerModel.from_domain(trigger))
    await session.flush()

    return trigger


def _make_buy_transaction(
    *,
    portfolio_id: UUID,
    timestamp: datetime,
    notes: str = "Trigger fire — agent BUY",
) -> Transaction:
    """Build a BUY transaction (post-deposit) for tests."""
    return Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.BUY,
        timestamp=timestamp,
        cash_change=Money(Decimal("-150.00"), "USD"),
        ticker=Ticker("AAPL"),
        quantity=Quantity(Decimal("1")),
        price_per_share=Money(Decimal("150.00"), "USD"),
        notes=notes,
    )


@pytest.mark.asyncio
async def test_save_with_trigger_id_stamps_column(
    session: AsyncSession,
    seeded_trigger: StrategyConditionTrigger,
) -> None:
    """``save(..., trigger_id=...)`` writes the value to the column."""
    repo = SQLModelTransactionRepository(session)

    # First seed a deposit so the BUY has cash to use; deposit row carries
    # no trigger_id (it's user-initiated).
    deposit = Transaction(
        id=uuid4(),
        portfolio_id=seeded_trigger.activation_id,  # placeholder — overwritten
        transaction_type=TransactionType.DEPOSIT,
        timestamp=datetime.now(UTC) - timedelta(seconds=30),
        cash_change=Money(Decimal("10000"), "USD"),
        notes="seed",
    )
    # Resolve the activation -> portfolio mapping by re-reading the model.
    activation_model = await session.get(
        StrategyActivationModel, seeded_trigger.activation_id
    )
    assert activation_model is not None
    portfolio_id = activation_model.portfolio_id

    deposit = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.DEPOSIT,
        timestamp=datetime.now(UTC) - timedelta(seconds=30),
        cash_change=Money(Decimal("10000"), "USD"),
        notes="seed",
    )
    await repo.save(deposit)

    # Now the BUY tagged with the trigger id.
    buy = _make_buy_transaction(
        portfolio_id=portfolio_id,
        timestamp=datetime.now(UTC) - timedelta(seconds=10),
    )
    await repo.save(buy, trigger_id=seeded_trigger.id)

    # Round-trip via direct ORM read to confirm the column is set.
    persisted = await session.get(TransactionModel, buy.id)
    assert persisted is not None
    assert persisted.trigger_id == seeded_trigger.id


@pytest.mark.asyncio
async def test_save_without_trigger_id_leaves_column_null(
    session: AsyncSession,
    seeded_trigger: StrategyConditionTrigger,
) -> None:
    """The default ``trigger_id=None`` path keeps the column null."""
    repo = SQLModelTransactionRepository(session)
    activation_model = await session.get(
        StrategyActivationModel, seeded_trigger.activation_id
    )
    assert activation_model is not None
    portfolio_id = activation_model.portfolio_id

    buy = _make_buy_transaction(
        portfolio_id=portfolio_id,
        timestamp=datetime.now(UTC) - timedelta(seconds=10),
    )
    await repo.save(buy)

    persisted = await session.get(TransactionModel, buy.id)
    assert persisted is not None
    assert persisted.trigger_id is None


@pytest.mark.asyncio
async def test_save_all_with_trigger_id_stamps_every_row(
    session: AsyncSession,
    seeded_trigger: StrategyConditionTrigger,
) -> None:
    """``save_all(..., trigger_id=...)`` stamps every row in the batch."""
    repo = SQLModelTransactionRepository(session)
    activation_model = await session.get(
        StrategyActivationModel, seeded_trigger.activation_id
    )
    assert activation_model is not None
    portfolio_id = activation_model.portfolio_id

    transactions = [
        _make_buy_transaction(
            portfolio_id=portfolio_id,
            timestamp=datetime.now(UTC) - timedelta(seconds=20 - i),
            notes=f"batch BUY #{i}",
        )
        for i in range(3)
    ]
    # Seed cash first so the inserts don't violate any post-write checks.
    deposit = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.DEPOSIT,
        timestamp=datetime.now(UTC) - timedelta(seconds=60),
        cash_change=Money(Decimal("10000"), "USD"),
        notes="seed",
    )
    await repo.save(deposit)

    await repo.save_all(transactions, trigger_id=seeded_trigger.id)

    for txn in transactions:
        persisted = await session.get(TransactionModel, txn.id)
        assert persisted is not None
        assert persisted.trigger_id == seeded_trigger.id


@pytest.mark.asyncio
async def test_trigger_delete_sets_transaction_trigger_id_null(
    session: AsyncSession,
    seeded_trigger: StrategyConditionTrigger,
) -> None:
    """``ON DELETE SET NULL`` — deleting the trigger detaches the FK only."""
    repo = SQLModelTransactionRepository(session)
    activation_model = await session.get(
        StrategyActivationModel, seeded_trigger.activation_id
    )
    assert activation_model is not None
    portfolio_id = activation_model.portfolio_id

    deposit = Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.DEPOSIT,
        timestamp=datetime.now(UTC) - timedelta(seconds=60),
        cash_change=Money(Decimal("10000"), "USD"),
        notes="seed",
    )
    await repo.save(deposit)

    buy = _make_buy_transaction(
        portfolio_id=portfolio_id,
        timestamp=datetime.now(UTC) - timedelta(seconds=10),
    )
    await repo.save(buy, trigger_id=seeded_trigger.id)

    # Delete the trigger row directly (the API DELETE endpoint soft-deletes
    # by transitioning the entity to EXPIRED — that's a different code path
    # and doesn't exercise the FK-cascade behaviour). Hard-deleting the
    # row is the only way to verify ``ON DELETE SET NULL`` actually fires.
    trigger_model = await session.get(StrategyConditionTriggerModel, seeded_trigger.id)
    assert trigger_model is not None
    await session.delete(trigger_model)
    await session.flush()

    # Re-read the transaction; the trigger_id should now be NULL.
    persisted = await session.get(TransactionModel, buy.id)
    assert persisted is not None
    assert persisted.trigger_id is None
