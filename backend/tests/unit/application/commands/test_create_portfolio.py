"""Tests for CreatePortfolio command."""

from decimal import Decimal
from uuid import uuid4

import pytest

from papertrade.application.commands.create_portfolio import (
    CreatePortfolioCommand,
    CreatePortfolioHandler,
)
from papertrade.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from papertrade.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from papertrade.domain.entities.transaction import TransactionType
from papertrade.domain.exceptions import (
    InvalidPortfolioError,
    InvalidTransactionError,
)


@pytest.fixture
def portfolio_repo():
    """Provide clean in-memory portfolio repository."""
    return InMemoryPortfolioRepository()


@pytest.fixture
def transaction_repo():
    """Provide clean in-memory transaction repository."""
    return InMemoryTransactionRepository()


@pytest.fixture
def handler(portfolio_repo, transaction_repo):
    """Provide CreatePortfolio handler with repositories."""
    return CreatePortfolioHandler(portfolio_repo, transaction_repo)


class TestCreatePortfolio:
    """Tests for CreatePortfolio command handler."""

    async def test_valid_creation_succeeds(
        self, handler, portfolio_repo, transaction_repo
    ):
        """Test that valid portfolio creation succeeds."""
        # Arrange
        user_id = uuid4()
        command = CreatePortfolioCommand(
            user_id=user_id,
            name="My Portfolio",
            initial_deposit_amount=Decimal("1000.00"),
            initial_deposit_currency="USD",
        )

        # Act
        result = await handler.execute(command)

        # Assert
        assert result.portfolio_id is not None
        assert result.transaction_id is not None

        # Verify portfolio was saved
        portfolio = await portfolio_repo.get(result.portfolio_id)
        assert portfolio is not None
        assert portfolio.user_id == user_id
        assert portfolio.name == "My Portfolio"

        # Verify transaction was saved
        transaction = await transaction_repo.get(result.transaction_id)
        assert transaction is not None
        assert transaction.portfolio_id == result.portfolio_id
        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.cash_change.amount == Decimal("1000.00")
        assert transaction.cash_change.currency == "USD"
        assert transaction.notes == "Initial portfolio deposit"

    async def test_zero_deposit_raises_error(self, handler):
        """Test that zero initial deposit raises InvalidTransactionError."""
        command = CreatePortfolioCommand(
            user_id=uuid4(),
            name="My Portfolio",
            initial_deposit_amount=Decimal("0.00"),
        )

        with pytest.raises(InvalidTransactionError):
            await handler.execute(command)

    async def test_negative_deposit_raises_error(self, handler):
        """Test that negative initial deposit raises InvalidTransactionError."""
        command = CreatePortfolioCommand(
            user_id=uuid4(),
            name="My Portfolio",
            initial_deposit_amount=Decimal("-100.00"),
        )

        with pytest.raises(InvalidTransactionError):
            await handler.execute(command)

    async def test_empty_name_raises_error(self, handler):
        """Test that empty portfolio name raises InvalidPortfolioError."""
        command = CreatePortfolioCommand(
            user_id=uuid4(),
            name="",
            initial_deposit_amount=Decimal("1000.00"),
        )

        with pytest.raises(InvalidPortfolioError):
            await handler.execute(command)

    async def test_whitespace_only_name_raises_error(self, handler):
        """Test that whitespace-only name raises InvalidPortfolioError."""
        command = CreatePortfolioCommand(
            user_id=uuid4(),
            name="   ",
            initial_deposit_amount=Decimal("1000.00"),
        )

        with pytest.raises(InvalidPortfolioError):
            await handler.execute(command)

    async def test_name_too_long_raises_error(self, handler):
        """Test that name exceeding 100 characters raises InvalidPortfolioError."""
        command = CreatePortfolioCommand(
            user_id=uuid4(),
            name="A" * 101,  # 101 characters
            initial_deposit_amount=Decimal("1000.00"),
        )

        with pytest.raises(InvalidPortfolioError):
            await handler.execute(command)

    async def test_can_retrieve_created_portfolio(self, handler, portfolio_repo):
        """Test that created portfolio can be retrieved."""
        command = CreatePortfolioCommand(
            user_id=uuid4(),
            name="My Portfolio",
            initial_deposit_amount=Decimal("1000.00"),
        )

        result = await handler.execute(command)
        portfolio = await portfolio_repo.get(result.portfolio_id)

        assert portfolio is not None
        assert portfolio.id == result.portfolio_id

    async def test_initial_transaction_recorded_correctly(
        self, handler, transaction_repo
    ):
        """Test that initial transaction is recorded with correct values."""
        command = CreatePortfolioCommand(
            user_id=uuid4(),
            name="My Portfolio",
            initial_deposit_amount=Decimal("5000.00"),
            initial_deposit_currency="EUR",
        )

        result = await handler.execute(command)
        transaction = await transaction_repo.get(result.transaction_id)

        assert transaction is not None
        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.cash_change.amount == Decimal("5000.00")
        assert transaction.cash_change.currency == "EUR"
        assert transaction.ticker is None
        assert transaction.quantity is None
        assert transaction.price_per_share is None

    async def test_different_currencies_supported(self, handler, transaction_repo):
        """Test that different currencies can be used for initial deposit."""
        currencies = ["USD", "EUR", "GBP", "JPY"]

        for currency in currencies:
            command = CreatePortfolioCommand(
                user_id=uuid4(),
                name=f"Portfolio {currency}",
                initial_deposit_amount=Decimal("1000.00"),
                initial_deposit_currency=currency,
            )

            result = await handler.execute(command)
            transaction = await transaction_repo.get(result.transaction_id)

            assert transaction.cash_change.currency == currency
