"""Tests for DeletePortfolio command."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.application.commands.create_portfolio import (
    CreatePortfolioCommand,
    CreatePortfolioHandler,
)
from zebu.application.commands.delete_portfolio import (
    DeletePortfolioCommand,
    DeletePortfolioHandler,
)
from zebu.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from zebu.application.ports.in_memory_snapshot_repository import (
    InMemorySnapshotRepository,
)
from zebu.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.exceptions import PortfolioNotFoundError


@pytest.fixture
def portfolio_repo():
    """Provide clean in-memory portfolio repository."""
    return InMemoryPortfolioRepository()


@pytest.fixture
def transaction_repo():
    """Provide clean in-memory transaction repository."""
    return InMemoryTransactionRepository()


@pytest.fixture
def snapshot_repo():
    """Provide clean in-memory snapshot repository."""
    return InMemorySnapshotRepository()


@pytest.fixture
def handler(portfolio_repo, transaction_repo, snapshot_repo):
    """Provide DeletePortfolio handler with repositories."""
    return DeletePortfolioHandler(portfolio_repo, transaction_repo, snapshot_repo)


@pytest.fixture
def create_handler(portfolio_repo, transaction_repo):
    """Provide CreatePortfolio handler for test setup."""
    return CreatePortfolioHandler(portfolio_repo, transaction_repo)


class TestDeletePortfolio:
    """Tests for DeletePortfolio command handler."""

    async def test_delete_existing_portfolio_succeeds(
        self, handler, create_handler, portfolio_repo, transaction_repo
    ):
        """Test that deleting an existing portfolio succeeds."""
        # Arrange - Create a portfolio first
        user_id = uuid4()
        create_command = CreatePortfolioCommand(
            user_id=user_id,
            name="Test Portfolio",
            initial_deposit_amount=Decimal("1000.00"),
        )
        create_result = await create_handler.execute(create_command)
        portfolio_id = create_result.portfolio_id

        # Verify portfolio and transaction exist
        assert await portfolio_repo.get(portfolio_id) is not None
        transactions = await transaction_repo.get_by_portfolio(portfolio_id)
        assert len(transactions) == 1

        # Act - Delete the portfolio
        delete_command = DeletePortfolioCommand(
            portfolio_id=portfolio_id,
            user_id=user_id,
        )
        await handler.execute(delete_command)

        # Assert - Verify portfolio and transactions are gone
        assert await portfolio_repo.get(portfolio_id) is None
        transactions_after = await transaction_repo.get_by_portfolio(portfolio_id)
        assert len(transactions_after) == 0

    async def test_delete_nonexistent_portfolio_raises_error(self, handler):
        """Test that deleting a non-existent portfolio raises PortfolioNotFoundError."""
        # Arrange
        nonexistent_id = uuid4()
        command = DeletePortfolioCommand(
            portfolio_id=nonexistent_id,
            user_id=uuid4(),
        )

        # Act & Assert
        with pytest.raises(PortfolioNotFoundError) as exc_info:
            await handler.execute(command)

        assert str(nonexistent_id) in str(exc_info.value)

    async def test_delete_wrong_user_raises_permission_error(
        self, handler, create_handler
    ):
        """Test that deleting another user's portfolio raises PermissionError."""
        # Arrange - Create portfolio owned by user1
        user1_id = uuid4()
        user2_id = uuid4()

        create_command = CreatePortfolioCommand(
            user_id=user1_id,
            name="User 1 Portfolio",
            initial_deposit_amount=Decimal("1000.00"),
        )
        create_result = await create_handler.execute(create_command)
        portfolio_id = create_result.portfolio_id

        # Act & Assert - Try to delete with user2
        command = DeletePortfolioCommand(
            portfolio_id=portfolio_id,
            user_id=user2_id,
        )

        with pytest.raises(PermissionError) as exc_info:
            await handler.execute(command)

        assert str(user2_id) in str(exc_info.value)
        assert str(portfolio_id) in str(exc_info.value)

    async def test_delete_removes_all_transactions(
        self,
        handler,
        create_handler,
        portfolio_repo,
        transaction_repo,
    ):
        """Test that deleting a portfolio removes all its transactions."""
        # Arrange - Create a portfolio with initial transaction
        user_id = uuid4()
        create_command = CreatePortfolioCommand(
            user_id=user_id,
            name="Test Portfolio",
            initial_deposit_amount=Decimal("1000.00"),
        )
        create_result = await create_handler.execute(create_command)
        portfolio_id = create_result.portfolio_id

        # Verify we have the initial transaction
        transactions_before = await transaction_repo.get_by_portfolio(portfolio_id)
        assert len(transactions_before) == 1

        # Act - Delete portfolio
        delete_command = DeletePortfolioCommand(
            portfolio_id=portfolio_id,
            user_id=user_id,
        )
        await handler.execute(delete_command)

        # Assert - Verify all transactions are deleted
        transactions_after = await transaction_repo.get_by_portfolio(portfolio_id)
        assert len(transactions_after) == 0

    async def test_delete_portfolio_with_no_transactions(
        self,
        handler,
        portfolio_repo,
        transaction_repo,
    ):
        """Test deleting a portfolio that somehow has no transactions."""
        # Arrange - Create portfolio directly without transactions
        user_id = uuid4()
        portfolio_id = uuid4()
        portfolio = Portfolio(
            id=portfolio_id,
            user_id=user_id,
            name="Empty Portfolio",
            created_at=datetime.now(UTC),
        )
        await portfolio_repo.save(portfolio)

        # Act - Delete the portfolio
        delete_command = DeletePortfolioCommand(
            portfolio_id=portfolio_id,
            user_id=user_id,
        )
        await handler.execute(delete_command)

        # Assert - Portfolio should be deleted
        assert await portfolio_repo.get(portfolio_id) is None

    async def test_delete_multiple_portfolios_independently(
        self,
        handler,
        create_handler,
        portfolio_repo,
    ):
        """Test that deleting one portfolio doesn't affect others."""
        # Arrange - Create two portfolios for the same user
        user_id = uuid4()

        create_command1 = CreatePortfolioCommand(
            user_id=user_id,
            name="Portfolio 1",
            initial_deposit_amount=Decimal("1000.00"),
        )
        result1 = await create_handler.execute(create_command1)

        create_command2 = CreatePortfolioCommand(
            user_id=user_id,
            name="Portfolio 2",
            initial_deposit_amount=Decimal("2000.00"),
        )
        result2 = await create_handler.execute(create_command2)

        # Act - Delete first portfolio
        delete_command = DeletePortfolioCommand(
            portfolio_id=result1.portfolio_id,
            user_id=user_id,
        )
        await handler.execute(delete_command)

        # Assert - First portfolio deleted, second still exists
        assert await portfolio_repo.get(result1.portfolio_id) is None
        assert await portfolio_repo.get(result2.portfolio_id) is not None
