"""Integration tests for SQLModelPortfolioRepository.

Tests the portfolio repository with a real SQLite database to verify
all CRUD operations work correctly.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from zebu.adapters.outbound.database.portfolio_repository import (
    SQLModelPortfolioRepository,
)
from zebu.domain.entities.portfolio import Portfolio


class TestSQLModelPortfolioRepository:
    """Integration tests for SQLModel portfolio repository."""

    @pytest.mark.asyncio
    async def test_save_and_get_portfolio(self, session):
        """Test saving and retrieving a portfolio."""
        # Arrange
        repo = SQLModelPortfolioRepository(session)
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Portfolio",
            created_at=datetime.now(),
        )

        # Act
        await repo.save(portfolio)
        await session.commit()  # Commit to database

        result = await repo.get(portfolio.id)

        # Assert
        assert result is not None
        assert result.id == portfolio.id
        assert result.user_id == portfolio.user_id
        assert result.name == portfolio.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_portfolio_returns_none(self, session):
        """Test getting a portfolio that doesn't exist returns None."""
        # Arrange
        repo = SQLModelPortfolioRepository(session)
        nonexistent_id = uuid4()

        # Act
        result = await repo.get(nonexistent_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_user_returns_all_user_portfolios(self, session):
        """Test getting all portfolios for a user."""
        # Arrange
        repo = SQLModelPortfolioRepository(session)
        user_id = uuid4()
        other_user_id = uuid4()

        portfolio1 = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Portfolio 1",
            created_at=datetime.now(),
        )
        portfolio2 = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Portfolio 2",
            created_at=datetime.now(),
        )
        other_portfolio = Portfolio(
            id=uuid4(),
            user_id=other_user_id,
            name="Other Portfolio",
            created_at=datetime.now(),
        )

        # Act
        await repo.save(portfolio1)
        await repo.save(portfolio2)
        await repo.save(other_portfolio)
        await session.commit()

        result = await repo.get_by_user(user_id)

        # Assert
        assert len(result) == 2
        assert all(p.user_id == user_id for p in result)
        assert {p.name for p in result} == {"Portfolio 1", "Portfolio 2"}

    @pytest.mark.asyncio
    async def test_get_by_user_returns_empty_list_for_no_portfolios(self, session):
        """Test get_by_user returns empty list for user with no portfolios."""
        # Arrange
        repo = SQLModelPortfolioRepository(session)
        user_id = uuid4()

        # Act
        result = await repo.get_by_user(user_id)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing_portfolio(self, session):
        """Test exists returns True for existing portfolio."""
        # Arrange
        repo = SQLModelPortfolioRepository(session)
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Portfolio",
            created_at=datetime.now(),
        )

        # Act
        await repo.save(portfolio)
        await session.commit()

        result = await repo.exists(portfolio.id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_nonexistent_portfolio(self, session):
        """Test exists returns False for non-existent portfolio."""
        # Arrange
        repo = SQLModelPortfolioRepository(session)
        nonexistent_id = uuid4()

        # Act
        result = await repo.exists(nonexistent_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_save_updates_existing_portfolio(self, session):
        """Test saving an existing portfolio updates it."""
        # Arrange
        repo = SQLModelPortfolioRepository(session)
        portfolio_id = uuid4()
        user_id = uuid4()
        portfolio = Portfolio(
            id=portfolio_id,
            user_id=user_id,
            name="Original Name",
            created_at=datetime.now(),
        )

        # Act - Create
        await repo.save(portfolio)
        await session.commit()

        # Act - Update (create new instance with updated name)
        updated_portfolio = Portfolio(
            id=portfolio_id,
            user_id=user_id,
            name="Updated Name",
            created_at=portfolio.created_at,
        )
        await repo.save(updated_portfolio)
        await session.commit()

        # Assert
        result = await repo.get(portfolio_id)
        assert result is not None
        assert result.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_portfolios_returned_in_creation_order(self, session):
        """Test get_by_user returns portfolios in creation order."""
        # Arrange
        repo = SQLModelPortfolioRepository(session)
        user_id = uuid4()

        import time

        portfolio1 = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="First",
            created_at=datetime.now(),
        )
        time.sleep(0.01)  # Ensure different timestamps
        portfolio2 = Portfolio(
            id=uuid4(),
            user_id=user_id,
            name="Second",
            created_at=datetime.now(),
        )

        # Act
        await repo.save(portfolio1)
        await repo.save(portfolio2)
        await session.commit()

        result = await repo.get_by_user(user_id)

        # Assert
        assert len(result) == 2
        assert result[0].name == "First"
        assert result[1].name == "Second"
