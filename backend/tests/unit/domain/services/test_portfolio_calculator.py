"""Tests for PortfolioCalculator service."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from papertrade.domain.entities import Holding, Transaction, TransactionType
from papertrade.domain.services import PortfolioCalculator
from papertrade.domain.value_objects import Money, Quantity, Ticker


class TestCalculateCashBalance:
    """Test PortfolioCalculator.calculate_cash_balance."""

    def test_empty_transactions_returns_zero(self) -> None:
        """Test that empty transaction list returns zero balance."""
        balance = PortfolioCalculator.calculate_cash_balance([])
        assert balance == Money(Decimal("0.00"), "USD")

    def test_single_deposit(self) -> None:
        """Test calculating balance with single deposit."""
        portfolio_id = uuid4()
        txn = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            type=TransactionType.DEPOSIT,
            amount=Money(Decimal("1000.00"), "USD"),
            timestamp=datetime.now(timezone.utc),
        )
        balance = PortfolioCalculator.calculate_cash_balance([txn])
        assert balance == Money(Decimal("1000.00"), "USD")

    def test_deposit_and_withdrawal(self) -> None:
        """Test calculating balance with deposit and withdrawal."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("1000.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.WITHDRAWAL,
                amount=Money(Decimal("300.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        balance = PortfolioCalculator.calculate_cash_balance(txns)
        assert balance == Money(Decimal("700.00"), "USD")

    def test_buy_transaction_reduces_cash(self) -> None:
        """Test that buy transaction reduces cash balance."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("1000.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(Decimal("500.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("50.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        balance = PortfolioCalculator.calculate_cash_balance(txns)
        assert balance == Money(Decimal("500.00"), "USD")

    def test_sell_transaction_increases_cash(self) -> None:
        """Test that sell transaction increases cash balance."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("1000.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.SELL,
                amount=Money(Decimal("600.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("60.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        balance = PortfolioCalculator.calculate_cash_balance(txns)
        assert balance == Money(Decimal("1600.00"), "USD")

    def test_dividend_transaction_increases_cash(self) -> None:
        """Test that dividend transaction increases cash balance."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("1000.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DIVIDEND,
                amount=Money(Decimal("50.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        balance = PortfolioCalculator.calculate_cash_balance(txns)
        assert balance == Money(Decimal("1050.00"), "USD")

    def test_fee_transaction_reduces_cash(self) -> None:
        """Test that fee transaction reduces cash balance."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("1000.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.FEE,
                amount=Money(Decimal("10.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        balance = PortfolioCalculator.calculate_cash_balance(txns)
        assert balance == Money(Decimal("990.00"), "USD")

    def test_complex_transaction_history(self) -> None:
        """Test calculating balance with complex transaction history."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("10000.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(Decimal("1500.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(Decimal("2800.00"), "USD"),
                ticker=Ticker("GOOGL"),
                quantity=Quantity(Decimal("1")),
                price_per_share=Money(Decimal("2800.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.SELL,
                amount=Money(Decimal("800.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("5")),
                price_per_share=Money(Decimal("160.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.WITHDRAWAL,
                amount=Money(Decimal("1000.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        balance = PortfolioCalculator.calculate_cash_balance(txns)
        # 10000 - 1500 - 2800 + 800 - 1000 = 5500
        assert balance == Money(Decimal("5500.00"), "USD")


class TestCalculateHoldings:
    """Test PortfolioCalculator.calculate_holdings."""

    def test_empty_transactions_returns_empty_holdings(self) -> None:
        """Test that empty transaction list returns empty holdings."""
        holdings = PortfolioCalculator.calculate_holdings([])
        assert holdings == []

    def test_single_buy_transaction(self) -> None:
        """Test calculating holdings with single buy."""
        portfolio_id = uuid4()
        txn = Transaction(
            id=uuid4(),
            portfolio_id=portfolio_id,
            type=TransactionType.BUY,
            amount=Money(Decimal("1500.00"), "USD"),
            ticker=Ticker("AAPL"),
            quantity=Quantity(Decimal("10")),
            price_per_share=Money(Decimal("150.00"), "USD"),
            timestamp=datetime.now(timezone.utc),
        )
        holdings = PortfolioCalculator.calculate_holdings([txn])
        assert len(holdings) == 1
        assert holdings[0].ticker == Ticker("AAPL")
        assert holdings[0].quantity == Quantity(Decimal("10"))
        assert holdings[0].average_cost == Money(Decimal("150.00"), "USD")

    def test_multiple_buys_same_ticker(self) -> None:
        """Test calculating holdings with multiple buys of same ticker."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(Decimal("1500.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(Decimal("1600.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("160.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        holdings = PortfolioCalculator.calculate_holdings(txns)
        assert len(holdings) == 1
        assert holdings[0].ticker == Ticker("AAPL")
        assert holdings[0].quantity == Quantity(Decimal("20"))
        # Average cost: (1500 + 1600) / 20 = 155
        assert holdings[0].average_cost == Money(Decimal("155.00"), "USD")

    def test_buy_then_sell_partial(self) -> None:
        """Test calculating holdings after partial sell."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(Decimal("1500.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.SELL,
                amount=Money(Decimal("800.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("5")),
                price_per_share=Money(Decimal("160.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        holdings = PortfolioCalculator.calculate_holdings(txns)
        assert len(holdings) == 1
        assert holdings[0].ticker == Ticker("AAPL")
        assert holdings[0].quantity == Quantity(Decimal("5"))
        # Cost basis should be reduced proportionally
        # Original cost: 1500, sell 50% -> remaining cost: 750
        # Average cost: 750 / 5 = 150
        assert holdings[0].average_cost == Money(Decimal("150.00"), "USD")

    def test_buy_then_sell_all(self) -> None:
        """Test that selling all shares removes holding."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(Decimal("1500.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.SELL,
                amount=Money(Decimal("1600.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("160.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        holdings = PortfolioCalculator.calculate_holdings(txns)
        assert holdings == []

    def test_multiple_tickers(self) -> None:
        """Test calculating holdings with multiple tickers."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(Decimal("1500.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(Decimal("2800.00"), "USD"),
                ticker=Ticker("GOOGL"),
                quantity=Quantity(Decimal("1")),
                price_per_share=Money(Decimal("2800.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        holdings = PortfolioCalculator.calculate_holdings(txns)
        assert len(holdings) == 2
        tickers = {h.ticker for h in holdings}
        assert Ticker("AAPL") in tickers
        assert Ticker("GOOGL") in tickers

    def test_non_trade_transactions_ignored(self) -> None:
        """Test that non-trade transactions don't affect holdings."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DEPOSIT,
                amount=Money(Decimal("1000.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DIVIDEND,
                amount=Money(Decimal("50.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        holdings = PortfolioCalculator.calculate_holdings(txns)
        assert holdings == []


class TestCalculateTotalValue:
    """Test PortfolioCalculator.calculate_total_value."""

    def test_empty_holdings_returns_cash_only(self) -> None:
        """Test that empty holdings returns only cash balance."""
        cash = Money(Decimal("1000.00"), "USD")
        total = PortfolioCalculator.calculate_total_value([], {}, cash)
        assert total == Money(Decimal("1000.00"), "USD")

    def test_single_holding_with_price(self) -> None:
        """Test calculating total value with single holding."""
        holdings = [
            Holding(
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                average_cost=Money(Decimal("150.00"), "USD"),
            )
        ]
        prices = {Ticker("AAPL"): Money(Decimal("160.00"), "USD")}
        cash = Money(Decimal("500.00"), "USD")
        total = PortfolioCalculator.calculate_total_value(holdings, prices, cash)
        # 10 * 160 + 500 = 2100
        assert total == Money(Decimal("2100.00"), "USD")

    def test_multiple_holdings_with_prices(self) -> None:
        """Test calculating total value with multiple holdings."""
        holdings = [
            Holding(
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                average_cost=Money(Decimal("150.00"), "USD"),
            ),
            Holding(
                ticker=Ticker("GOOGL"),
                quantity=Quantity(Decimal("2")),
                average_cost=Money(Decimal("2800.00"), "USD"),
            ),
        ]
        prices = {
            Ticker("AAPL"): Money(Decimal("160.00"), "USD"),
            Ticker("GOOGL"): Money(Decimal("2900.00"), "USD"),
        }
        cash = Money(Decimal("1000.00"), "USD")
        total = PortfolioCalculator.calculate_total_value(holdings, prices, cash)
        # (10 * 160) + (2 * 2900) + 1000 = 1600 + 5800 + 1000 = 8400
        assert total == Money(Decimal("8400.00"), "USD")

    def test_holding_without_price_ignored(self) -> None:
        """Test that holdings without prices are ignored in calculation."""
        holdings = [
            Holding(
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                average_cost=Money(Decimal("150.00"), "USD"),
            ),
            Holding(
                ticker=Ticker("GOOGL"),
                quantity=Quantity(Decimal("2")),
                average_cost=Money(Decimal("2800.00"), "USD"),
            ),
        ]
        prices = {
            Ticker("AAPL"): Money(Decimal("160.00"), "USD"),
            # GOOGL price missing
        }
        cash = Money(Decimal("1000.00"), "USD")
        total = PortfolioCalculator.calculate_total_value(holdings, prices, cash)
        # Only AAPL counted: (10 * 160) + 1000 = 2600
        assert total == Money(Decimal("2600.00"), "USD")


class TestPortfolioCalculatorPropertyBased:
    """Property-based tests for PortfolioCalculator."""

    @given(
        deposits=st.lists(
            st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("10000.00"),
                places=2,
            ),
            min_size=1,
            max_size=10,
        )
    )
    def test_only_deposits_results_in_positive_balance(
        self, deposits: list[Decimal]
    ) -> None:
        """Test that only deposits results in positive cash balance."""
        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.DEPOSIT,
                amount=Money(amount, "USD"),
                timestamp=datetime.now(timezone.utc),
            )
            for amount in deposits
        ]
        balance = PortfolioCalculator.calculate_cash_balance(txns)
        assert balance.amount > 0
        assert balance.amount == sum(deposits)

    @given(
        buy_quantity=st.decimals(
            min_value=Decimal("1"), max_value=Decimal("100"), places=2
        ),
        sell_quantity=st.decimals(
            min_value=Decimal("1"), max_value=Decimal("100"), places=2
        ),
    )
    def test_holdings_quantity_matches_buys_minus_sells(
        self, buy_quantity: Decimal, sell_quantity: Decimal
    ) -> None:
        """Test that holdings quantity equals buy quantity minus sell quantity."""
        # Only test if we're not selling more than we bought
        if sell_quantity >= buy_quantity:
            return

        portfolio_id = uuid4()
        txns = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.BUY,
                amount=Money(buy_quantity * Decimal("100.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(buy_quantity),
                price_per_share=Money(Decimal("100.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                type=TransactionType.SELL,
                amount=Money(sell_quantity * Decimal("100.00"), "USD"),
                ticker=Ticker("AAPL"),
                quantity=Quantity(sell_quantity),
                price_per_share=Money(Decimal("100.00"), "USD"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        holdings = PortfolioCalculator.calculate_holdings(txns)
        if buy_quantity == sell_quantity:
            assert len(holdings) == 0
        else:
            assert len(holdings) == 1
            assert holdings[0].quantity.value == buy_quantity - sell_quantity
