"""Tests for GetPortfolioHoldings query with market data integration."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from papertrade.adapters.outbound.market_data.in_memory_adapter import (
    InMemoryMarketDataAdapter,
)
from papertrade.application.dtos.price_point import PricePoint
from papertrade.application.ports.in_memory_portfolio_repository import (
    InMemoryPortfolioRepository,
)
from papertrade.application.ports.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)
from papertrade.application.queries.get_portfolio_holdings import (
    GetPortfolioHoldingsHandler,
    GetPortfolioHoldingsQuery,
)
from papertrade.domain.entities.portfolio import Portfolio
from papertrade.domain.entities.transaction import Transaction, TransactionType
from papertrade.domain.exceptions import InvalidPortfolioError
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.quantity import Quantity
from papertrade.domain.value_objects.ticker import Ticker


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
    """Provide GetPortfolioHoldings handler with dependencies."""
    return GetPortfolioHoldingsHandler(portfolio_repo, transaction_repo, market_data)


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


class TestGetPortfolioHoldings:
    """Tests for GetPortfolioHoldings query handler."""

    async def test_empty_portfolio_returns_no_holdings(self, handler, sample_portfolio):
        """Test that empty portfolio returns empty holdings list."""
        # Arrange
        query = GetPortfolioHoldingsQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert
        assert result.portfolio_id == sample_portfolio.id
        assert len(result.holdings) == 0

    async def test_single_holding_with_real_price(
        self, handler, sample_portfolio, transaction_repo, market_data
    ):
        """Test single holding enriched with real market price."""
        # Arrange - Buy AAPL
        buy = Transaction(
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
        await transaction_repo.save(buy)

        # Seed market data
        current_price = PricePoint(
            ticker=Ticker("AAPL"),
            price=Money(Decimal("175.00"), "USD"),
            timestamp=datetime.now(UTC),
            source="alpha_vantage",
            interval="1day",
        )
        market_data.seed_price(current_price)

        query = GetPortfolioHoldingsQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert
        assert len(result.holdings) == 1
        holding = result.holdings[0]

        # Basic holding data
        assert holding.ticker_symbol == "AAPL"
        assert holding.quantity_shares == Decimal("100")
        assert holding.cost_basis_amount == Decimal("15000.00")
        assert holding.average_cost_per_share_amount == Decimal("150.00")

        # Market data fields
        assert holding.current_price_amount == Decimal("175.00")
        assert holding.market_value_amount == Decimal("17500.00")  # 100 * 175
        # 17500 - 15000
        assert holding.unrealized_gain_loss_amount == Decimal("2500.00")
        # Allow slight precision difference in percentage calculation
        expected_percent = Decimal("16.666666666666666666666666667")
        assert abs(holding.unrealized_gain_loss_percent - expected_percent) < Decimal(
            "0.0001"
        )
        assert holding.price_timestamp is not None
        assert holding.price_source == "alpha_vantage"

    async def test_multiple_holdings_with_real_prices(
        self, handler, sample_portfolio, transaction_repo, market_data
    ):
        """Test multiple holdings enriched with real market prices."""
        # Arrange - Buy AAPL and GOOGL
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
                price=Money(Decimal("90.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )

        query = GetPortfolioHoldingsQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert
        assert len(result.holdings) == 2

        # Find holdings by ticker
        aapl_holding = next(h for h in result.holdings if h.ticker_symbol == "AAPL")
        googl_holding = next(h for h in result.holdings if h.ticker_symbol == "GOOGL")

        # AAPL - gained value
        assert aapl_holding.current_price_amount == Decimal("175.00")
        assert aapl_holding.market_value_amount == Decimal("17500.00")
        assert aapl_holding.unrealized_gain_loss_amount == Decimal("2500.00")
        assert aapl_holding.unrealized_gain_loss_percent > Decimal("0")

        # GOOGL - lost value
        assert googl_holding.current_price_amount == Decimal("90.00")
        assert googl_holding.market_value_amount == Decimal("18000.00")  # 200 * 90
        # 18000 - 20000
        assert googl_holding.unrealized_gain_loss_amount == Decimal("-2000.00")
        assert googl_holding.unrealized_gain_loss_percent < Decimal("0")

    async def test_holding_without_price_data_returns_partial_info(
        self, handler, sample_portfolio, transaction_repo, market_data
    ):
        """Test that holdings without price data still return basic info."""
        # Arrange - Buy stock without seeding price
        buy = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("-5000.00"), "USD"),
            ticker=Ticker("UNKN"),  # Unknown ticker, max 5 chars
            quantity=Quantity(Decimal("50")),
            price_per_share=Money(Decimal("100.00"), "USD"),
            notes="Buy UNKN",
        )
        await transaction_repo.save(buy)

        # Don't seed price data for UNKN

        query = GetPortfolioHoldingsQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert
        assert len(result.holdings) == 1
        holding = result.holdings[0]

        # Basic data should be present
        assert holding.ticker_symbol == "UNKN"
        assert holding.quantity_shares == Decimal("50")
        assert holding.cost_basis_amount == Decimal("5000.00")
        assert holding.average_cost_per_share_amount == Decimal("100.00")

        # Market data fields should be None
        assert holding.current_price_amount is None
        assert holding.market_value_amount is None
        assert holding.unrealized_gain_loss_amount is None
        assert holding.unrealized_gain_loss_percent is None
        assert holding.price_timestamp is None
        assert holding.price_source is None

    async def test_buy_and_sell_updates_holding_quantity(
        self, handler, sample_portfolio, transaction_repo, market_data
    ):
        """Test that buy/sell transactions correctly update holding quantity."""
        # Arrange - Buy then sell some shares
        buy = Transaction(
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
        await transaction_repo.save(buy)

        sell = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.SELL,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("8750.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("50")),  # Positive for sell
            price_per_share=Money(Decimal("175.00"), "USD"),
            notes="Sell AAPL",
        )
        await transaction_repo.save(sell)

        # Seed market data
        market_data.seed_price(
            PricePoint(
                ticker=Ticker("AAPL"),
                price=Money(Decimal("180.00"), "USD"),
                timestamp=datetime.now(UTC),
                source="alpha_vantage",
                interval="1day",
            )
        )

        query = GetPortfolioHoldingsQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert
        assert len(result.holdings) == 1
        holding = result.holdings[0]

        # Should have 50 shares remaining
        assert holding.quantity_shares == Decimal("50")
        # Cost basis should be for 50 shares at $150 = $7500
        assert holding.cost_basis_amount == Decimal("7500.00")
        # Market value: 50 * 180 = 9000
        assert holding.market_value_amount == Decimal("9000.00")

    async def test_portfolio_not_found_raises_error(self, handler):
        """Test that querying non-existent portfolio raises error."""
        # Arrange
        non_existent_id = uuid4()
        query = GetPortfolioHoldingsQuery(portfolio_id=non_existent_id)

        # Act & Assert
        with pytest.raises(InvalidPortfolioError):
            await handler.execute(query)

    async def test_fully_sold_position_not_in_holdings(
        self, handler, sample_portfolio, transaction_repo, market_data
    ):
        """Test that fully sold positions don't appear in holdings."""
        # Arrange - Buy and then sell all shares
        buy = Transaction(
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
        await transaction_repo.save(buy)

        sell_all = Transaction(
            id=uuid4(),
            portfolio_id=sample_portfolio.id,
            transaction_type=TransactionType.SELL,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("17500.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("100")),  # Positive for sell
            price_per_share=Money(Decimal("175.00"), "USD"),
            notes="Sell all AAPL",
        )
        await transaction_repo.save(sell_all)

        query = GetPortfolioHoldingsQuery(portfolio_id=sample_portfolio.id)

        # Act
        result = await handler.execute(query)

        # Assert - No holdings should be returned
        assert len(result.holdings) == 0
