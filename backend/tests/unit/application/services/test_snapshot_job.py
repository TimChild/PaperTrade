"""Tests for SnapshotJobService."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from zebu.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from zebu.application.services.snapshot_job import SnapshotJobService
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


class InMemorySnapshotRepository:
    """Simple in-memory snapshot repository for testing."""

    def __init__(self) -> None:
        """Initialize empty snapshot storage."""
        self._snapshots: list = []

    async def save(self, snapshot) -> None:  # type: ignore[no-untyped-def]
        """Save a snapshot."""
        # Upsert behavior: replace if exists for same portfolio+date
        existing_idx = None
        for idx, s in enumerate(self._snapshots):
            if (
                s.portfolio_id == snapshot.portfolio_id
                and s.snapshot_date == snapshot.snapshot_date
            ):
                existing_idx = idx
                break

        if existing_idx is not None:
            self._snapshots[existing_idx] = snapshot
        else:
            self._snapshots.append(snapshot)

    async def get_by_portfolio_and_date(self, portfolio_id, snapshot_date):  # type: ignore[no-untyped-def]
        """Get snapshot by portfolio and date."""
        for s in self._snapshots:
            if s.portfolio_id == portfolio_id and s.snapshot_date == snapshot_date:
                return s
        return None

    async def get_range(self, portfolio_id, start_date, end_date):  # type: ignore[no-untyped-def]
        """Get snapshots in date range."""
        result = [
            s
            for s in self._snapshots
            if s.portfolio_id == portfolio_id
            and start_date <= s.snapshot_date <= end_date
        ]
        return sorted(result, key=lambda s: s.snapshot_date)

    async def get_latest(self, portfolio_id):  # type: ignore[no-untyped-def]
        """Get latest snapshot for portfolio."""
        portfolio_snapshots = [
            s for s in self._snapshots if s.portfolio_id == portfolio_id
        ]
        if not portfolio_snapshots:
            return None
        return max(portfolio_snapshots, key=lambda s: s.snapshot_date)

    async def delete_by_portfolio(self, portfolio_id):  # type: ignore[no-untyped-def]
        """Delete all snapshots for a portfolio."""
        count = sum(1 for s in self._snapshots if s.portfolio_id == portfolio_id)
        self._snapshots = [s for s in self._snapshots if s.portfolio_id != portfolio_id]
        return count


class TestRunDailySnapshot:
    """Tests for run_daily_snapshot method."""

    @pytest.mark.asyncio
    async def test_run_daily_snapshot_all_portfolios(self) -> None:
        """Test that daily snapshot processes all portfolios."""
        # Arrange
        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        snapshot_repo = InMemorySnapshotRepository()
        market_data = InMemoryMarketDataAdapter()

        # Create 3 portfolios
        user_id = uuid4()
        portfolio1 = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Portfolio 1",
            created_at=datetime.now(UTC),
        )
        portfolio2 = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Portfolio 2",
            created_at=datetime.now(UTC),
        )
        portfolio3 = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Portfolio 3",
            created_at=datetime.now(UTC),
        )

        await portfolio_repo.save(portfolio1)
        await portfolio_repo.save(portfolio2)
        await portfolio_repo.save(portfolio3)

        service = SnapshotJobService(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            snapshot_repo=snapshot_repo,
            market_data=market_data,
        )

        # Act
        results = await service.run_daily_snapshot()

        # Assert
        assert results["processed"] == 3
        assert results["succeeded"] == 3
        assert results["failed"] == 0
        assert len(snapshot_repo._snapshots) == 3

    @pytest.mark.asyncio
    async def test_run_daily_snapshot_empty_portfolios(self) -> None:
        """Test daily snapshot with no portfolios."""
        # Arrange
        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        snapshot_repo = InMemorySnapshotRepository()
        market_data = InMemoryMarketDataAdapter()

        service = SnapshotJobService(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            snapshot_repo=snapshot_repo,
            market_data=market_data,
        )

        # Act
        results = await service.run_daily_snapshot()

        # Assert
        assert results["processed"] == 0
        assert results["succeeded"] == 0
        assert results["failed"] == 0

    @pytest.mark.asyncio
    async def test_run_daily_snapshot_with_specific_date(self) -> None:
        """Test daily snapshot for a specific date."""
        # Arrange
        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        snapshot_repo = InMemorySnapshotRepository()
        market_data = InMemoryMarketDataAdapter()

        user_id = uuid4()
        portfolio = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Test Portfolio",
            created_at=datetime.now(UTC),
        )
        await portfolio_repo.save(portfolio)

        service = SnapshotJobService(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            snapshot_repo=snapshot_repo,
            market_data=market_data,
        )

        target_date = date(2024, 1, 15)

        # Act
        results = await service.run_daily_snapshot(snapshot_date=target_date)

        # Assert
        assert results["succeeded"] == 1
        snapshot = snapshot_repo._snapshots[0]
        assert snapshot.snapshot_date == target_date


class TestBackfillSnapshots:
    """Tests for backfill_snapshots method."""

    @pytest.mark.asyncio
    async def test_backfill_snapshots_date_range(self) -> None:
        """Test backfilling snapshots for a date range."""
        # Arrange
        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        snapshot_repo = InMemorySnapshotRepository()
        market_data = InMemoryMarketDataAdapter()

        user_id = uuid4()
        portfolio = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Test Portfolio",
            created_at=datetime.now(UTC),
        )
        await portfolio_repo.save(portfolio)

        service = SnapshotJobService(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            snapshot_repo=snapshot_repo,
            market_data=market_data,
        )

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)

        # Act
        results = await service.backfill_snapshots(
            portfolio_id=portfolio.id,
            start_date=start_date,
            end_date=end_date,
        )

        # Assert
        assert results["processed"] == 5  # 5 days
        assert results["succeeded"] == 5
        assert results["failed"] == 0
        assert len(snapshot_repo._snapshots) == 5

        # Verify all dates are present
        snapshot_dates = [s.snapshot_date for s in snapshot_repo._snapshots]
        expected_dates = [
            date(2024, 1, 1),
            date(2024, 1, 2),
            date(2024, 1, 3),
            date(2024, 1, 4),
            date(2024, 1, 5),
        ]
        assert sorted(snapshot_dates) == expected_dates

    @pytest.mark.asyncio
    async def test_backfill_snapshots_single_day(self) -> None:
        """Test backfilling snapshots for a single day."""
        # Arrange
        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        snapshot_repo = InMemorySnapshotRepository()
        market_data = InMemoryMarketDataAdapter()

        user_id = uuid4()
        portfolio = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Test Portfolio",
            created_at=datetime.now(UTC),
        )
        await portfolio_repo.save(portfolio)

        service = SnapshotJobService(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            snapshot_repo=snapshot_repo,
            market_data=market_data,
        )

        target_date = date(2024, 1, 15)

        # Act
        results = await service.backfill_snapshots(
            portfolio_id=portfolio.id,
            start_date=target_date,
            end_date=target_date,
        )

        # Assert
        assert results["processed"] == 1
        assert results["succeeded"] == 1
        assert results["failed"] == 0
        assert len(snapshot_repo._snapshots) == 1
        assert snapshot_repo._snapshots[0].snapshot_date == target_date

    @pytest.mark.asyncio
    async def test_backfill_snapshots_portfolio_not_found(self) -> None:
        """Test backfilling snapshots for non-existent portfolio."""
        # Arrange
        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        snapshot_repo = InMemorySnapshotRepository()
        market_data = InMemoryMarketDataAdapter()

        service = SnapshotJobService(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            snapshot_repo=snapshot_repo,
            market_data=market_data,
        )

        non_existent_id = uuid4()
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 5)

        # Act
        results = await service.backfill_snapshots(
            portfolio_id=non_existent_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Assert - all should fail
        assert results["processed"] == 5
        assert results["succeeded"] == 0
        assert results["failed"] == 5


class TestCalculateSnapshotForPortfolio:
    """Tests for _calculate_snapshot_for_portfolio method."""

    @pytest.mark.asyncio
    async def test_calculate_snapshot_cash_only(self) -> None:
        """Test calculating snapshot for portfolio with only cash."""
        # Arrange
        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        snapshot_repo = InMemorySnapshotRepository()
        market_data = InMemoryMarketDataAdapter()

        user_id = uuid4()
        portfolio = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Test Portfolio",
            created_at=datetime.now(UTC),
        )
        await portfolio_repo.save(portfolio)

        # Add deposit transaction (cash only)
        deposit = Transaction(
            id=uuid4(),
            portfolio_id=portfolio.id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("10000.00"), "USD"),
        )
        await transaction_repo.save(deposit)

        service = SnapshotJobService(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            snapshot_repo=snapshot_repo,
            market_data=market_data,
        )

        # Act
        snapshot = await service._calculate_snapshot_for_portfolio(
            portfolio_id=portfolio.id,
            snapshot_date=date.today(),
        )

        # Assert
        assert snapshot.portfolio_id == portfolio.id
        assert snapshot.cash_balance == Decimal("10000.00")
        assert snapshot.holdings_value == Decimal("0.00")
        assert snapshot.total_value == Decimal("10000.00")
        assert snapshot.holdings_count == 0

    @pytest.mark.asyncio
    async def test_calculate_snapshot_with_holdings(self) -> None:
        """Test calculating snapshot for portfolio with stock holdings."""
        # Arrange
        portfolio_repo = InMemoryPortfolioRepository()
        transaction_repo = InMemoryTransactionRepository()
        snapshot_repo = InMemorySnapshotRepository()
        market_data = InMemoryMarketDataAdapter()

        user_id = uuid4()
        portfolio = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Test Portfolio",
            created_at=datetime.now(UTC),
        )
        await portfolio_repo.save(portfolio)

        # Add deposit
        deposit = Transaction(
            id=uuid4(),
            portfolio_id=portfolio.id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("10000.00"), "USD"),
        )
        await transaction_repo.save(deposit)

        # Add buy transaction
        ticker = Ticker("AAPL")
        buy = Transaction(
            id=uuid4(),
            portfolio_id=portfolio.id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("-1500.00"), "USD"),  # 10 * 150
            ticker=ticker,
            quantity=Quantity(Decimal("10")),
            price_per_share=Money(Decimal("150.00"), "USD"),
        )
        await transaction_repo.save(buy)

        # Seed current price for AAPL
        from zebu.application.dtos.price_point import PricePoint
        from zebu.domain.value_objects.money import Money as MoneyVO

        market_data.seed_price(
            PricePoint(
                ticker=ticker,
                price=MoneyVO(Decimal("150.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="database",
                interval="1day",
            )
        )

        service = SnapshotJobService(
            portfolio_repo=portfolio_repo,
            transaction_repo=transaction_repo,
            snapshot_repo=snapshot_repo,
            market_data=market_data,
        )

        # Act
        snapshot = await service._calculate_snapshot_for_portfolio(
            portfolio_id=portfolio.id,
            snapshot_date=date.today(),
        )

        # Assert
        # Cash: 10000 - 1500 = 8500
        # Holdings: 10 * 150 = 1500
        # Total: 8500 + 1500 = 10000
        assert snapshot.portfolio_id == portfolio.id
        assert snapshot.cash_balance == Decimal("8500.00")
        assert snapshot.holdings_value == Decimal("1500.00")
        assert snapshot.total_value == Decimal("10000.00")
        assert snapshot.holdings_count == 1
