"""Tests for MovingAverageCrossoverStrategy."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from zebu.application.dtos.price_point import PricePoint
from zebu.domain.services.strategies.moving_average_crossover import (
    MovingAverageCrossoverStrategy,
)
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trade_signal import TradeAction


def _make_price_map(
    ticker: str,
    prices: list[tuple[date, Decimal]],
) -> dict[str, dict[date, PricePoint]]:
    """Build a price_map for a single ticker from (date, price) pairs."""
    result: dict[date, PricePoint] = {}
    for d, price in prices:
        ts = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC)
        result[d] = PricePoint(
            ticker=Ticker(ticker),
            price=Money(price, "USD"),
            timestamp=ts,
            source="database",
            interval="1day",
        )
    return {ticker: result}


def _daily_prices(
    ticker: str,
    start: date,
    count: int,
    price: Decimal = Decimal("100"),
) -> dict[str, dict[date, PricePoint]]:
    """Build a price_map with a flat price for ``count`` consecutive days."""
    pairs = [(start + timedelta(days=i), price) for i in range(count)]
    return _make_price_map(ticker, pairs)


class TestMovingAverageCrossoverStrategy:
    """Tests for MovingAverageCrossoverStrategy signal generation."""

    def test_golden_cross_triggers_buy_signal(self) -> None:
        """When fast SMA crosses above slow SMA, a BUY signal is generated."""
        # Prices: first 3 days low (10), next days rising so fast SMA > slow SMA
        prices = [
            (date(2024, 1, 1), Decimal("10")),
            (date(2024, 1, 2), Decimal("10")),
            (date(2024, 1, 3), Decimal("10")),
            (date(2024, 1, 4), Decimal("200")),  # spike drives fast SMA above slow
        ]
        price_map = _make_price_map("AAPL", prices)

        strategy = MovingAverageCrossoverStrategy(
            tickers=["AAPL"],
            fast_window=2,
            slow_window=3,
            invest_fraction=1.0,
        )

        # Day 3: first day with enough data for slow SMA (window=3)
        # fast_sma(3) = (10 + 10) / 2 = 10 (days 2,3)
        # slow_sma(3) = (10 + 10 + 10) / 3 = 10 (days 1,2,3)
        # fast <= slow → no crossover yet; store prev_sma
        signals_day3 = strategy.generate_signals(
            current_date=date(2024, 1, 3),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )
        assert signals_day3 == []

        # Day 4: fast_sma(4) = (10 + 200) / 2 = 105 (days 3,4)
        # slow_sma(4) = (10 + 10 + 200) / 3 = 73.33 (days 2,3,4)
        # prev_fast (10) <= prev_slow (10), fast (105) > slow (73.33) → golden cross
        signals_day4 = strategy.generate_signals(
            current_date=date(2024, 1, 4),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )
        assert len(signals_day4) == 1
        assert signals_day4[0].action == TradeAction.BUY
        assert signals_day4[0].ticker == "AAPL"

    def test_death_cross_triggers_sell_signal(self) -> None:
        """When fast SMA crosses below slow SMA, a SELL signal is generated."""
        prices = [
            (date(2024, 1, 1), Decimal("200")),
            (date(2024, 1, 2), Decimal("200")),
            (date(2024, 1, 3), Decimal("200")),
            (date(2024, 1, 4), Decimal("10")),  # crash drives fast SMA below slow
        ]
        price_map = _make_price_map("AAPL", prices)

        strategy = MovingAverageCrossoverStrategy(
            tickers=["AAPL"],
            fast_window=2,
            slow_window=3,
            invest_fraction=1.0,
        )

        # Seed prev_sma with day 3: fast (200), slow (200) — equal
        strategy.generate_signals(
            current_date=date(2024, 1, 3),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )

        # Day 4: fast_sma drops below slow_sma; holding 50 shares
        signals = strategy.generate_signals(
            current_date=date(2024, 1, 4),
            price_map=price_map,
            cash_balance=Decimal("0"),
            holdings={"AAPL": Decimal("50")},
        )

        assert len(signals) == 1
        assert signals[0].action == TradeAction.SELL
        assert signals[0].ticker == "AAPL"
        assert signals[0].quantity == Decimal("50")

    def test_no_crossover_no_signal(self) -> None:
        """No crossover in either direction produces no signals."""
        prices = [(date(2024, 1, d), Decimal("100")) for d in range(1, 6)]
        price_map = _make_price_map("AAPL", prices)

        strategy = MovingAverageCrossoverStrategy(
            tickers=["AAPL"],
            fast_window=2,
            slow_window=3,
            invest_fraction=0.5,
        )

        # Prime with day 3 (flat prices, no crossover)
        strategy.generate_signals(
            current_date=date(2024, 1, 3),
            price_map=price_map,
            cash_balance=Decimal("5000"),
            holdings={},
        )

        # Day 4: still flat — no crossover
        signals = strategy.generate_signals(
            current_date=date(2024, 1, 4),
            price_map=price_map,
            cash_balance=Decimal("5000"),
            holdings={},
        )

        assert signals == []

    def test_insufficient_data_returns_no_signals(self) -> None:
        """If there are fewer trading days than slow_window, no signals are emitted."""
        # Only 2 days of data but slow_window = 3
        prices = [
            (date(2024, 1, 1), Decimal("100")),
            (date(2024, 1, 2), Decimal("100")),
        ]
        price_map = _make_price_map("AAPL", prices)

        strategy = MovingAverageCrossoverStrategy(
            tickers=["AAPL"],
            fast_window=2,
            slow_window=3,
            invest_fraction=1.0,
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 2),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert signals == []

    def test_already_holding_no_duplicate_buy(self) -> None:
        """No BUY signal is generated when already holding the asset."""
        prices = [
            (date(2024, 1, 1), Decimal("10")),
            (date(2024, 1, 2), Decimal("10")),
            (date(2024, 1, 3), Decimal("10")),
            (date(2024, 1, 4), Decimal("200")),
        ]
        price_map = _make_price_map("AAPL", prices)

        strategy = MovingAverageCrossoverStrategy(
            tickers=["AAPL"],
            fast_window=2,
            slow_window=3,
            invest_fraction=1.0,
        )

        # Prime prev_sma on day 3
        strategy.generate_signals(
            current_date=date(2024, 1, 3),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )

        # Day 4 golden cross, but already holding → no BUY
        signals = strategy.generate_signals(
            current_date=date(2024, 1, 4),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={"AAPL": Decimal("10")},  # already in position
        )

        assert signals == []

    def test_multiple_tickers_independent_signals(self) -> None:
        """Each ticker generates signals independently."""
        aapl_prices = [
            (date(2024, 1, 1), Decimal("10")),
            (date(2024, 1, 2), Decimal("10")),
            (date(2024, 1, 3), Decimal("10")),
            (date(2024, 1, 4), Decimal("200")),  # AAPL golden cross
        ]
        googl_prices = [
            (date(2024, 1, 1), Decimal("100")),
            (date(2024, 1, 2), Decimal("100")),
            (date(2024, 1, 3), Decimal("100")),
            (date(2024, 1, 4), Decimal("100")),  # GOOGL flat — no crossover
        ]
        price_map: dict[str, dict[date, PricePoint]] = {}
        price_map.update(_make_price_map("AAPL", aapl_prices))
        price_map.update(_make_price_map("GOOGL", googl_prices))

        strategy = MovingAverageCrossoverStrategy(
            tickers=["AAPL", "GOOGL"],
            fast_window=2,
            slow_window=3,
            invest_fraction=0.5,
        )

        # Prime day 3
        strategy.generate_signals(
            current_date=date(2024, 1, 3),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )

        # Day 4: only AAPL should generate a BUY
        signals = strategy.generate_signals(
            current_date=date(2024, 1, 4),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert len(signals) == 1
        assert signals[0].ticker == "AAPL"
        assert signals[0].action == TradeAction.BUY

    def test_minimum_windows_fast2_slow3(self) -> None:
        """Edge case: fast_window=2, slow_window=3 computes correctly."""
        prices = [
            (date(2024, 1, 1), Decimal("100")),
            (date(2024, 1, 2), Decimal("100")),
            (date(2024, 1, 3), Decimal("100")),
        ]
        price_map = _make_price_map("AAPL", prices)

        strategy = MovingAverageCrossoverStrategy(
            tickers=["AAPL"],
            fast_window=2,
            slow_window=3,
            invest_fraction=1.0,
        )

        # Day 3 is the first day with enough data; should not raise
        signals = strategy.generate_signals(
            current_date=date(2024, 1, 3),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )

        # flat prices → no crossover
        assert signals == []

    def test_buy_amount_equals_cash_times_invest_fraction(self) -> None:
        """BUY signal amount equals cash_balance × invest_fraction."""
        prices = [
            (date(2024, 1, 1), Decimal("10")),
            (date(2024, 1, 2), Decimal("10")),
            (date(2024, 1, 3), Decimal("10")),
            (date(2024, 1, 4), Decimal("200")),
        ]
        price_map = _make_price_map("AAPL", prices)

        strategy = MovingAverageCrossoverStrategy(
            tickers=["AAPL"],
            fast_window=2,
            slow_window=3,
            invest_fraction=0.5,
        )

        strategy.generate_signals(
            current_date=date(2024, 1, 3),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )

        signals = strategy.generate_signals(
            current_date=date(2024, 1, 4),
            price_map=price_map,
            cash_balance=Decimal("10000"),
            holdings={},
        )

        assert len(signals) == 1
        assert signals[0].amount == Decimal("5000")  # 10000 × 0.5
