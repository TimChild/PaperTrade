"""Tests for WithdrawCash command."""

from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.application.commands.create_portfolio import (
    CreatePortfolioCommand,
    CreatePortfolioHandler,
)
from zebu.application.commands.withdraw_cash import (
    WithdrawCashCommand,
    WithdrawCashHandler,
)
from zebu.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from zebu.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from zebu.domain.entities.transaction import TransactionType
from zebu.domain.exceptions import (
    InsufficientFundsError,
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
    """Provide WithdrawCash handler with repositories."""
    return WithdrawCashHandler(portfolio_repo, transaction_repo)


@pytest.fixture
async def portfolio_with_cash(portfolio_repo, transaction_repo):
    """Create a portfolio with $1000 initial deposit."""
    create_handler = CreatePortfolioHandler(portfolio_repo, transaction_repo)
    result = await create_handler.execute(
        CreatePortfolioCommand(
            user_id=uuid4(),
            name="Test Portfolio",
            initial_deposit_amount=Decimal("1000.00"),
        )
    )
    return result.portfolio_id


class TestWithdrawCash:
    """Tests for WithdrawCash command handler."""

    async def test_valid_withdrawal_succeeds(
        self, handler, transaction_repo, portfolio_with_cash
    ):
        """Test that valid withdrawal succeeds."""
        command = WithdrawCashCommand(
            portfolio_id=portfolio_with_cash,
            amount=Decimal("100.00"),
        )

        result = await handler.execute(command)

        assert result.transaction_id is not None

        # Verify transaction was saved
        transaction = await transaction_repo.get(result.transaction_id)
        assert transaction is not None
        assert transaction.transaction_type == TransactionType.WITHDRAWAL
        assert transaction.cash_change.amount == Decimal("-100.00")

    async def test_withdrawal_entire_balance_succeeds(
        self, handler, transaction_repo, portfolio_with_cash
    ):
        """Test that withdrawing entire balance succeeds."""
        command = WithdrawCashCommand(
            portfolio_id=portfolio_with_cash,
            amount=Decimal("1000.00"),  # Exact balance
        )

        result = await handler.execute(command)

        assert result.transaction_id is not None

        transaction = await transaction_repo.get(result.transaction_id)
        assert transaction.cash_change.amount == Decimal("-1000.00")

    async def test_insufficient_funds_raises_error(self, handler, portfolio_with_cash):
        """Test that withdrawing more than balance raises error."""
        command = WithdrawCashCommand(
            portfolio_id=portfolio_with_cash,
            amount=Decimal("1001.00"),  # More than $1000 balance
        )

        with pytest.raises(InsufficientFundsError) as exc_info:
            await handler.execute(command)

        # New structured error message format
        assert "Insufficient funds" in str(exc_info.value)
        assert "$1,001.00" in str(exc_info.value)  # Money formats with comma
        assert "$1,000.00" in str(exc_info.value)  # Available balance

    async def test_zero_withdrawal_raises_error(self, handler, portfolio_with_cash):
        """Test that zero withdrawal raises error."""
        command = WithdrawCashCommand(
            portfolio_id=portfolio_with_cash,
            amount=Decimal("0.00"),
        )

        with pytest.raises(InvalidTransactionError):
            await handler.execute(command)

    async def test_negative_withdrawal_raises_error(self, handler, portfolio_with_cash):
        """Test that negative withdrawal raises error."""
        command = WithdrawCashCommand(
            portfolio_id=portfolio_with_cash,
            amount=Decimal("-100.00"),
        )

        with pytest.raises(InvalidTransactionError):
            await handler.execute(command)

    async def test_portfolio_not_found_raises_error(self, handler):
        """Test that withdrawing from non-existent portfolio raises error."""
        command = WithdrawCashCommand(
            portfolio_id=uuid4(),  # Random ID that doesn't exist
            amount=Decimal("100.00"),
        )

        with pytest.raises(InvalidPortfolioError):
            await handler.execute(command)

    async def test_withdrawal_with_notes(
        self, handler, transaction_repo, portfolio_with_cash
    ):
        """Test that withdrawal can include notes."""
        command = WithdrawCashCommand(
            portfolio_id=portfolio_with_cash,
            amount=Decimal("50.00"),
            notes="Test withdrawal",
        )

        result = await handler.execute(command)

        transaction = await transaction_repo.get(result.transaction_id)
        assert transaction.notes == "Test withdrawal"

    async def test_different_currencies_supported(
        self, portfolio_repo, transaction_repo, handler
    ):
        """Test that different currencies can be used for withdrawal."""
        # Create portfolio with EUR
        create_handler = CreatePortfolioHandler(portfolio_repo, transaction_repo)
        result = await create_handler.execute(
            CreatePortfolioCommand(
                user_id=uuid4(),
                name="EUR Portfolio",
                initial_deposit_amount=Decimal("1000.00"),
                initial_deposit_currency="EUR",
            )
        )

        command = WithdrawCashCommand(
            portfolio_id=result.portfolio_id,
            amount=Decimal("100.00"),
            currency="EUR",
        )

        withdraw_result = await handler.execute(command)

        transaction = await transaction_repo.get(withdraw_result.transaction_id)
        assert transaction.cash_change.currency == "EUR"
