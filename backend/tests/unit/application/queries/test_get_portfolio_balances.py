"""Tests for GetPortfolioBalances batch query handler."""

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
from zebu.application.queries.get_portfolio_balances import (
    GetPortfolioBalancesHandler,
    GetPortfolioBalancesQuery,
)
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.transaction import Transaction, TransactionType
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
    """Provide GetPortfolioBalances handler with dependencies."""
    return GetPortfolioBalancesHandler(portfolio_repo, transaction_repo, market_data)


async def make_portfolio(portfolio_repo: InMemoryPortfolioRepository) -> Portfolio:
    """Helper to create and save a portfolio."""
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Test Portfolio",
        created_at=datetime.now(UTC),
    )
    await portfolio_repo.save(portfolio)
    return portfolio


class TestGetPortfolioBalancesHandler:
    """Tests for GetPortfolioBalances batch query handler."""

    async def test_empty_portfolio_ids_returns_empty_result(self, handler):
        """Test that empty input returns empty result."""
        query = GetPortfolioBalancesQuery(portfolio_ids=[])
        result = await handler.execute(query)
        assert result.balances == []

    async def test_cash_only_portfolios(
        self, handler, portfolio_repo, transaction_repo
    ):
        """Test batch balance for cash-only portfolios."""
        portfolio_1 = await make_portfolio(portfolio_repo)
        portfolio_2 = await make_portfolio(portfolio_repo)

        # Deposit $10k in portfolio 1
        deposit_1 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_1.id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("10000.00"), "USD"),
        )
        await transaction_repo.save(deposit_1)

        # Deposit $5k in portfolio 2
        deposit_2 = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_2.id,
            transaction_type=TransactionType.DEPOSIT,
            timestamp=datetime.now(UTC),
            cash_change=Money(Decimal("5000.00"), "USD"),
        )
        await transaction_repo.save(deposit_2)

        query = GetPortfolioBalancesQuery(
            portfolio_ids=[portfolio_1.id, portfolio_2.id]
        )
        result = await handler.execute(query)

        assert len(result.balances) == 2
        # Results are in same order as input
        b1 = next(b for b in result.balances if b.portfolio_id == portfolio_1.id)
        b2 = next(b for b in result.balances if b.portfolio_id == portfolio_2.id)
        assert b1.cash_balance.amount == Decimal("10000.00")
        assert b1.holdings_value.amount == Decimal("0")
        assert b2.cash_balance.amount == Decimal("5000.00")
        assert b2.holdings_value.amount == Decimal("0")

    async def test_portfolios_with_holdings(
        self, handler, portfolio_repo, transaction_repo, market_data
    ):
        """Test batch balance for portfolios with stock holdings."""
        portfolio_1 = await make_portfolio(portfolio_repo)
        portfolio_2 = await make_portfolio(portfolio_repo)

        # Portfolio 1: deposit + buy AAPL
        await transaction_repo.save(
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_1.id,
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("20000.00"), "USD"),
            )
        )
        await transaction_repo.save(
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_1.id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-15000.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("100")),
                price_per_share=Money(Decimal("150.00"), "USD"),
            )
        )

        # Portfolio 2: deposit + buy GOOGL
        await transaction_repo.save(
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_2.id,
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("30000.00"), "USD"),
            )
        )
        await transaction_repo.save(
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_2.id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-20000.00"), "USD"),
                ticker=Ticker("GOOGL"),
                quantity=Quantity(Decimal("200")),
                price_per_share=Money(Decimal("100.00"), "USD"),
            )
        )

        # Seed market prices
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

        query = GetPortfolioBalancesQuery(
            portfolio_ids=[portfolio_1.id, portfolio_2.id]
        )
        result = await handler.execute(query)

        assert len(result.balances) == 2
        b1 = next(b for b in result.balances if b.portfolio_id == portfolio_1.id)
        b2 = next(b for b in result.balances if b.portfolio_id == portfolio_2.id)

        # Portfolio 1: 20000 - 15000 = 5000 cash, 100 * 175 = 17500 holdings
        assert b1.cash_balance.amount == Decimal("5000.00")
        assert b1.holdings_value.amount == Decimal("17500.00")
        assert b1.total_value.amount == Decimal("22500.00")

        # Portfolio 2: 30000 - 20000 = 10000 cash, 200 * 120 = 24000 holdings
        assert b2.cash_balance.amount == Decimal("10000.00")
        assert b2.holdings_value.amount == Decimal("24000.00")
        assert b2.total_value.amount == Decimal("34000.00")

    async def test_portfolio_with_no_transactions_returns_zero(
        self, handler, portfolio_repo
    ):
        """Test that a portfolio with no transactions returns zero balance."""
        portfolio = await make_portfolio(portfolio_repo)

        query = GetPortfolioBalancesQuery(portfolio_ids=[portfolio.id])
        result = await handler.execute(query)

        assert len(result.balances) == 1
        b = result.balances[0]
        assert b.cash_balance.amount == Decimal("0")
        assert b.holdings_value.amount == Decimal("0")
        assert b.total_value.amount == Decimal("0")

    async def test_order_preserved_in_results(
        self, handler, portfolio_repo, transaction_repo
    ):
        """Test that results maintain the same order as input portfolio_ids."""
        portfolios = [await make_portfolio(portfolio_repo) for _ in range(3)]
        ids = [p.id for p in portfolios]

        # Add different deposits
        for i, portfolio in enumerate(portfolios):
            await transaction_repo.save(
                Transaction(
                    id=uuid4(),
                    portfolio_id=portfolio.id,
                    transaction_type=TransactionType.DEPOSIT,
                    timestamp=datetime.now(UTC),
                    cash_change=Money(Decimal(f"{(i + 1) * 1000}.00"), "USD"),
                )
            )

        query = GetPortfolioBalancesQuery(portfolio_ids=ids)
        result = await handler.execute(query)

        assert len(result.balances) == 3
        for i, balance in enumerate(result.balances):
            assert balance.portfolio_id == ids[i]
