"""Tests for BacktestTransactionBuilder."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from zebu.application.services.backtest_transaction_builder import (
    BacktestTransactionBuilder,
)
from zebu.domain.entities.transaction import TransactionType
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal


def _now() -> datetime:
    return datetime.now(UTC)


def _buy_signal_by_amount(
    ticker: str, amount: Decimal, dt: datetime | None = None
) -> TradeSignal:
    return TradeSignal(
        action=TradeAction.BUY,
        ticker=Ticker(ticker),
        signal_date=(dt or _now()).date(),
        amount=Money(amount, "USD"),
    )


def _buy_signal_by_quantity(
    ticker: str, quantity: Decimal, dt: datetime | None = None
) -> TradeSignal:
    return TradeSignal(
        action=TradeAction.BUY,
        ticker=Ticker(ticker),
        signal_date=(dt or _now()).date(),
        quantity=Quantity(quantity),
    )


def _sell_signal_by_quantity(
    ticker: str, quantity: Decimal, dt: datetime | None = None
) -> TradeSignal:
    return TradeSignal(
        action=TradeAction.SELL,
        ticker=Ticker(ticker),
        signal_date=(dt or _now()).date(),
        quantity=Quantity(quantity),
    )


class TestBacktestTransactionBuilderBuy:
    """Tests for BUY signal handling."""

    def test_buy_by_amount_creates_transaction(self) -> None:
        """BUY with amount creates a valid transaction with fractional shares."""
        portfolio_id = uuid4()
        builder = BacktestTransactionBuilder(
            portfolio_id=portfolio_id,
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        signal = _buy_signal_by_amount("AAPL", Decimal("1500"))
        price = Money(Decimal("150.00"), "USD")

        transaction = builder.apply_signal(signal, price, _now())

        assert transaction is not None
        assert transaction.transaction_type == TransactionType.BUY
        assert transaction.ticker is not None
        assert transaction.ticker.symbol == "AAPL"
        # 1500 / 150 = 10.0000 shares (clean division)
        assert transaction.quantity is not None
        assert transaction.quantity.shares == Decimal("10.0000")

    def test_buy_by_amount_resolves_to_fractional_shares(self) -> None:
        """Amount-based BUY produces fractional shares to four decimal places.

        Regression for #283: previously this floored to whole shares, so a
        DCA strategy investing $100/period at a $150-priced ticker silently
        emitted zero trades. Fractional execution is the standard model
        retail brokers use for DCA.
        """
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        # 1000 / 300 = 3.3333… → quantised to 3.3333 (round-down)
        signal = _buy_signal_by_amount("GOOGL", Decimal("1000"))
        price = Money(Decimal("300.00"), "USD")

        transaction = builder.apply_signal(signal, price, _now())

        assert transaction is not None
        assert transaction.quantity is not None
        assert transaction.quantity.shares == Decimal("3.3333")

    def test_buy_by_amount_smaller_than_price_uses_fractional_share(self) -> None:
        """A BUY amount below price-per-share still produces a trade.

        Direct regression for #283: ``amount_per_period=$100`` at a
        ``$150`` ticker used to floor to zero shares and silently skip.
        The fractional fix executes ``0.6666`` shares instead.
        """
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        signal = _buy_signal_by_amount("AAPL", Decimal("100"))
        price = Money(Decimal("150.00"), "USD")

        transaction = builder.apply_signal(signal, price, _now())

        assert transaction is not None
        assert transaction.quantity is not None
        # 100 / 150 = 0.6666… → quantised to 0.6666 (round-down)
        assert transaction.quantity.shares == Decimal("0.6666")

    def test_buy_by_quantity_creates_transaction(self) -> None:
        """BUY with explicit quantity creates correct transaction."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        signal = _buy_signal_by_quantity("AAPL", Decimal("5"))
        price = Money(Decimal("100.00"), "USD")

        transaction = builder.apply_signal(signal, price, _now())

        assert transaction is not None
        assert transaction.quantity is not None
        assert transaction.quantity.shares == Decimal("5")

    def test_buy_updates_cash_balance(self) -> None:
        """After BUY, cash balance is reduced by total cost."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        signal = _buy_signal_by_quantity("AAPL", Decimal("10"))
        price = Money(Decimal("100.00"), "USD")

        builder.apply_signal(signal, price, _now())

        # 10000 - (10 * 100) = 9000
        assert builder.cash_balance.amount == Decimal("9000")

    def test_buy_updates_holdings(self) -> None:
        """After BUY, holdings are updated with purchased shares."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        signal = _buy_signal_by_quantity("AAPL", Decimal("10"))
        price = Money(Decimal("100.00"), "USD")

        builder.apply_signal(signal, price, _now())

        assert Ticker("AAPL") in builder.holdings
        assert builder.holdings[Ticker("AAPL")].shares == Decimal("10")

    def test_buy_insufficient_funds_returns_none(self) -> None:
        """BUY that exceeds cash returns None and state is unchanged."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("100"), "USD"),
        )
        # Want to buy 10 @ $100 = $1000, but only have $100
        signal = _buy_signal_by_quantity("AAPL", Decimal("10"))
        price = Money(Decimal("100.00"), "USD")

        result = builder.apply_signal(signal, price, _now())

        assert result is None
        # Cash unchanged
        assert builder.cash_balance.amount == Decimal("100")
        assert builder.holdings == {}

    def test_buy_amount_below_one_fractional_share_returns_none(self) -> None:
        """If amount/price < 0.0001 the quantised quantity is zero → None.

        With four-decimal-place fractional shares, the only "amount too
        small" case is when ``amount / price`` rounds down to zero (i.e.
        below the ``0.0001`` fractional-share quantum).
        """
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        # amount = $0.01 (1 cent), price = $200 → 0.00005 → quantised to 0
        signal = _buy_signal_by_amount("AAPL", Decimal("0.01"))
        price = Money(Decimal("200.00"), "USD")

        result = builder.apply_signal(signal, price, _now())

        assert result is None

    def test_buy_amount_smaller_than_price_executes_fractional_share(self) -> None:
        """An amount below the price-per-share executes a fractional share.

        Mirrors the user-visible behaviour from #283: DCA with
        ``amount_per_period=$50`` at a ``$100`` ticker now buys
        ``0.5000`` shares, not zero.
        """
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        signal = _buy_signal_by_amount("AAPL", Decimal("50"))
        price = Money(Decimal("100.00"), "USD")

        transaction = builder.apply_signal(signal, price, _now())

        assert transaction is not None
        assert transaction.quantity is not None
        assert transaction.quantity.shares == Decimal("0.5000")

    def test_multiple_buys_accumulate_holdings(self) -> None:
        """Multiple BUY signals for the same ticker accumulate holdings."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        price = Money(Decimal("100.00"), "USD")

        for _ in range(3):
            signal = _buy_signal_by_quantity("AAPL", Decimal("5"))
            builder.apply_signal(signal, price, _now())

        assert builder.holdings[Ticker("AAPL")].shares == Decimal("15")


class TestBacktestTransactionBuilderSell:
    """Tests for SELL signal handling."""

    def _buy_shares(
        self, builder: BacktestTransactionBuilder, ticker: str, shares: Decimal
    ) -> None:
        """Helper to buy shares for a ticker."""
        signal = _buy_signal_by_quantity(ticker, shares)
        price = Money(Decimal("100.00"), "USD")
        builder.apply_signal(signal, price, _now())

    def test_sell_reduces_holdings(self) -> None:
        """After SELL, holdings for ticker are reduced."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        self._buy_shares(builder, "AAPL", Decimal("10"))

        sell_signal = _sell_signal_by_quantity("AAPL", Decimal("5"))
        price = Money(Decimal("100.00"), "USD")
        builder.apply_signal(sell_signal, price, _now())

        assert builder.holdings[Ticker("AAPL")].shares == Decimal("5")

    def test_sell_all_shares_removes_from_holdings(self) -> None:
        """Selling all shares removes ticker from holdings dict."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        self._buy_shares(builder, "AAPL", Decimal("10"))

        sell_signal = _sell_signal_by_quantity("AAPL", Decimal("10"))
        price = Money(Decimal("100.00"), "USD")
        builder.apply_signal(sell_signal, price, _now())

        assert Ticker("AAPL") not in builder.holdings

    def test_sell_increases_cash(self) -> None:
        """SELL increases cash balance."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        self._buy_shares(builder, "AAPL", Decimal("10"))
        cash_after_buy = builder.cash_balance.amount

        sell_signal = _sell_signal_by_quantity("AAPL", Decimal("5"))
        price = Money(Decimal("120.00"), "USD")  # sell at higher price
        builder.apply_signal(sell_signal, price, _now())

        expected = cash_after_buy + Decimal("5") * Decimal("120")
        assert builder.cash_balance.amount == expected

    def test_sell_insufficient_shares_returns_none(self) -> None:
        """SELL that exceeds holdings returns None."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        self._buy_shares(builder, "AAPL", Decimal("5"))

        sell_signal = _sell_signal_by_quantity("AAPL", Decimal("10"))
        price = Money(Decimal("100.00"), "USD")
        result = builder.apply_signal(sell_signal, price, _now())

        assert result is None
        # Holdings unchanged
        assert builder.holdings[Ticker("AAPL")].shares == Decimal("5")

    def test_sell_no_holdings_returns_none(self) -> None:
        """SELL on a ticker with no holdings returns None."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )

        sell_signal = _sell_signal_by_quantity("AAPL", Decimal("5"))
        price = Money(Decimal("100.00"), "USD")
        result = builder.apply_signal(sell_signal, price, _now())

        assert result is None


class TestBacktestTransactionBuilderState:
    """Tests for state tracking in BacktestTransactionBuilder."""

    def test_initial_state(self) -> None:
        """Builder starts with correct initial state."""
        initial_cash = Money(Decimal("5000"), "USD")
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=initial_cash,
        )

        assert builder.cash_balance == initial_cash
        assert builder.holdings == {}
        assert builder.transactions == []

    def test_transactions_list_grows(self) -> None:
        """Each successful signal adds a transaction to the list."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        price = Money(Decimal("100.00"), "USD")

        for _i in range(3):
            signal = _buy_signal_by_quantity("AAPL", Decimal("1"))
            builder.apply_signal(signal, price, _now())

        assert len(builder.transactions) == 3

    def test_failed_signals_not_added_to_transactions(self) -> None:
        """Failed signals (insufficient funds/shares) don't add transactions."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("50"), "USD"),
        )
        # This will fail (not enough cash)
        signal = _buy_signal_by_quantity("AAPL", Decimal("10"))
        price = Money(Decimal("100.00"), "USD")
        builder.apply_signal(signal, price, _now())

        assert len(builder.transactions) == 0

    def test_count_trades_counts_buy_and_sell_only(self) -> None:
        """count_trades() returns only BUY + SELL transactions."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        price = Money(Decimal("100.00"), "USD")

        # 2 buys
        for _ in range(2):
            signal = _buy_signal_by_quantity("AAPL", Decimal("5"))
            builder.apply_signal(signal, price, _now())

        # 1 sell
        sell_signal = _sell_signal_by_quantity("AAPL", Decimal("3"))
        builder.apply_signal(sell_signal, price, _now())

        assert builder.count_trades() == 3

    def test_holdings_returns_copy(self) -> None:
        """holdings property returns a copy to prevent mutation."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        holdings1 = builder.holdings
        holdings2 = builder.holdings
        assert holdings1 is not holdings2

    def test_transactions_returns_copy(self) -> None:
        """transactions property returns a copy to prevent mutation."""
        builder = BacktestTransactionBuilder(
            portfolio_id=uuid4(),
            initial_cash=Money(Decimal("10000"), "USD"),
        )
        txns1 = builder.transactions
        txns2 = builder.transactions
        assert txns1 is not txns2
