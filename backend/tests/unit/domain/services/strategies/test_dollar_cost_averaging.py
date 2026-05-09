"""Tests for DollarCostAveragingStrategy."""

from datetime import date
from decimal import Decimal

from zebu.domain.services.strategies.dollar_cost_averaging import (
    DollarCostAveragingStrategy,
)
from zebu.domain.value_objects.allocation import Allocation
from zebu.domain.value_objects.price_point import PricePoint
from zebu.domain.value_objects.trade_signal import TradeAction


class TestDollarCostAveragingStrategy:
    """Tests for DollarCostAveragingStrategy signal generation."""

    def _make_price_map(self) -> dict[str, dict[date, PricePoint]]:
        """Return an empty price map (not used by DCA)."""
        return {}

    def test_first_day_triggers_purchase(self) -> None:
        """On the first call, BUY signals are generated."""
        strategy = DollarCostAveragingStrategy(
            tickers=["AAPL"],
            frequency_days=7,
            amount_per_period=Decimal("1000"),
            allocation=Allocation.from_raw({"AAPL": 1.0}),
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert len(signals) == 1
        assert signals[0].action == TradeAction.BUY
        assert signals[0].ticker.symbol == "AAPL"

    def test_subsequent_days_within_window_no_signals(self) -> None:
        """Days within the frequency window produce no signals."""
        strategy = DollarCostAveragingStrategy(
            tickers=["AAPL"],
            frequency_days=7,
            amount_per_period=Decimal("1000"),
            allocation=Allocation.from_raw({"AAPL": 1.0}),
        )

        # First purchase
        strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        # Days 1–6 after purchase: no signals
        for delta in range(1, 7):
            signals = strategy.generate_signals(
                current_date=date(2024, 1, 2 + delta),
                price_map=self._make_price_map(),
                cash_balance=Decimal("10000"),
                holdings={},
            )
            assert signals == [], f"Expected no signals on day +{delta}"

    def test_day_at_frequency_boundary_triggers_purchase(self) -> None:
        """On the day exactly ``frequency_days`` after the last purchase, buy."""
        strategy = DollarCostAveragingStrategy(
            tickers=["AAPL"],
            frequency_days=7,
            amount_per_period=Decimal("1000"),
            allocation=Allocation.from_raw({"AAPL": 1.0}),
        )

        # First purchase
        strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        # Exactly 7 days later: should purchase
        signals = strategy.generate_signals(
            current_date=date(2024, 1, 9),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert len(signals) == 1
        assert signals[0].action == TradeAction.BUY

    def test_multiple_tickers_allocation(self) -> None:
        """Multiple tickers each receive their allocated fraction."""
        strategy = DollarCostAveragingStrategy(
            tickers=["AAPL", "GOOGL"],
            frequency_days=7,
            amount_per_period=Decimal("1000"),
            allocation=Allocation.from_raw({"AAPL": 0.6, "GOOGL": 0.4}),
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert len(signals) == 2
        signal_map = {s.ticker.symbol: s for s in signals}
        assert signal_map["AAPL"].amount is not None
        assert signal_map["AAPL"].amount.amount == Decimal("600.00")
        assert signal_map["GOOGL"].amount is not None
        assert signal_map["GOOGL"].amount.amount == Decimal("400.00")

    def test_zero_cash_balance_still_generates_signal(self) -> None:
        """DCA generates signals even when cash_balance is zero.

        The executor is responsible for skipping signals that exceed
        available cash. The strategy itself should still emit signals.
        """
        strategy = DollarCostAveragingStrategy(
            tickers=["AAPL"],
            frequency_days=7,
            amount_per_period=Decimal("1000"),
            allocation=Allocation.from_raw({"AAPL": 1.0}),
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("0"),
            holdings={},
        )

        # Signal is based on amount_per_period, not cash_balance
        assert len(signals) == 1
        assert signals[0].amount is not None
        assert signals[0].amount.amount == Decimal("1000.00")

    def test_daily_frequency_purchases_every_day(self) -> None:
        """frequency_days=1 causes a purchase on every trading day."""
        strategy = DollarCostAveragingStrategy(
            tickers=["AAPL"],
            frequency_days=1,
            amount_per_period=Decimal("100"),
            allocation=Allocation.from_raw({"AAPL": 1.0}),
        )

        for i in range(5):
            signals = strategy.generate_signals(
                current_date=date(2024, 1, 2 + i),
                price_map=self._make_price_map(),
                cash_balance=Decimal("10000"),
                holdings={},
            )
            assert len(signals) == 1, f"Expected signal on day {i + 1}"

    def test_signal_amount_equals_period_amount_times_allocation(self) -> None:
        """Signal amount = amount_per_period × allocation fraction."""
        strategy = DollarCostAveragingStrategy(
            tickers=["AAPL"],
            frequency_days=30,
            amount_per_period=Decimal("500"),
            allocation=Allocation.from_raw({"AAPL": 1.0}),
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=self._make_price_map(),
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert len(signals) == 1
        assert signals[0].amount is not None
        # 500 × 1.0 = 500
        assert signals[0].amount.amount == Decimal("500.00")

    def test_signal_date_matches_current_date(self) -> None:
        """TradeSignal.signal_date matches the current_date argument."""
        strategy = DollarCostAveragingStrategy(
            tickers=["AAPL"],
            frequency_days=7,
            amount_per_period=Decimal("1000"),
            allocation=Allocation.from_raw({"AAPL": 1.0}),
        )
        today = date(2024, 6, 15)

        signals = strategy.generate_signals(
            current_date=today,
            price_map=self._make_price_map(),
            cash_balance=Decimal("5000"),
            holdings={},
        )

        assert signals[0].signal_date == today
