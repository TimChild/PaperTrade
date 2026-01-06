"""Integration tests for SQLModelSnapshotRepository.

Tests the snapshot repository with a real SQLite database to verify
all CRUD operations work correctly.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from papertrade.adapters.outbound.database.snapshot_repository import (
    SQLModelSnapshotRepository,
)
from papertrade.domain.entities.portfolio_snapshot import PortfolioSnapshot


class TestSQLModelSnapshotRepository:
    """Integration tests for SQLModel snapshot repository."""

    @pytest.mark.asyncio
    async def test_save_new_snapshot(self, session):
        """Test saving a new snapshot."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        snapshot = PortfolioSnapshot.create(
            portfolio_id=uuid4(),
            snapshot_date=date(2024, 1, 15),
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("5000.00"),
            holdings_count=3,
        )

        # Act
        result = await repo.save(snapshot)
        await session.commit()

        # Assert
        assert result is not None
        assert result.id == snapshot.id
        assert result.portfolio_id == snapshot.portfolio_id
        assert result.snapshot_date == snapshot.snapshot_date
        assert result.total_value == Decimal("15000.00")
        assert result.cash_balance == Decimal("10000.00")
        assert result.holdings_value == Decimal("5000.00")
        assert result.holdings_count == 3

    @pytest.mark.asyncio
    async def test_save_updates_existing_snapshot(self, session):
        """Test that saving a snapshot with same portfolio_id and date updates it."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id = uuid4()
        snapshot_date = date(2024, 1, 15)

        # Create initial snapshot
        snapshot1 = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("5000.00"),
            holdings_count=3,
        )
        await repo.save(snapshot1)
        await session.commit()

        # Create updated snapshot with same portfolio and date but different values
        snapshot2 = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=Decimal("12000.00"),
            holdings_value=Decimal("8000.00"),
            holdings_count=5,
        )

        # Act
        result = await repo.save(snapshot2)
        await session.commit()

        # Assert - should have updated the existing record
        assert result.portfolio_id == portfolio_id
        assert result.snapshot_date == snapshot_date
        assert result.total_value == Decimal("20000.00")  # Updated
        assert result.cash_balance == Decimal("12000.00")  # Updated
        assert result.holdings_value == Decimal("8000.00")  # Updated
        assert result.holdings_count == 5  # Updated

        # Verify only one snapshot exists for this portfolio+date
        all_snapshots = await repo.get_range(
            portfolio_id, date(2024, 1, 1), date(2024, 12, 31)
        )
        assert len(all_snapshots) == 1

    @pytest.mark.asyncio
    async def test_get_by_portfolio_and_date_found(self, session):
        """Test getting a snapshot by portfolio and date when it exists."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id = uuid4()
        snapshot_date = date(2024, 1, 15)

        snapshot = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("5000.00"),
            holdings_count=3,
        )
        await repo.save(snapshot)
        await session.commit()

        # Act
        result = await repo.get_by_portfolio_and_date(portfolio_id, snapshot_date)

        # Assert
        assert result is not None
        assert result.portfolio_id == portfolio_id
        assert result.snapshot_date == snapshot_date
        assert result.total_value == Decimal("15000.00")

    @pytest.mark.asyncio
    async def test_get_by_portfolio_and_date_not_found(self, session):
        """Test getting a snapshot when it doesn't exist returns None."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id = uuid4()
        snapshot_date = date(2024, 1, 15)

        # Act
        result = await repo.get_by_portfolio_and_date(portfolio_id, snapshot_date)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_range_returns_ordered_snapshots(self, session):
        """Test getting snapshots in a date range returns them ordered by date."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id = uuid4()

        # Create snapshots on different dates
        snapshot1 = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=date(2024, 1, 10),
            cash_balance=Decimal("10000.00"),
            holdings_value=Decimal("5000.00"),
            holdings_count=3,
        )
        snapshot2 = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=date(2024, 1, 20),
            cash_balance=Decimal("11000.00"),
            holdings_value=Decimal("6000.00"),
            holdings_count=4,
        )
        snapshot3 = PortfolioSnapshot.create(
            portfolio_id=portfolio_id,
            snapshot_date=date(2024, 1, 15),
            cash_balance=Decimal("10500.00"),
            holdings_value=Decimal("5500.00"),
            holdings_count=3,
        )

        # Save in random order
        await repo.save(snapshot2)
        await repo.save(snapshot1)
        await repo.save(snapshot3)
        await session.commit()

        # Act
        results = await repo.get_range(
            portfolio_id, date(2024, 1, 1), date(2024, 1, 31)
        )

        # Assert - should be ordered by date ascending
        assert len(results) == 3
        assert results[0].snapshot_date == date(2024, 1, 10)
        assert results[1].snapshot_date == date(2024, 1, 15)
        assert results[2].snapshot_date == date(2024, 1, 20)

    @pytest.mark.asyncio
    async def test_get_range_filters_by_date(self, session):
        """Test that get_range only returns snapshots within the date range."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id = uuid4()

        # Create snapshots on different dates
        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 5),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 15),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 25),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await session.commit()

        # Act - get only middle snapshot
        results = await repo.get_range(
            portfolio_id, date(2024, 1, 10), date(2024, 1, 20)
        )

        # Assert
        assert len(results) == 1
        assert results[0].snapshot_date == date(2024, 1, 15)

    @pytest.mark.asyncio
    async def test_get_range_empty_when_no_data(self, session):
        """Test that get_range returns empty list when no snapshots exist."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id = uuid4()

        # Act
        results = await repo.get_range(
            portfolio_id, date(2024, 1, 1), date(2024, 12, 31)
        )

        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_get_range_filters_by_portfolio(self, session):
        """Test that get_range only returns snapshots for the specified portfolio."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id1 = uuid4()
        portfolio_id2 = uuid4()

        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id1,
                snapshot_date=date(2024, 1, 15),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id2,
                snapshot_date=date(2024, 1, 15),
                cash_balance=Decimal("20000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await session.commit()

        # Act
        results = await repo.get_range(
            portfolio_id1, date(2024, 1, 1), date(2024, 12, 31)
        )

        # Assert
        assert len(results) == 1
        assert results[0].portfolio_id == portfolio_id1

    @pytest.mark.asyncio
    async def test_get_latest_returns_most_recent(self, session):
        """Test that get_latest returns the snapshot with the most recent date."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id = uuid4()

        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 10),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 20),
                cash_balance=Decimal("12000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id,
                snapshot_date=date(2024, 1, 15),
                cash_balance=Decimal("11000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await session.commit()

        # Act
        result = await repo.get_latest(portfolio_id)

        # Assert
        assert result is not None
        assert result.snapshot_date == date(2024, 1, 20)
        assert result.cash_balance == Decimal("12000.00")

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_when_no_snapshots(self, session):
        """Test that get_latest returns None when no snapshots exist."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id = uuid4()

        # Act
        result = await repo.get_latest(portfolio_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_by_portfolio_removes_all(self, session):
        """Test that delete_by_portfolio removes all snapshots for a portfolio."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id1 = uuid4()
        portfolio_id2 = uuid4()

        # Create snapshots for both portfolios
        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id1,
                snapshot_date=date(2024, 1, 10),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id1,
                snapshot_date=date(2024, 1, 15),
                cash_balance=Decimal("10000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await repo.save(
            PortfolioSnapshot.create(
                portfolio_id=portfolio_id2,
                snapshot_date=date(2024, 1, 10),
                cash_balance=Decimal("20000.00"),
                holdings_value=Decimal("0.00"),
                holdings_count=0,
            )
        )
        await session.commit()

        # Act
        deleted_count = await repo.delete_by_portfolio(portfolio_id1)
        await session.commit()

        # Assert
        assert deleted_count == 2

        # Verify portfolio1 snapshots are gone
        portfolio1_snapshots = await repo.get_range(
            portfolio_id1, date(2024, 1, 1), date(2024, 12, 31)
        )
        assert len(portfolio1_snapshots) == 0

        # Verify portfolio2 snapshots are still there
        portfolio2_snapshots = await repo.get_range(
            portfolio_id2, date(2024, 1, 1), date(2024, 12, 31)
        )
        assert len(portfolio2_snapshots) == 1

    @pytest.mark.asyncio
    async def test_delete_by_portfolio_returns_zero_when_no_snapshots(self, session):
        """Test that delete_by_portfolio returns 0 when no snapshots exist."""
        # Arrange
        repo = SQLModelSnapshotRepository(session)
        portfolio_id = uuid4()

        # Act
        deleted_count = await repo.delete_by_portfolio(portfolio_id)
        await session.commit()

        # Assert
        assert deleted_count == 0
