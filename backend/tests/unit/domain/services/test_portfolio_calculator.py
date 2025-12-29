"""Tests for PortfolioCalculator service."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from papertrade.domain.entities.transaction import Transaction, TransactionType
from papertrade.domain.services.portfolio_calculator import PortfolioCalculator
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.quantity import Quantity
from papertrade.domain.value_objects.ticker import Ticker


class TestCalculateCashBalance:
    """Tests for calculate_cash_balance method."""

    def test_empty_transaction_list(self) -> None:
        """Should return zero balance for empty transaction list."""
        balance = PortfolioCalculator.calculate_cash_balance([])
        assert balance.amount == Decimal("0.00")
        assert balance.currency == "USD"

    def test_single_deposit(self) -> None:
        """Should calculate balance from single deposit."""
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("1000.00")),
            )
        ]

        balance = PortfolioCalculator.calculate_cash_balance(transactions)
        assert balance.amount == Decimal("1000.00")

    def test_multiple_deposits(self) -> None:
        """Should sum multiple deposits."""
        portfolio_id = uuid4()
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("1000.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("500.00")),
            ),
        ]

        balance = PortfolioCalculator.calculate_cash_balance(transactions)
        assert balance.amount == Decimal("1500.00")

    def test_deposit_and_withdrawal(self) -> None:
        """Should handle both deposits and withdrawals."""
        portfolio_id = uuid4()
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("1000.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.WITHDRAWAL,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-300.00")),
            ),
        ]

        balance = PortfolioCalculator.calculate_cash_balance(transactions)
        assert balance.amount == Decimal("700.00")

    def test_buy_reduces_cash(self) -> None:
        """Buy transaction should reduce cash balance."""
        portfolio_id = uuid4()
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("10000.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            ),
        ]

        balance = PortfolioCalculator.calculate_cash_balance(transactions)
        assert balance.amount == Decimal("8500.00")

    def test_sell_increases_cash(self) -> None:
        """Sell transaction should increase cash balance."""
        portfolio_id = uuid4()
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.DEPOSIT,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("10000.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.SELL,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("800.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("5")),
                price_per_share=Money(Decimal("160.00")),
            ),
        ]

        balance = PortfolioCalculator.calculate_cash_balance(transactions)
        # 10000 - 1500 + 800 = 9300
        assert balance.amount == Decimal("9300.00")


class TestCalculateHoldings:
    """Tests for calculate_holdings method."""

    def test_empty_transaction_list(self) -> None:
        """Should return empty list for no transactions."""
        holdings = PortfolioCalculator.calculate_holdings([])
        assert holdings == []

    def test_single_buy_transaction(self) -> None:
        """Should create holding from single buy."""
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            )
        ]

        holdings = PortfolioCalculator.calculate_holdings(transactions)
        assert len(holdings) == 1
        assert holdings[0].ticker == Ticker("AAPL")
        assert holdings[0].quantity.shares == Decimal("10")
        assert holdings[0].cost_basis.amount == Decimal("1500.00")

    def test_multiple_buys_same_ticker(self) -> None:
        """Should accumulate multiple buys of same ticker."""
        portfolio_id = uuid4()
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-800.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("5")),
                price_per_share=Money(Decimal("160.00")),
            ),
        ]

        holdings = PortfolioCalculator.calculate_holdings(transactions)
        assert len(holdings) == 1
        assert holdings[0].ticker == Ticker("AAPL")
        assert holdings[0].quantity.shares == Decimal("15")  # 10 + 5
        assert holdings[0].cost_basis.amount == Decimal("2300.00")  # 1500 + 800

    def test_multiple_tickers(self) -> None:
        """Should create separate holdings for different tickers."""
        portfolio_id = uuid4()
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-3000.00")),
                ticker=Ticker("MSFT"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("300.00")),
            ),
        ]

        holdings = PortfolioCalculator.calculate_holdings(transactions)
        assert len(holdings) == 2

        # Sort for consistent testing
        holdings_by_ticker = {h.ticker.symbol: h for h in holdings}
        assert "AAPL" in holdings_by_ticker
        assert "MSFT" in holdings_by_ticker

    def test_buy_then_sell_reduces_quantity(self) -> None:
        """Should reduce quantity after sell."""
        portfolio_id = uuid4()
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.SELL,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("450.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("3")),
                price_per_share=Money(Decimal("150.00")),
            ),
        ]

        holdings = PortfolioCalculator.calculate_holdings(transactions)
        assert len(holdings) == 1
        assert holdings[0].quantity.shares == Decimal("7")  # 10 - 3

    def test_cost_basis_reduces_proportionally_on_sell(self) -> None:
        """Cost basis should reduce proportionally when selling."""
        portfolio_id = uuid4()
        transactions = [
            # Buy 10 shares at $150 = $1500 cost
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            ),
            # Sell 5 shares (50%) - cost basis should reduce by 50%
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.SELL,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("800.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("5")),
                price_per_share=Money(Decimal("160.00")),
            ),
        ]

        holdings = PortfolioCalculator.calculate_holdings(transactions)
        assert len(holdings) == 1
        assert holdings[0].quantity.shares == Decimal("5")
        # Cost basis: 1500 * (5 remaining / 10 original) = 750
        assert holdings[0].cost_basis.amount == Decimal("750.00")

    def test_complete_sell_closes_position(self) -> None:
        """Selling all shares should result in no holdings."""
        portfolio_id = uuid4()
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.SELL,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("1600.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("160.00")),
            ),
        ]

        holdings = PortfolioCalculator.calculate_holdings(transactions)
        # Zero positions should be filtered out
        assert holdings == []

    def test_multiple_buy_sell_cycles(self) -> None:
        """Should handle multiple buy/sell cycles correctly."""
        portfolio_id = uuid4()
        transactions = [
            # Buy 10
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1000.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("100.00")),
            ),
            # Sell 5
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.SELL,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("550.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("5")),
                price_per_share=Money(Decimal("110.00")),
            ),
            # Buy 8 more
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-960.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("8")),
                price_per_share=Money(Decimal("120.00")),
            ),
        ]

        holdings = PortfolioCalculator.calculate_holdings(transactions)
        assert len(holdings) == 1
        # Quantity: 10 - 5 + 8 = 13
        assert holdings[0].quantity.shares == Decimal("13")
        # Cost: 1000 * (5/10) + 960 = 500 + 960 = 1460
        assert holdings[0].cost_basis.amount == Decimal("1460.00")


class TestCalculateHoldingForTicker:
    """Tests for calculate_holding_for_ticker method."""

    def test_ticker_not_found(self) -> None:
        """Should return None for ticker not in transactions."""
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=uuid4(),
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            )
        ]

        holding = PortfolioCalculator.calculate_holding_for_ticker(
            transactions, Ticker("MSFT")
        )
        assert holding is None

    def test_ticker_found(self) -> None:
        """Should return holding for specified ticker."""
        portfolio_id = uuid4()
        transactions = [
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-1500.00")),
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("150.00")),
            ),
            Transaction(
                id=uuid4(),
                portfolio_id=portfolio_id,
                transaction_type=TransactionType.BUY,
                timestamp=datetime.now(UTC),
                cash_change=Money(Decimal("-3000.00")),
                ticker=Ticker("MSFT"),
                quantity=Quantity(Decimal("10")),
                price_per_share=Money(Decimal("300.00")),
            ),
        ]

        holding = PortfolioCalculator.calculate_holding_for_ticker(
            transactions, Ticker("AAPL")
        )
        assert holding is not None
        assert holding.ticker == Ticker("AAPL")
        assert holding.quantity.shares == Decimal("10")


class TestCalculatePortfolioValue:
    """Tests for calculate_portfolio_value method."""

    def test_empty_holdings(self) -> None:
        """Should return zero for empty holdings."""
        value = PortfolioCalculator.calculate_portfolio_value([], {})
        assert value.amount == Decimal("0.00")

    def test_single_holding(self) -> None:
        """Should calculate value from single holding."""
        from papertrade.domain.entities.holding import Holding

        holdings = [
            Holding(
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                cost_basis=Money(Decimal("1500.00")),
            )
        ]
        prices = {Ticker("AAPL"): Money(Decimal("160.00"))}

        value = PortfolioCalculator.calculate_portfolio_value(holdings, prices)
        # 10 shares * $160 = $1600
        assert value.amount == Decimal("1600.00")

    def test_multiple_holdings(self) -> None:
        """Should sum values of multiple holdings."""
        from papertrade.domain.entities.holding import Holding

        holdings = [
            Holding(
                ticker=Ticker("AAPL"),
                quantity=Quantity(Decimal("10")),
                cost_basis=Money(Decimal("1500.00")),
            ),
            Holding(
                ticker=Ticker("MSFT"),
                quantity=Quantity(Decimal("5")),
                cost_basis=Money(Decimal("1500.00")),
            ),
        ]
        prices = {
            Ticker("AAPL"): Money(Decimal("160.00")),
            Ticker("MSFT"): Money(Decimal("320.00")),
        }

        value = PortfolioCalculator.calculate_portfolio_value(holdings, prices)
        # (10 * 160) + (5 * 320) = 1600 + 1600 = 3200
        assert value.amount == Decimal("3200.00")


class TestCalculateTotalValue:
    """Tests for calculate_total_value method."""

    def test_cash_only(self) -> None:
        """Should return just cash when no holdings."""
        cash = Money(Decimal("10000.00"))
        holdings_value = Money(Decimal("0.00"))

        total = PortfolioCalculator.calculate_total_value(cash, holdings_value)
        assert total.amount == Decimal("10000.00")

    def test_cash_and_holdings(self) -> None:
        """Should sum cash and holdings value."""
        cash = Money(Decimal("5000.00"))
        holdings_value = Money(Decimal("15000.00"))

        total = PortfolioCalculator.calculate_total_value(cash, holdings_value)
        assert total.amount == Decimal("20000.00")
