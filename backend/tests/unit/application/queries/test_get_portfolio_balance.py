"""Tests for GetPortfolioBalance query with market data integration."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from zebu.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from zebu.application.dtos.price_point import PricePoint
from zebu.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from zebu.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from zebu.application.queries.get_portfolio_balance import (
    GetPortfolioBalanceHandler,
    GetPortfolioBalanceQuery,
)
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.exceptions import InvalidPortfolioError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


@pytest.fixture
def portfolio_repo():
    """Provide clean in-memory portfolio repository."""
    return InMemoryPortfolioRepository()


@pytest.fixture
def transaction_repo():
    """Provide clean in-memory transaction repository."""
    return InMemoryTransactionRepository()


@pytest.fixture
def market_data():
    """Provide in-memory market data adapter."""
    return InMemoryMarketDataAdapter()


@pytest.fixture
def handler(portfolio_repo, transaction_repo, market_data):
    """Provide GetPortfolioBalance handler with dependencies."""
    return GetPortfolioBalanceHandler(portfolio_repo, transaction_repo, market_data)


@pytest.fixture
async def sample_portfolio(portfolio_repo):
    """Create a sample portfolio."""
    user_id = uuid4()
    portfolio = Portfolio(
        id=uuid4(),
        user_id=user_id,
        name="Test Portfolio",
        created_at=datetime.now(UTC),
    )
    await portfolio_repo.save(portfolio)
    return portfolio


class TestGetPortfolioBalance:
    """Tests for GetPortfolioBalance query handler."""

    async def test_cash_only_portfolio(
        self, handler, sample_portfolio, transaction_repo
    ):
        """Test portfolio balance with only cash (no holdings)."""
        # Arrange - Create deposit transaction
        deposit = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("10000.00"), "USD"),
            notes="Initial deposit",
        )
        await transaction_repo.save(deposit)

        query = GetPortfolioBalanceQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert
        assert result.portfolio_id == sample_portfolio.id
        assert result.cash_balance.amount == Decimal("10000.00")
        assert result.holdings_value.amount == Decimal("0")
        assert result.total_value.amount == Decimal("10000.00")
        assert result.currency == "USD"

    async def test_portfolio_with_holdings_and_real_prices(
        self, handler, sample_portfolio, transaction_repo, market_data
    ):
        """Test portfolio balance calculation with real market prices."""
        # Arrange - Create initial deposit
        deposit = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("20000.00"), "USD"),
            notes="Initial deposit",
        )
        await transaction_repo.save(deposit)

        # Create buy transaction for AAPL
        buy_aapl = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("-15000.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("100")),
            price_per_share=Money(Decimal("150.00"), "USD"),
            notes="Buy AAPL",
        )
        await transaction_repo.save(buy_aapl)

        # Seed market data with current AAPL price
        current_price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("175.00"), "USD"),
            timestamp=datetime.now(UTC),
            source="alpha_vantage",
            interval="1day",
        )
        market_data.seed_price(current_price)

        query = GetPortfolioBalanceQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert
        assert result.cash_balance.amount == Decimal("5000.00")  # 20000 - 15000
        assert result.holdings_value.amount == Decimal("17500.00")  # 100 * 175.00
        assert result.total_value.amount == Decimal("22500.00")  # 5000 + 17500

    async def test_portfolio_with_multiple_holdings(
        self, handler, sample_portfolio, transaction_repo, market_data
    ):
        """Test portfolio balance with multiple stock positions."""
        # Arrange - Deposit and buy transactions
        deposit = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("50000.00"), "USD"),
            notes="Initial deposit",
        )
        await transaction_repo.save(deposit)

        # Buy AAPL
        buy_aapl = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("-15000.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("100")),
            price_per_share=Money(Decimal("150.00"), "USD"),
            notes="Buy AAPL",
        )
        await transaction_repo.save(buy_aapl)

        # Buy GOOGL
        buy_googl = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("-20000.00"), "USD"),
            ticker=Ticker("GOOGL"),
            quantity=Quantity(Decimal("200")),
            price_per_share=Money(Decimal("100.00"), "USD"),
            notes="Buy GOOGL",
        )
        await transaction_repo.save(buy_googl)

        # Seed market data
        market_data.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("175.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )
        market_data.seed_price(
            PricePoint(
                ticker=Ticker("GOOGL"),
                price=Money(Decimal("120.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )

        query = GetPortfolioBalanceQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert
        # 50000 - 15000 - 20000
        assert result.cash_balance.amount == Decimal("15000.00")
        # AAPL: 100 * 175 = 17500, GOOGL: 200 * 120 = 24000
        assert result.holdings_value.amount == Decimal("41500.00")
        assert result.total_value.amount == Decimal("56500.00")  # 15000 + 41500

    async def test_handles_ticker_not_found_gracefully(
        self, handler, sample_portfolio, transaction_repo, market_data
    ):
        """Test graceful handling when ticker price is not found."""
        # Arrange
        deposit = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("10000.00"), "USD"),
            notes="Initial deposit",
        )
        await transaction_repo.save(deposit)

        # Buy stock with unknown ticker (max 5 chars)
        buy = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("-5000.00"), "USD"),
            ticker=Ticker("UNKN"),  # Unknown ticker, max 5 chars
            quantity=Quantity(Decimal("100")),
            price_per_share=Money(Decimal("50.00"), "USD"),
            notes="Buy UNKN",
        )
        await transaction_repo.save(buy)

        # Don't seed price for UNKN ticker - will raise TickerNotFoundError

        query = GetPortfolioBalanceQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert - Should not raise error, just skip the holding
        assert result.cash_balance.amount == Decimal("5000.00")
        assert result.holdings_value.amount == Decimal("0")  # Unknown ticker value = 0
        assert result.total_value.amount == Decimal("5000.00")

    async def test_portfolio_not_found_raises_error(self, handler):
        """Test that querying non-existent portfolio raises error."""
        # Arrange
        non_existent_id = uuid4()
        query = GetPortfolioBalanceQuery(portfolio_id=non_existent_id)

        # Act & Assert
        with pytest.raises(InvalidPortfolioError):
            await handler.execute(query)

    async def test_empty_portfolio_returns_zero_balance(
        self, handler, sample_portfolio
    ):
        """Test empty portfolio (no transactions) returns zero balance."""
        # Arrange
        query = GetPortfolioBalanceQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert
        assert result.cash_balance.amount == Decimal("0")
        assert result.holdings_value.amount == Decimal("0")
        assert result.total_value.amount == Decimal("0")
